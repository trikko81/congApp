import os
import ssl
import json
import uuid
from pathlib import Path

from typing import List, Dict, Any, Optional
import urllib3
import httpx

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
os.environ["HF_HUB_DISABLE_SSL_VERIFICATION"] = "1"
os.environ["CURL_CA_BUNDLE"] = ""

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

_orig_httpx_init = httpx.Client.__init__
def _patched_httpx_init(self, *args, **kwargs):
    kwargs['verify'] = False
    _orig_httpx_init(self, *args, **kwargs)
httpx.Client.__init__ = _patched_httpx_init



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

    def index_batch_raw(self, chunk_payloads: List[Dict[str, Any]], batch_size: int = 100) -> int:
        if not chunk_payloads:
            return 0

        total = len(chunk_payloads)
        print(f"Indexing {total} raw batch chunks into Qdrant...")
        indexed_count = 0

        for i in range(0, total, batch_size):
            batch = chunk_payloads[i : i + batch_size]
            texts_to_embed = []
            embed_indices = []

            for idx, item in enumerate(batch):
                if not item.get("vector"):
                    texts_to_embed.append(item.get("text_chunk", ""))
                    embed_indices.append(idx)

            if texts_to_embed:
                computed_vectors = self.embed_texts(texts_to_embed)
                for idx, vec in zip(embed_indices, computed_vectors):
                    batch[idx]["vector"] = vec

            points = []
            for item in batch:
                point_id = str(uuid.uuid4())
                vector = item.get("vector")
                payload = {k: v for k, v in item.items() if k != "vector"}
                if "doc_title" in payload and "source_doc" not in payload:
                    payload["source_doc"] = payload["doc_title"]
                points.append(PointStruct(id=point_id, vector=vector, payload=payload))

            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                wait=True,
                points=points
            )
            if operation_info.status == UpdateStatus.COMPLETED:
                indexed_count += len(batch)

        print(f"Successfully indexed {indexed_count} total raw batch chunks.")
        return indexed_count


    def import_external_vectors_payload(self, file_path: str, batch_size: int = 200) -> int:
        """Import pre-computed vectors and metadata chunks (e.g. from Google Colab GPU run)."""
        import gzip
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Payload file not found: {file_path}")

        if p.name.endswith(".gz"):
            with gzip.open(p, "rt", encoding="utf-8") as f:
                data = json.load(f)
        else:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)

        chunks = data if isinstance(data, list) else data.get("chunks", data.get("bills", []))
        if not chunks:
            print("No vector chunks found in payload.")
            return 0

        total_imported = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            points = []
            for item in batch:
                vec = item.get("vector")
                if vec is None:
                    continue
                point_id = str(uuid.uuid4())
                payload = {k: v for k, v in item.items() if k != "vector"}
                points.append(PointStruct(id=point_id, vector=vec, payload=payload))

            if points:
                self.client.upsert(collection_name=self.collection_name, points=points, wait=True)
                total_imported += len(points)

        print(f"Successfully imported {total_imported} pre-computed vectors into '{self.collection_name}'.")
        return total_imported

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

