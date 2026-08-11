# api.py
from fastapi import FastAPI, HTTPException
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

app = FastAPI(title="FinSight Underwriting API")
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
@app.post("/api/v1/analyze")
async def generate_memo(request: AnalyzeRequest):
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
            "upcoming_projects": None,
            "final_memo": None,
            "errors": []
        }
        
        # Run LangGraph pipeline
        final_state = finsight_graph.invoke(initial_state)
        
        if final_state.get("errors"):
            raise HTTPException(status_code=500, detail=str(final_state["errors"]))
            
        return final_state
    
    except Exception as e:
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))