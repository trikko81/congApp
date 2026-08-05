import os
import ssl
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
import urllib3

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    UpdateStatus,
    Filter,
    FieldCondition,
    MatchValue
)
from fastembed import TextEmbedding
from backend.parser import DocumentChunk

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

os.environ["HF_HUB_DISABLE_SSL_VERIFICATION"] = "1"


class VectorStoreManager:
    """Manages local Qdrant vector database and FastEmbed embedding pipeline."""

    def __init__(
        self,
        collection_name: str = "ordinance_rag",
        db_path: str = "./qdrant_db",
        embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    ):
        self.collection_name = collection_name
        self.db_path = Path(db_path)
        
        print(f"Loading FastEmbed model: {embedding_model_name}...")
        self.embedding_model = TextEmbedding(model_name=embedding_model_name)
        self.vector_dim = 384
        
        print(f"Initializing Qdrant at {self.db_path.resolve()}...")
        self.client = QdrantClient(path=str(self.db_path))
        
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            print(f"Creating collection '{self.collection_name}' with dimension {self.vector_dim}...")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_dim, distance=Distance.COSINE),
            )
        else:
            print(f"Collection '{self.collection_name}' already exists.")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings_generator = self.embedding_model.embed(texts)
        return [embedding.tolist() for embedding in embeddings_generator]

    def index_chunks(self, chunks: List[DocumentChunk], batch_size: int = 100) -> None:
        if not chunks:
            return

        total = len(chunks)
        print(f"Indexing {total} chunks into Qdrant...")
        
        for i in range(0, total, batch_size):
            batch = chunks[i : i + batch_size]
            texts = [chunk.text_chunk for chunk in batch]
            embeddings = self.embed_texts(texts)
            
            points = []
            for chunk, vector in zip(batch, embeddings):
                point_id = str(uuid.uuid4())
                payload = chunk.to_dict()
                points.append(PointStruct(id=point_id, vector=vector, payload=payload))
                
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                wait=True,
                points=points
            )
            
            if operation_info.status != UpdateStatus.COMPLETED:
                print(f"Warning: Batch {i//batch_size + 1} status: {operation_info.status}")
            else:
                print(f"Indexed batch {i//batch_size + 1} ({len(batch)} chunks)")
                
        print(f"Successfully indexed {total} total chunks.")

    def search(self, query: str, limit: int = 5, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        query_vector = list(self.embedding_model.embed([query]))[0].tolist()
        
        qdrant_filter = None
        if filter_dict:
            must_conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_dict.items()
            ]
            qdrant_filter = Filter(must=must_conditions)
            
        search_response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            query_filter=qdrant_filter,
            with_payload=True
        )
        
        results = []
        for scored_point in search_response.points:
            results.append({
                "id": scored_point.id,
                "score": scored_point.score,
                "payload": scored_point.payload
            })
            
        return results


if __name__ == "__main__":
    print("Testing VectorStoreManager initialization...")
    vsm = VectorStoreManager(db_path=":memory:")
    test_text = "This is a test of the vector embedding system."
    vec = vsm.embed_texts([test_text])
    print(f"Test vector dimension: {len(vec[0])}")
    print("Vector generation successful.")

