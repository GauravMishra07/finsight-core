# src/rag/vector_store.py
import time
from pinecone import Pinecone, ServerlessSpec
from config.settings import settings
from config.logger import setup_logger
from typing import List, Dict, Any

logger = setup_logger(__name__)

class PineconeManager:
    EMBEDDING_DIM = 1024  # must match the embedder (multilingual-e5-large)

    def __init__(self):
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name

        existing_indexes = [index.name for index in self.pc.list_indexes()]

        if self.index_name not in existing_indexes:
            logger.info(f"Index '{self.index_name}' not found. Creating it now...")
            self.pc.create_index(
                name=self.index_name,
                dimension=self.EMBEDDING_DIM,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            while not self.pc.describe_index(self.index_name).status["ready"]:
                time.sleep(1)
            logger.info(f"Index '{self.index_name}' successfully created!")
        else:
            # Fail at startup instead of on the first user request
            actual = self.pc.describe_index(self.index_name).dimension
            if actual != self.EMBEDDING_DIM:
                raise RuntimeError(
                    f"Index '{self.index_name}' has dimension {actual}, "
                    f"but embeddings are {self.EMBEDDING_DIM}-dim."
                )

        self.index = self.pc.Index(self.index_name)
        logger.info(f"Connected to Pinecone index: {self.index_name}")

    def has_document(self, namespace: str, document_id: str) -> bool:
        """True only if the document was fully upserted (chunk_0 is written last)."""
        try:
            res = self.index.fetch(ids=[f"{document_id}_chunk_0"], namespace=namespace)
            return bool(res.vectors)
        except Exception as e:
            logger.warning(f"Cache check failed for {namespace}: {e}")
            return False  # on doubt, treat as a miss

    def delete_namespace(self, namespace: str):
        try:
            self.index.delete(delete_all=True, namespace=namespace)
        except Exception as e:
            logger.warning(f"Could not delete namespace {namespace}: {e}")

    def upsert_chunks(self, tenant_id: str, document_id: str, chunks: List[str],
                      embeddings: List[List[float]], batch_size: int = 100):
        vectors = [
            {
                "id": f"{document_id}_chunk_{i}",
                "values": emb,
                "metadata": {"text": chunk, "document_id": document_id},
            }
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]

        # Reverse batch order: the batch holding chunk_0 is written LAST,
        # so chunk_0 existing means the whole document is in.
        starts = list(range(0, len(vectors), batch_size))
        for n, start in enumerate(reversed(starts), 1):
            batch = vectors[start:start + batch_size]
            self.index.upsert(vectors=batch, namespace=tenant_id)
            logger.info(f"Upserted batch {n}/{len(starts)} (vectors {start} to {start + len(batch)})")

        logger.info(f"Successfully upserted {len(vectors)} chunks into namespace '{tenant_id}' ({document_id})")

    # search() stays exactly as it is

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