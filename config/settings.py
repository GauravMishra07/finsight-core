# config/settings.py
import os
from dotenv import load_dotenv

# Load environment variables from the .env file in the root directory
load_dotenv()

class Settings:
    """Centralized configuration for FinSight environment variables."""
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")

    huggingface_api_key: str = os.getenv("HUGGINGFACE_API_KEY", "")
    
    # Defaulting to finsight-enterprise as discussed, but falls back to .env if set
    pinecone_index_name: str = os.getenv("PINECONE_INDEX_NAME", "finsight-enterprise")
    
    # We will use Llama 3 70B via Groq for high-quality financial analysis
    default_model: str = os.getenv("DEFAULT_MODEL", "llama-3.3-70b-versatile")
    
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

# Export a single instance to be used across the app
settings = Settings()