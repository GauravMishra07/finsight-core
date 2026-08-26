# src/rag/embedder.py
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from typing import List
from config.settings import settings
from config.logger import setup_logger

logger = setup_logger(__name__)

class Embedder:
    """
    Generates vector embeddings for text chunks using HuggingFace Inference API.
    """
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        logger.info(f"Connecting to HuggingFace API for embedding model: {model_name}...")
        
        # Use settings instead of os.getenv
        hf_token = settings.huggingface_api_key
        
        if not hf_token:
            logger.warning("HUGGINGFACE_API_KEY environment variable not found. API calls may fail.")
            
        self.embeddings = HuggingFaceEndpointEmbeddings(
            model=model_name,
            task="feature-extraction",
            huggingfacehub_api_token=hf_token
        )
        logger.info("Embedding model API connected successfully.")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a list of text chunks for database insertion."""
        return self.embeddings.embed_documents(texts)

    def embed_query(self, query: str) -> List[float]:
        """Embeds a single search query."""
        return self.embeddings.embed_query(query)

# Singleton instance
embedder = Embedder()