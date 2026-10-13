# src/agents/extractor.py
from src.agents.state import AgentState
from src.mcp.tools.edgar_client import edgar_client
from src.rag.chunker import chunker
from src.rag.embedder import embedder
from src.rag.vector_store import vector_store
from config.logger import setup_logger

logger = setup_logger(__name__)

def extractor_node(state: AgentState) -> dict:
    ticker = state.get("ticker")
    logger.info(f"[Extractor Agent] Starting data pipeline for {ticker}")

    # 1. Cheap lookup: which filing is the latest?
    try:
        company, filing = edgar_client.get_latest_10k_filing(ticker)
    except Exception as e:
        msg = f"Extractor Failed: could not resolve {ticker}: {e}"
        logger.error(msg)
        return {"errors": [msg], "filing_chunks_indexed": False}

    if filing is None:
        msg = f"Extractor Failed: no 10-K found for {ticker}."
        logger.error(msg)
        return {"errors": [msg], "filing_chunks_indexed": False}

    accession = filing.accession_no
    namespace = f"{ticker.upper()}__{accession}"
    document_id = f"{ticker.upper()}_{accession}" 

    # 2. Cache hit: this exact filing is already embedded
    if vector_store.has_document(namespace, document_id):
        logger.info(f"[Extractor Agent] Cache hit for {namespace}. Skipping download and embedding.")
        return {"tenant_id": namespace, "filing_chunks_indexed": True}

    # 3. Cache miss: do the full pipeline
    raw_text = edgar_client.get_filing_text(filing)
    if not raw_text:
        msg = f"Extractor Failed: could not retrieve 10-K text for {ticker}."
        logger.error(msg)
        return {"errors": [msg], "filing_chunks_indexed": False}

    try:
        chunks = chunker.chunk_text(raw_text)
        embeddings = embedder.embed_documents(chunks)
        vector_store.upsert_chunks(
            tenant_id=namespace,
            document_id=document_id,
            chunks=chunks,
            embeddings=embeddings,
        )
        logger.info("[Extractor Agent] Extraction and indexing complete.")
        return {
            "tenant_id": namespace,
            "raw_filing_text": raw_text[:50000],
            "filing_chunks_indexed": True,
        }
    except Exception as e:
        logger.exception("Extractor pipeline failed")
        # Don't leave a half-filled namespace that a later request would mistake for a cache hit
        try:
            vector_store.delete_namespace(namespace)
        except Exception:
            pass
        return {"errors": [f"Extractor Failed during chunking/embedding pipeline: {e}"],
                "filing_chunks_indexed": False}