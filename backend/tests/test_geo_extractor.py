import pytest
from backend.geo_extractor import GeoParcelExtractor

def test_extract_addresses():
    extractor = GeoParcelExtractor()
    text = "Motion to approve zoning variance at 124 Main Street and 500 Oak Avenue for residential construction."
    locations = extractor.extract_locations(text)
    
    addresses = [loc.address for loc in locations if loc.address]
    assert any("124 Main" in addr for addr in addresses)
    assert any("500 Oak" in addr for addr in addresses)

def test_extract_parcels():
    extractor = GeoParcelExtractor()
    text = "Application for Tax Map Parcel 045-12-88B and APN 102-449-01 located in District 4."
    locations = extractor.extract_locations(text)
    
    parcel_ids = [loc.parcel_id for loc in locations if loc.parcel_id]
    assert "045-12-88B" in parcel_ids or "Tax Map Parcel 045-12-88B" in [str(loc.raw_match) for loc in locations]
    assert any("102-449-01" in str(loc.parcel_id or loc.raw_match) for loc in locations)

def test_extract_intersections():
    extractor = GeoParcelExtractor()
    text = "Traffic light installation at the corner of Broad St & Elm Boulevard."
    locations = extractor.extract_locations(text)
    assert len(locations) >= 1
    assert any("Broad" in str(loc.address or loc.raw_match) for loc in locations)

def test_extract_addresses_trims_trailing_punctuation():
    extractor = GeoParcelExtractor()
    text = "Located at 450 North Elm St., and 124 Main Street."
    locations = extractor.extract_locations(text)
    for loc in locations:
        if loc.address:
            assert not loc.address.endswith(".")
            assert not loc.address.endswith(",")

