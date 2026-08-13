from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from backend.main import app

def test_batch_ingest_endpoint() -> None:
    payload = {
        "chunks": [
            {
                "doc_title": "Virginia_HB-1526_2020.pdf",
                "text_chunk": "Be it enacted by the General Assembly of Virginia: Clean Economy Act zero-carbon electricity.",
                "page": 1,
                "paragraph": 1,
                "section": "General Assembly of Virginia",
                "ordinance_id": "HB-1526",
                "date": "2020-07-01",
                "state": "Virginia",
                "vector": [0.01] * 384
            }
        ]
    }
    mock_vsm = MagicMock()
    mock_vsm.index_batch_raw.return_value = 1

    with patch("backend.main.get_vector_store_manager", return_value=mock_vsm):
        with TestClient(app) as client:
            response = client.post("/api/ingest/batch", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["indexed_count"] == 1


def test_legislative_search_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/legislative/search?query=clean energy&state=Virginia")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) > 0
        assert data["results"][0]["state"] == "Virginia"
