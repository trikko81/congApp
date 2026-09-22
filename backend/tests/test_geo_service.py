import pytest
from backend.schemas import ParcelLocation, AgendaItem, TopicCategory
from backend.geo_service import GeoService

def test_resolve_parcel_coordinates():
    service = GeoService(default_center=(36.8529, -75.9780)) # Virginia Beach default
    loc = ParcelLocation(
        raw_match="450 North Elm Street",
        address="450 North Elm Street",
        confidence=0.95
    )
    resolved = service.resolve_location(loc)
    assert resolved.latitude is not None
    assert resolved.longitude is not None
    assert 30.0 <= resolved.latitude <= 45.0
    assert -85.0 <= resolved.longitude <= -70.0

def test_generate_geojson_feature_collection():
    service = GeoService()
    items = [
        AgendaItem(
            item_id="item-1",
            doc_title="Council_Agenda_2026.pdf",
            title="Ordinance 2026-102: Elm St Rezoning",
            full_text="Rezoning for parcel 104-55-A at 450 North Elm Street.",
            category=TopicCategory.ZONING_LAND_USE,
            ordinance_id="ORD-2026-102",
            page_start=4,
            summary_bullets=["Approved setback variance from 25ft to 15ft"],
            locations=[
                ParcelLocation(raw_match="450 North Elm Street", address="450 North Elm Street"),
                ParcelLocation(raw_match="Tax Map Parcel 104-55-A", parcel_id="104-55-A")
            ]
        ),
        AgendaItem(
            item_id="item-2",
            doc_title="Council_Agenda_2026.pdf",
            title="Resolution 2026-15: General Administration",
            full_text="Minutes approval.",
            category=TopicCategory.GENERAL_ADMIN,
            page_start=1,
            locations=[] # No locations
        )
    ]

    geojson = service.items_to_geojson(items)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) >= 1
    
    first_feature = geojson["features"][0]
    assert first_feature["type"] == "Feature"
    assert first_feature["geometry"]["type"] == "Point"
    assert len(first_feature["geometry"]["coordinates"]) == 2 # [lng, lat]
    props = first_feature["properties"]
    assert props["ordinance_id"] == "ORD-2026-102"
    assert props["category"] == TopicCategory.ZONING_LAND_USE.value
    assert props["page"] == 4
    assert "Elm" in (props.get("address") or "") or "104-55-A" in (props.get("parcel_id") or "")
