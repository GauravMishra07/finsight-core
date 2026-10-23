# src/agents/macro_reviewer.py
import re
import json

from ddgs import DDGS
from config.llm import chat

from src.agents.state import AgentState
from src.rag.embedder import embedder
from src.rag.vector_store import vector_store
from src.mcp.tools.edgar_client import edgar_client
from src.agents.risk_analyst import peer_metrics
from config.settings import settings
from config.logger import setup_logger

logger = setup_logger(__name__)

_name_cache: dict = {}


def _company_name(ticker: str) -> str:
    """'COSTCO WHOLESALE CORP /NEW' -> 'Costco Wholesale Corp'. Falls back to the ticker."""
    key = ticker.upper()
    if key in _name_cache:
        return _name_cache[key]
    try:
        name = edgar_client.resolve_company(ticker).name or ticker
    except Exception:
        logger.warning(f"Could not resolve company name for {ticker}; using ticker in news search.")
        name = ticker
    name = re.sub(r"\s*/[^/]*$", "", name).strip()   # drop suffixes like "/NEW" or "/DE"
    name = name.title() if name.isupper() else name
    _name_cache[key] = name
    return name


def _fetch_news(name: str, ticker: str) -> str:
    """Try the news endpoint first, then general web search. Never raises."""
    query = f"{name} ({ticker}) stock news"
    attempts = [
        ("news", lambda d: d.news(query, max_results=6)),
        ("text", lambda d: d.text(f"{name} {ticker} upcoming projects market trends", max_results=6)),
    ]
    for kind, fn in attempts:
        try:
            results = fn(DDGS()) or []
            lines = []
            for r in results:
                if not isinstance(r, dict):
                    continue
                title = r.get("title", "")
                body = r.get("body", "")
                date = r.get("date", "")
                lines.append(f"- {title}{f' ({date})' if date else ''}: {body}")
            if lines:
                return "\n".join(lines)
            logger.info(f"DDG {kind} search returned nothing for '{query}'.")
        except Exception as e:
            logger.warning(f"DDG {kind} search failed: {e}")
    return "No recent news found."


def _as_text(v, default):
    if not v:
        return default
    if isinstance(v, list):
        return "\n".join(f"- {i}" if isinstance(i, str) else f"- {json.dumps(i)}" for i in v)
    if isinstance(v, dict):
        return json.dumps(v, indent=2)
    return str(v)


MAX_PEERS = 4  # each peer costs ~4-8 small SEC requests


def _competitors(raw) -> list:
    """LLM competitor objects -> [{name, ticker, threat, overlap, note, sec_name?, metrics?}].
    Up to MAX_PEERS listed peers get XBRL numbers. Never raises."""
    rows = []
    for c in raw if isinstance(raw, list) else []:
        if isinstance(c, str):
            c = {"name": c}
        if not isinstance(c, dict) or not c.get("name"):
            continue
        threat = str(c.get("threat") or "").title()
        ticker = c.get("ticker")
        rows.append({
            "name": str(c["name"]),
            "ticker": ticker.strip().upper() if isinstance(ticker, str) and ticker.strip() else None,
            "threat": threat if threat in ("High", "Medium", "Low") else None,
            "overlap": str(c.get("overlap") or ""),
            "note": str(c.get("note") or ""),
        })
    for r in [r for r in rows if r["ticker"]][:MAX_PEERS]:
        try:
            hit = peer_metrics(r["ticker"])
        except Exception:
            logger.exception(f"Peer metrics failed for {r['ticker']}")
            hit = None
        if hit:
            r["sec_name"], r["metrics"] = hit
    return rows


def _competitor_text(rows: list) -> str:
    """Markdown bullets of the structured rows (fed to the memo and the chat copilot)."""
    if not rows:
        return "No competitor data found."
    lines = []
    for r in rows:
        head = f"**{r['name']}**" + (f" ({r['ticker']})" if r["ticker"] else "")
        tags = " — ".join(t for t in (f"{r['threat']} threat" if r["threat"] else "", r["overlap"]) if t)
        lines.append(f"- {head}{' — ' + tags if tags else ''}: {r['note']}")
    return "\n".join(lines)


def macro_reviewer_node(state: AgentState) -> dict:
    ticker = state.get("ticker")
    tenant_id = state.get("tenant_id")
    name = _company_name(ticker)

    # 1. Official context from the 10-K (Pinecone)
    logger.info(f"[Qualitative Agent] Querying vector DB for {name} ({ticker}) official SEC context...")
    retrieved_context = ""
    try:
        query_embedding = embedder.embed_query(
            "strategic initiatives, upcoming projects, new products, research and development pipeline, competitors, market risks"
        )
        matches = vector_store.search(tenant_id=tenant_id, query_embedding=query_embedding, top_k=15)
        retrieved_context = "\n...\n".join(
            m["metadata"]["text"] for m in matches if m.get("metadata", {}).get("text")
        )
    except Exception:
        logger.exception("Vector search failed in macro reviewer")

    # 2. Real-time news
    logger.info(f"[Qualitative Agent] Fetching real-time news for '{name}' via DuckDuckGo...")
    realtime_news = _fetch_news(name, ticker)

    # 3. LLM synthesis
    prompt = f"""
    You are an expert Strategic Equity Analyst evaluating {name} (ticker: {ticker}).
    Based on BOTH the official 10-K filing text and the LIVE real-time news below, output a STRICT JSON object
    (a single object, not an array) with three keys:

    - "macro_analysis": A 2-paragraph summary of industry headwinds, regulatory risks, and current market sentiment based on the latest news.
    - "competitors": An array of up to 6 competitor objects, most threatening first, each with:
      "name" (company name), "ticker" (its US stock ticker, or null if private or non-US listed),
      "threat" ("High", "Medium" or "Low"), "overlap" (the segment or product where they compete, a few words),
      "note" (one sentence on why they matter to this company's credit profile).
    - "projects": A detailed bulleted list of upcoming projects, R&D focus areas, and new product pipelines. Incorporate recent developments from the live news where available.

    If the live news says no results were found, rely on the SEC excerpts only and do not invent current events.

    [OFFICIAL SEC EXCERPTS (Historical)]
    {retrieved_context}

    [LIVE REAL-TIME NEWS (Current Events)]
    {realtime_news}
    """

    try:
        response = chat(
            messages=[
                {"role": "system", "content": "You are a financial API returning valid JSON."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )

        raw = json.loads(response.choices[0].message.content)
        if isinstance(raw, list):
            raw = next((x for x in raw if isinstance(x, dict)), {})
        if not isinstance(raw, dict):
            raw = {}

        competitors = _competitors(raw.get("competitors"))
        return {
            "macro_analysis": _as_text(raw.get("macro_analysis"), "Not available."),
            "competitors": competitors,
            "competitor_analysis": _competitor_text(competitors),
            "upcoming_projects": _as_text(raw.get("projects"), "No project data found."),
            "evidence": [retrieved_context, realtime_news],
        }
    except Exception as e:
        logger.exception("Macro reviewer failed")
        return {"errors": [f"Macro Reviewer Failed: {e}"]}