# src/rag/embedder.py
from langchain_pinecone import PineconeEmbeddings
from typing import List
from config.settings import settings
from config.logger import setup_logger
import os

logger = setup_logger(__name__)

class Embedder:
    """
    Generates vector embeddings for text chunks using Pinecone Serverless Inference.
    """
    def __init__(self, model_name: str = "multilingual-e5-large"):
        logger.info(f"Connecting to Pinecone Inference API for model: {model_name}...")
        
        # LangChain's Pinecone integration expects the API key in the environment
        if not os.getenv("PINECONE_API_KEY"):
            os.environ["PINECONE_API_KEY"] = settings.pinecone_api_key
            
        if not settings.pinecone_api_key:
            logger.warning("PINECONE_API_KEY environment variable not found. Embeddings will fail.")
            
        self.embeddings = PineconeEmbeddings(model=model_name)
        logger.info("Pinecone Embedding model connected successfully.")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a list of text chunks for database insertion."""
        return self.embeddings.embed_documents(texts)

    def embed_query(self, query: str) -> List[float]:
        """Embeds a single search query."""
        return self.embeddings.embed_query(query)

# Singleton instance
embedder = Embedder()