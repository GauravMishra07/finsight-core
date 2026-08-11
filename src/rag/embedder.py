# src/rag/embedder.py
from langchain_huggingface import HuggingFaceEmbeddings
from typing import List
from config.logger import setup_logger

logger = setup_logger(__name__)

class Embedder:
    """
    Locally generates vector embeddings for text chunks using HuggingFace.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info(f"Loading local embedding model: {model_name}...")
        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
        logger.info("Embedding model loaded successfully.")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a list of text chunks for database insertion."""
        return self.embeddings.embed_documents(texts)

    def embed_query(self, query: str) -> List[float]:
        """Embeds a single search query."""
        return self.embeddings.embed_query(query)

# Singleton instance
embedder = Embedder()