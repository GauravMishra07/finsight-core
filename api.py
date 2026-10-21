# api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import sys
import os

# Ensure Python can find the src directory
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.agents.graph import finsight_graph
from src.rag.embedder import embedder
from src.rag.vector_store import vector_store
from config.settings import settings
from groq import Groq
from config.logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(title="FinSight Underwriting API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
client = Groq(api_key=settings.groq_api_key)

# --- Pydantic Data Models ---
class AnalyzeRequest(BaseModel):
    ticker: str

class ChatRequest(BaseModel):
    ticker: str
    tenant_id: str
    user_query: str
    chat_history: List[Dict[str, str]]
    memo_text: str
    financial_metrics: Dict[str, Any] = {}

# --- API Endpoints ---
@app.get("/health")
def health():
    """Cheap ping the frontend uses to wake Render's free tier."""
    return {"status": "ok"}

@app.post("/api/v1/analyze")
def generate_memo(request: AnalyzeRequest):
    """Triggers the LangGraph multi-agent pipeline."""
    try:
        tenant_id = f"tenant_{request.ticker.lower()}_api"
        initial_state = {
            "tenant_id": tenant_id,
            "ticker": request.ticker,
            "raw_filing_text": None,
            "filing_chunks_indexed": False,
            "financial_metrics": {},
            "risk_analysis": None,
            "macro_analysis": None,
            "competitor_analysis": None,
            "competitors": [],
            "upcoming_projects": None,
            "final_memo": None,
            "errors": []
        }
        
        # Run LangGraph pipeline
        final_state = finsight_graph.invoke(initial_state)

        if not final_state.get("filing_chunks_indexed"):
            raise HTTPException(
                status_code=502,
                detail=f"Could not ingest the SEC filing: {final_state.get('errors')}",
            )
        if not final_state.get("final_memo"):
            raise HTTPException(status_code=500, detail=str(final_state.get("errors")))
        final_state.pop("raw_filing_text", None)  # ~50 KB the UI never uses
        return final_state # includes "errors" so the UI can show them as warnings
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Analyze pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/chat")
async def chat_assistant(request: ChatRequest):
    """Handles RAG-based follow-up questions."""
    try:
        # 1. Search Pinecone
        query_emb = embedder.embed_query(request.user_query)
        matches = vector_store.search(
            tenant_id=request.tenant_id, 
            query_embedding=query_emb, 
            top_k=6
        )
        retrieved_context = "\n...\n".join([m["metadata"]["text"] for m in matches])
        
        # 2. Build Prompt
        # 2. Build Prompt (Inside api.py -> chat_assistant)
        system_prompt = f"""
        You are FinSight Copilot, an expert AI financial analyst.

        FORMAT (answers are read in a narrow side panel):
        Lead with a one or two sentence answer. Then use short bullets or short paragraphs with **bold** key figures.
        Use a Markdown table only for genuinely tabular numbers, with at most 4 columns and compact values ($24.9B, 18.2%).
        Use ### for section headings, never # or ##. No preamble, and don't repeat the question.

        CRITICAL INSTRUCTION FOR FINANCIAL METRICS:
        Always use the following audited XBRL data for baseline quantitative questions (Revenue, Net Income, Assets, etc.):
        {request.financial_metrics}

        Context from SEC 10-K Vector Search:
        {retrieved_context}
        
        Memo Summary (Includes Real-Time DuckDuckGo News):
        {request.memo_text[:3000]}
        """

        messages_for_llm = [{"role": "system", "content": system_prompt}]
        for msg in request.chat_history[-6:]:
            messages_for_llm.append(msg)
            
        messages_for_llm.append({"role": "user", "content": request.user_query})

        # 3. Call Groq
        response = client.chat.completions.create(
            model=settings.default_model,
            messages=messages_for_llm,
            temperature=0.2
        )
        
        return {"answer": response.choices[0].message.content}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Analyze pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))