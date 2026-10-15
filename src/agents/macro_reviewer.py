# src/agents/macro_reviewer.py
import re
import json

from ddgs import DDGS
from groq import Groq

from src.agents.state import AgentState
from src.rag.embedder import embedder
from src.rag.vector_store import vector_store
from src.mcp.tools.edgar_client import edgar_client
from config.settings import settings
from config.logger import setup_logger

logger = setup_logger(__name__)
client = Groq(api_key=settings.groq_api_key)

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
    - "competitors": A bulleted list of competitors mentioned and their market threat.
    - "projects": A detailed bulleted list of upcoming projects, R&D focus areas, and new product pipelines. Incorporate recent developments from the live news where available.

    If the live news says no results were found, rely on the SEC excerpts only and do not invent current events.

    [OFFICIAL SEC EXCERPTS (Historical)]
    {retrieved_context}

    [LIVE REAL-TIME NEWS (Current Events)]
    {realtime_news}
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a financial API returning valid JSON."},
                {"role": "user", "content": prompt},
            ],
            model=settings.default_model,
            response_format={"type": "json_object"},
            temperature=0.3,
        )

        raw = json.loads(response.choices[0].message.content)
        if isinstance(raw, list):
            raw = next((x for x in raw if isinstance(x, dict)), {})
        if not isinstance(raw, dict):
            raw = {}

        return {
            "macro_analysis": _as_text(raw.get("macro_analysis"), "Not available."),
            "competitor_analysis": _as_text(raw.get("competitors"), "No competitor data found."),
            "upcoming_projects": _as_text(raw.get("projects"), "No project data found."),
        }
    except Exception as e:
        logger.exception("Macro reviewer failed")
        return {"errors": [f"Macro Reviewer Failed: {e}"]}