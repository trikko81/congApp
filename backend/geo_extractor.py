from typing import List, Optional
import re
from backend.schemas import ParcelLocation

class GeoParcelExtractor:
    # Matches street addresses e.g., "124 Main Street", "450 North Elm St."
    STREET_SUFFIXES = r"(?:Street|St\b|Avenue|Ave\b|Road|Rd\b|Boulevard|Blvd\b|Drive|Dr\b|Lane|Ln\b|Court|Ct\b|Way\b|Place|Pl\b|Terrace|Ter\b|Highway|Hwy\b|Parkway|Pkwy\b)"
    ADDRESS_REGEX = re.compile(
        r"\b(\d{1,6}\s+(?:[NSEW]\b\s*|North\s+|South\s+|East\s+|West\s+)?[A-Za-z0-9\.\s]{1,30}?\s*" + STREET_SUFFIXES + r"\.?)",
        re.IGNORECASE
    )
    
    # Matches parcel identifiers e.g., "Tax Map Parcel 045-12-88B", "APN: 102-449-01", "Parcel ID 12-44"
    PARCEL_REGEX = re.compile(
        r"\b(?:Tax\s+Map\s+Parcel|Tax\s+Parcel|Parcel\s+ID|APN|PIN|Folio|Lot|Block)[\s#:]+([A-Z0-9\-\.\/]+)\b",
        re.IGNORECASE
    )
    
    # Matches street intersections e.g., "corner of Broad St & Elm Boulevard"
    INTERSECTION_REGEX = re.compile(
        r"\b([A-Z][a-zA-Z0-9\.\s]{1,25}\s+" + STREET_SUFFIXES + r")\s+(?:and|&|at)\s+([A-Z][a-zA-Z0-9\.\s]{1,25}\s+" + STREET_SUFFIXES + r")\b",
        re.IGNORECASE
    )

    def extract_locations(self, text: str) -> List[ParcelLocation]:
        if not text:
            return []
        
        results: List[ParcelLocation] = []
        seen = set()

        # 1. Extract standard street addresses
        for match in self.ADDRESS_REGEX.finditer(text):
            raw = match.group(1).strip()
            clean_addr = raw.rstrip(".,;:").strip()
            if clean_addr.lower() not in seen:
                seen.add(clean_addr.lower())
                results.append(ParcelLocation(
                    raw_match=raw,
                    address=clean_addr,
                    confidence=0.95
                ))

        # 2. Extract parcel / APN / Tax Map IDs
        for match in self.PARCEL_REGEX.finditer(text):
            full_raw = match.group(0).strip()
            parcel_val = match.group(1).strip().rstrip(".,;:")
            if parcel_val.lower() not in seen:
                seen.add(parcel_val.lower())
                results.append(ParcelLocation(
                    raw_match=full_raw,
                    parcel_id=parcel_val,
                    confidence=0.90
                ))

        # 3. Extract street intersections
        for match in self.INTERSECTION_REGEX.finditer(text):
            street1 = match.group(1).strip().rstrip(".,;:")
            street2 = match.group(2).strip().rstrip(".,;:")
            intersection = f"{street1} & {street2}"
            if intersection.lower() not in seen:
                seen.add(intersection.lower())
                results.append(ParcelLocation(
                    raw_match=match.group(0).strip(),
                    address=intersection,
                    confidence=0.85
                ))

        return results
