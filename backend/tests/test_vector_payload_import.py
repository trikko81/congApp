import json
import gzip
import tempfile
from pathlib import Path
from backend.vector_store import VectorStoreManager

def test_import_external_vectors_payload():
    vsm = VectorStoreManager(collection_name="test_recent_va", db_path=":memory:")
    
    sample_payload = {
        "chunks": [
            {
                "doc_title": "HB 101 - Virginia Clean Tech Act",
                "text_chunk": "An Act relating to clean tech investment in Virginia enacted recently.",
                "page": 1,
                "paragraph": 1,
                "section": "Virginia Act",
                "ordinance_id": "HB 101",
                "date": "2026-02-01",
                "state": "Virginia",
                "vector": [0.01] * 384
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(suffix=".json.gz", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        
    try:
        with gzip.open(tmp_path, "wt", encoding="utf-8") as f:
            json.dump(sample_payload, f)
            
        imported = vsm.import_external_vectors_payload(str(tmp_path))
        assert imported == 1
        
        # Test vector search query
        results = vsm.search(query="clean tech investment in Virginia", limit=2)
        assert len(results) >= 1
        assert "clean tech" in results[0]["payload"]["text_chunk"].lower()
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
