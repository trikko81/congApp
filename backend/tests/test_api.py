import pytest
import os
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from backend.main import app, vector_store_manager

def test_health():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

def test_search_endpoint():
    mock_search_results = [
        {
            "id": "test-uuid-1",
            "score": 0.89,
            "payload": {
                "doc_title": "S5087_Clean_Air_Act_Renewable_Biomass_Amendment.pdf",
                "page": 1,
                "paragraph": 2,
                "text_chunk": "This is a clean air act section about renewable biomass.",
                "token_count": 10,
                "metadata": {
                    "source_path": "S5087_Clean_Air_Act_Renewable_Biomass_Amendment.pdf",
                    "bbox": [10.0, 20.0, 100.0, 200.0]
                }
            }
        }
    ]

    mock_vsm = MagicMock()
    mock_vsm.search.return_value = mock_search_results

    with patch("backend.main.get_vector_store_manager", return_value=mock_vsm):
        with TestClient(app) as client:
            response = client.post(
                "/api/search",
                json={"query": "biomass", "limit": 2}
            )
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 1
            item = data["results"][0]
            assert item["id"] == "test-uuid-1"
            assert item["score"] == 0.89
            assert item["doc_title"] == "S5087_Clean_Air_Act_Renewable_Biomass_Amendment.pdf"
            assert item["page"] == 1
            assert item["paragraph"] == 2
            assert item["snippet"] == "This is a clean air act section about renewable biomass."
            assert item["bbox"] == [10.0, 20.0, 100.0, 200.0]
            assert "synthesized_answer" in data
            assert data["synthesized_answer"] is not None
            assert "citations" in data
            assert len(data["citations"]) == 1


def test_get_document_success():
    with TestClient(app) as client:
        response = client.get("/api/documents/S5087_Clean_Air_Act_Renewable_Biomass_Amendment.pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

def test_get_document_not_found():
    with TestClient(app) as client:
        response = client.get("/api/documents/non_existent_file.pdf")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

def test_get_document_empty_or_invalid():
    with TestClient(app) as client:
        response = client.get("/api/documents/%20")
        assert response.status_code in [400, 404]

def test_upload_non_pdf_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/api/ingest/upload",
            files={"file": ("agenda.txt", b"plain text content", "text/plain")}
        )
        assert response.status_code == 400
        assert "must be a pdf" in response.json()["detail"].lower()

