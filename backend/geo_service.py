import hashlib
from typing import List, Dict, Any, Tuple, Optional
from backend.schemas import ParcelLocation, AgendaItem

class GeoService:
    """
    GIS and GeoJSON service for mapping municipal agenda items and parcel locations.
    """

    MUNICIPAL_CENTERS = {
        "virginia beach": (36.8529, -75.9780),
        "richmond": (37.5407, -77.4360),
        "fairfax": (38.8462, -77.3064),
        "norfolk": (36.8508, -76.2859),
        "alexandria": (38.8048, -77.0469),
        "chesapeake": (36.7682, -76.2875),
        "default": (36.8529, -75.9780),
    }

    # Known street landmark anchors
    STREET_OFFSETS = {
        "elm": (0.008, 0.012),
        "main": (0.002, -0.005),
        "broad": (-0.006, 0.015),
        "oak": (0.012, -0.008),
        "atlantic": (0.004, 0.025),
        "pacific": (0.005, 0.021),
    }

    def __init__(self, default_center: Optional[Tuple[float, float]] = None) -> None:
        self.default_center = default_center or self.MUNICIPAL_CENTERS["default"]

    def _hash_offset(self, text: str) -> Tuple[float, float]:
        """Generates a small deterministic jitter [~0.5 to 2 miles] around center."""
        digest = hashlib.md5(text.encode("utf-8")).hexdigest()
        val_lat = (int(digest[:4], 16) % 1000 - 500) / 15000.0
        val_lng = (int(digest[4:8], 16) % 1000 - 500) / 15000.0
        return val_lat, val_lng

    def resolve_location(self, loc: ParcelLocation, municipality: Optional[str] = None) -> ParcelLocation:
        if loc.latitude is not None and loc.longitude is not None:
            return loc

        center = self.default_center
        if municipality:
            center = self.MUNICIPAL_CENTERS.get(municipality.lower(), self.default_center)

        key = (loc.address or loc.parcel_id or loc.raw_match).lower()

        # Check known street offsets
        matched_offset = None
        for street_name, offset in self.STREET_OFFSETS.items():
            if street_name in key:
                matched_offset = offset
                break

        if matched_offset:
            d_lat, d_lng = matched_offset
        else:
            d_lat, d_lng = self._hash_offset(key)

        loc.latitude = round(center[0] + d_lat, 6)
        loc.longitude = round(center[1] + d_lng, 6)
        return loc

    def items_to_geojson(self, items: List[AgendaItem], municipality: Optional[str] = None) -> Dict[str, Any]:
        features = []
        for item in items:
            for loc in item.locations:
                resolved_loc = self.resolve_location(loc, municipality=municipality)
                if resolved_loc.latitude is None or resolved_loc.longitude is None:
                    continue

                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [resolved_loc.longitude, resolved_loc.latitude] # GeoJSON RFC 7946 [lng, lat]
                    },
                    "properties": {
                        "id": f"{item.item_id}-{resolved_loc.parcel_id or 'loc'}",
                        "item_id": item.item_id,
                        "title": item.title,
                        "ordinance_id": item.ordinance_id,
                        "category": item.category.value,
                        "page": item.page_start,
                        "doc_title": item.doc_title,
                        "address": resolved_loc.address or resolved_loc.raw_match,
                        "parcel_id": resolved_loc.parcel_id,
                        "summary": " • ".join(item.summary_bullets) if item.summary_bullets else item.title,
                        "confidence": resolved_loc.confidence
                    }
                }
                features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features
        }
