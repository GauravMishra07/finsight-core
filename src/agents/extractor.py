# src/agents/extractor.py
from src.agents.state import AgentState
from src.mcp.tools.edgar_client import edgar_client
from src.rag.chunker import chunker
from src.rag.embedder import embedder
from src.rag.vector_store import vector_store
from config.logger import setup_logger

logger = setup_logger(__name__)

def extractor_node(state: AgentState) -> dict:
    """
    Node 1: Extractor Agent
    Fetches the 10-K, chunks it, embeds it, and stores it in the multi-tenant vector DB.
    """
    ticker = state.get("ticker")
    tenant_id = state.get("tenant_id")
    
    logger.info(f"[Extractor Agent] Starting data pipeline for {ticker} (Tenant: {tenant_id})")
    
    # 1. Fetch Data
    raw_text = edgar_client.fetch_latest_10k_text(ticker)
    
    if not raw_text:
        error_msg = f"Extractor Failed: Could not retrieve 10-K filing for {ticker}."
        logger.error(error_msg)
        # LangGraph automatically appends this to the 'errors' list based on our state.py logic
        return {"errors": [error_msg], "filing_chunks_indexed": False}
    
    # 2. Chunk, Embed, and Index
    try:
        logger.info(f"[Extractor Agent] Chunking {len(raw_text)} characters...")
        chunks = chunker.chunk_text(raw_text)
        
        logger.info(f"[Extractor Agent] Generating embeddings for {len(chunks)} chunks. (This may take a moment locally)...")
        embeddings = embedder.embed_documents(chunks)
        
        logger.info(f"[Extractor Agent] Upserting {len(chunks)} vectors to Pinecone (Namespace: {tenant_id})")
        vector_store.upsert_chunks(
            tenant_id=tenant_id,
            document_id=f"{ticker}_10K",
            chunks=chunks,
            embeddings=embeddings
        )
        
        logger.info("[Extractor Agent] Extraction and indexing complete.")
        
        # 3. Update the shared state
        return {
            # We store only the first 50,000 characters in active memory to prevent 
            # blowing up the LLM's context window. Full data is safely in Pinecone.
            "raw_filing_text": raw_text[:50000], 
            "filing_chunks_indexed": True
        }
        
    except Exception as e:
        error_msg = f"Extractor Failed during chunking/embedding pipeline: {str(e)}"
        logger.error(error_msg)
        return {"errors": [error_msg], "filing_chunks_indexed": False}