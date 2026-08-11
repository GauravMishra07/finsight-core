# src/rag/vector_store.py
import time
from pinecone import Pinecone, ServerlessSpec
from config.settings import settings
from config.logger import setup_logger
from typing import List, Dict, Any

logger = setup_logger(__name__)

class PineconeManager:
    """
    Enterprise Pinecone client with strict multi-tenant namespace isolation.
    """
    def __init__(self):
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name
        
        # Check if the index exists; if not, dynamically create it
        existing_indexes = [index.name for index in self.pc.list_indexes()]
        
        if self.index_name not in existing_indexes:
            logger.info(f"Index '{self.index_name}' not found. Creating it now (this takes a moment)...")
            self.pc.create_index(
                name=self.index_name,
                dimension=384,  # The exact vector dimension for our all-MiniLM-L6-v2 model
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            
            # Wait for the index to be fully initialized on Pinecone's servers
            while not self.pc.describe_index(self.index_name).status['ready']:
                time.sleep(1)
            logger.info(f"Index '{self.index_name}' successfully created!")

        self.index = self.pc.Index(self.index_name)
        logger.info(f"Connected to Pinecone index: {self.index_name}")

    def upsert_chunks(self, tenant_id: str, document_id: str, chunks: List[str], embeddings: List[List[float]], batch_size: int = 100):
        """
        Stores chunks in Pinecone isolated by tenant_id (Namespace) using batching
        to stay well below Pinecone's 4MB request size limit.
        """
        vectors = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            vectors.append({
                "id": f"{document_id}_chunk_{i}",
                "values": emb,
                "metadata": {"text": chunk, "document_id": document_id}
            })
        
        # Slices vector list into batches of 100 to prevent payload size errors
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch, namespace=tenant_id)
            logger.info(f"Upserted batch {i // batch_size + 1} (vectors {i} to {i + len(batch)})")
            
        logger.info(f"Successfully upserted {len(vectors)} total chunks for tenant '{tenant_id}' into document '{document_id}'")

    def search(self, tenant_id: str, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Searches ONLY within the specific tenant's namespace.
        """
        response = self.index.query(
            namespace=tenant_id,
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        return response.get("matches", [])

# Singleton instance
vector_store = PineconeManager()