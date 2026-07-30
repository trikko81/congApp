import os
import ssl
import urllib3

# 1. Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 2. Patch global SSL context
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# 3. Patch requests Session verify attribute globally
try:
    import requests
    old_merge_environment_settings = requests.Session.merge_environment_settings

    def unverified_merge_environment_settings(self, url, proxies, stream, verify, cert):
        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings["verify"] = False
        return settings

    requests.Session.merge_environment_settings = unverified_merge_environment_settings
except ImportError:
    pass

from pathlib import Path
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, UpdateStatus
from fastembed import TextEmbedding
from backend.parser import DocumentChunk

class VectorStoreManager:
    """
    Manages the Qdrant local vector database and FastEmbed embedding pipeline.
    Zero API key required for testing.
    """
    def __init__(
        self,
        collection_name: str = "ordinance_rag",
        db_path: str = "./qdrant_db",
        embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    ):
        self.collection_name = collection_name
        self.db_path = Path(db_path)
        
        # Bypass SSL Verification for model downloading (useful for Windows proxy/SSL issues)
        import os
        os.environ["HF_HUB_DISABLE_SSL_VERIFICATION"] = "1"

        # Initialize FastEmbed model (downloads automatically if not present)
        print(f"Loading FastEmbed model: {embedding_model_name}...")
        self.embedding_model = TextEmbedding(model_name=embedding_model_name)
        # BAAI/bge-small-en-v1.5 vector dimension is 384
        # Assuming other models might vary, we can fetch it or hardcode for now
        # Actually, fastembed doesn't have a direct property for dim, but BGE small is 384.
        self.vector_dim = 384
        
        # Initialize Qdrant Client (Local Disk Mode)
        print(f"Initializing Qdrant at {self.db_path.resolve()}...")
        self.client = QdrantClient(path=str(self.db_path))
        
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create the collection if it doesn't exist."""
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
        """Generate dense vectors for a list of texts using FastEmbed."""
        embeddings_generator = self.embedding_model.embed(texts)
        # fastembed returns a generator of numpy arrays, we convert them to list of floats
        return [embedding.tolist() for embedding in embeddings_generator]

    def index_chunks(self, chunks: List[DocumentChunk], batch_size: int = 100) -> None:
        """Index DocumentChunks into Qdrant in batches."""
        if not chunks:
            return

        total = len(chunks)
        print(f"Indexing {total} chunks into Qdrant...")
        
        for i in range(0, total, batch_size):
            batch = chunks[i : i + batch_size]
            texts = [chunk.text_chunk for chunk in batch]
            embeddings = self.embed_texts(texts)
            
            points = []
            for j, (chunk, vector) in enumerate(zip(batch, embeddings)):
                # We use a UUID or simple deterministic ID.
                # Here we just use an incrementing ID based on current collection count
                # But to avoid clashes, let's use a combination of doc_title + page + paragraph (hash)
                # Or just let Qdrant assign UUIDs using Python's uuid module
                import uuid
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
        """
        Search for top k chunks matching the query string.
        Optionally apply payload filters (e.g. {"doc_title": "..."}).
        """
        # Embed the query
        query_vector = list(self.embedding_model.embed([query]))[0].tolist()
        
        # Build Qdrant filter if provided
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue
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
    # Test script
    print("Testing VectorStoreManager initialization...")
    vsm = VectorStoreManager(db_path=":memory:")
    test_text = "This is a test of the vector embedding system."
    vec = vsm.embed_texts([test_text])
    print(f"Test vector dimension: {len(vec[0])}")
    print("Vector generation successful.")
