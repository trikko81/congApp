import io
import pytest
from fastapi.testclient import TestClient
import pymupdf

from backend.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_feed_endpoint(client):
    response = client.get("/api/feed")
    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    assert "total" in data
    assert isinstance(data["entries"], list)

def test_feed_filtering_by_topic(client):
    response = client.get("/api/feed?topic=Zoning & Land Use")
    assert response.status_code == 200
    data = response.json()
    for item in data["entries"]:
        assert item["category"] == "Zoning & Land Use"

def test_map_parcels_endpoint(client):
    response = client.get("/api/map/parcels")
    assert response.status_code == 200
    data = response.json()
    assert data.get("type") == "FeatureCollection"
    assert "features" in data
    assert isinstance(data["features"], list)

def test_chat_endpoint_zoning_query(client):
    response = client.post(
        "/api/chat",
        json={"query": "What are the zoning variances and setback changes on North Elm Street?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "citations" in data
    assert "parcels" in data
    assert data["active_tab_suggestion"] == "zoning"

def test_chat_endpoint_general_query(client):
    response = client.post(
        "/api/chat",
        json={"query": "What is the general property tax rate or school funding?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "citations" in data

def test_upload_pdf_endpoint(client):
    # Create an in-memory PDF packet using PyMuPDF
    doc = pymupdf.open()
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((50, 50), "CITY OF VIRGINIA BEACH CITY COUNCIL AGENDA", fontsize=14)
    page1.insert_text((50, 100), "ITEM 1: ORDINANCE NO. 2026-102 RESIDENTIAL VARIANCE", fontsize=12)
    page1.insert_text((50, 120), "Variance request for parcel 104-55-A at 450 North Elm Street to reduce rear setback from 25ft to 15ft.", fontsize=10)
    
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((50, 50), "ITEM 2: RESOLUTION NO. 2026-45 TAX LEVY", fontsize=12)
    page2.insert_text((50, 80), "Resolution establishing annual tax rate of 0.99 per 100 dollars assessed valuation.", fontsize=10)

    pdf_bytes = doc.tobytes()
    doc.close()

    files = {"file": ("Sample_Council_Agenda_Test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/ingest/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_pages"] == 2
    assert data["total_items"] >= 2
    assert "entries" in data
    assert len(data["entries"]) >= 2
    assert data["parcels_found"] >= 1

def test_feed_filtering_by_municipality(client):
    response = client.get("/api/feed?municipality=Virginia Beach")
    assert response.status_code == 200
    data = response.json()
    for item in data["entries"]:
        assert "virginia beach" in item["municipality"].lower()

def test_feed_filtering_by_has_parcels(client):
    response = client.get("/api/feed?has_parcels=true")
    assert response.status_code == 200
    data = response.json()
    for item in data["entries"]:
        assert len(item["locations"]) > 0

def test_map_parcels_filtering_by_municipality(client):
    response = client.get("/api/map/parcels?municipality=Virginia Beach")
    assert response.status_code == 200
    data = response.json()
    assert "features" in data

