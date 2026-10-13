# src/agents/macro_reviewer.py
from src.agents.state import AgentState
from src.rag.embedder import embedder
from src.rag.vector_store import vector_store
from config.settings import settings
from config.logger import setup_logger
from groq import Groq
import json
#from duckduckgo_search import DDGS
from ddgs import DDGS

logger = setup_logger(__name__)
client = Groq(api_key=settings.groq_api_key)

def macro_reviewer_node(state: AgentState) -> dict:
    ticker = state.get("ticker")
    tenant_id = state.get("tenant_id")
    
    logger.info(f"[Qualitative Agent] Querying vector DB for {ticker} official SEC context...")
    
    # 1. Fetch Official Context (10-K Vector Search)
    query_embedding = embedder.embed_query(
        "strategic initiatives, upcoming projects, new products, research and development pipeline, competitors, market risks"
    )
    matches = vector_store.search(tenant_id=tenant_id, query_embedding=query_embedding, top_k=15)
    retrieved_context = "\n...\n".join([m["metadata"]["text"] for m in matches])

    # 2. Fetch Real-Time Context (DuckDuckGo Search)
    logger.info(f"[Qualitative Agent] Fetching real-time market news for {ticker} via DuckDuckGo...")
    realtime_news = ""
    try:
        ddgs = DDGS()
        # Search the web for the latest company news and projects
        results = ddgs.text(f"{ticker} stock company news upcoming projects market trends", max_results=5)
        if results:
            # Format the search results into a clean string for the LLM
            realtime_news = "\n".join([f"- {r.get('title')}: {r.get('body')}" for r in results])
        else:
            realtime_news = "No recent news found."
    except Exception as e:
        logger.warning(f"DuckDuckGo search rate-limited or failed: {str(e)}")
        realtime_news = "Real-time news search temporarily unavailable."

    # 3. Prompt the LLM with BOTH contexts
    prompt = f"""
    You are an expert Strategic Equity Analyst evaluating {ticker}.
    Based on BOTH the official 10-K filing text and the LIVE real-time news below, output a STRICT JSON object with three keys:
    
    - "macro_analysis": A 2-paragraph summary of industry headwinds, regulatory risks, and current market sentiment based on the latest news.
    - "competitors": A bulleted list of competitors mentioned and their market threat.
    - "projects": A detailed bulleted list of upcoming projects, R&D focus areas, and new product pipelines. MUST incorporate recent developments from the live news.

    [OFFICIAL SEC EXCERPTS (Historical)]
    {retrieved_context} 
    
    [LIVE REAL-TIME NEWS (Current Events)]
    {realtime_news}
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a financial API returning valid JSON."},
                {"role": "user", "content": prompt}
            ],
            model=settings.default_model,
            response_format={"type": "json_object"},
            temperature=0.3 
        )
        
        raw = json.loads(response.choices[0].message.content)

        # Normalize: model may return [ {...} ] or something unexpected
        if isinstance(raw, list):
            raw = next((x for x in raw if isinstance(x, dict)), {})
        if not isinstance(raw, dict):
            raw = {}

        def as_text(v, default):
            if not v:
                return default
            if isinstance(v, list):
                return "\n".join(f"- {i}" if isinstance(i, str) else f"- {json.dumps(i)}" for i in v)
            if isinstance(v, dict):
                return json.dumps(v, indent=2)
            return str(v)

        return {
            "macro_analysis": as_text(raw.get("macro_analysis"), "Not available."),
            "competitor_analysis": as_text(raw.get("competitors"), "No competitor data found."),
            "upcoming_projects": as_text(raw.get("projects"), "No project data found."),
        }
    except Exception as e:
        return {"errors": [f"Macro Reviewer Failed: {str(e)}"]}