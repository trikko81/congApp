from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import re
import uuid
import pymupdf

from backend.schemas import AgendaItem, TopicCategory, ParcelLocation
from backend.geo_extractor import GeoParcelExtractor
from backend.topic_classifier import TopicClassifier

class AgendaParser:
    """
    Layout-aware parser that segments municipal and school board PDF packets into structured AgendaItems.
    """
    
    # Common agenda item header patterns
    ITEM_HEADER_PATTERNS = [
        re.compile(r"^(?:ITEM|ACTION ITEM|AGENDA ITEM|CONSENT ITEM|BUSINESS ITEM|ORDER OF BUSINESS)\s*[\#\d\.\:\-]+.*", re.IGNORECASE),
        re.compile(r"^(?:ORDINANCE\s+(?:NO\.|NUMBER)?|RESOLUTION\s+(?:NO\.|NUMBER)?)\s*[\d\.\:\-]+.*", re.IGNORECASE),
        re.compile(r"^(?:PUBLIC HEARING|OLD BUSINESS|NEW BUSINESS|PRESENTATION|REPORT OF)\s*[\:\-]?.*", re.IGNORECASE),
        re.compile(r"^(?:BOARD OF EDUCATION|SUPERINTENDENT\'S REPORT|FINANCIAL REPORT|ZONING VARIANCE)\s*[\:\-]?.*", re.IGNORECASE),
    ]

    ORDINANCE_ID_PATTERN = re.compile(
        r"\b(?:ORDINANCE\s+(?:NO\.|NUMBER)?\s*|RESOLUTION\s+(?:NO\.|NUMBER)?\s*|ORD\s*#?|RES\s*#?)([\d]{4}[\-\s][\dA-Z]+|[\dA-Z\-]{3,15})\b",
        re.IGNORECASE
    )

    def __init__(
        self,
        geo_extractor: Optional[GeoParcelExtractor] = None,
        topic_classifier: Optional[TopicClassifier] = None
    ) -> None:
        self.geo_extractor = geo_extractor or GeoParcelExtractor()
        self.topic_classifier = topic_classifier or TopicClassifier()

    def _is_header(self, line: str) -> bool:
        line_clean = line.strip()
        if not line_clean or len(line_clean) < 3:
            return False
        for pattern in self.ITEM_HEADER_PATTERNS:
            if pattern.match(line_clean):
                return True
        return False

    def _extract_ordinance_id(self, text: str) -> Optional[str]:
        match = self.ORDINANCE_ID_PATTERN.search(text)
        if match:
            return match.group(0).strip()
        return None

    def segment_text(self, raw_text: str, doc_title: str) -> List[AgendaItem]:
        """
        Segments raw or block-extracted text into AgendaItem objects based on header boundaries.
        """
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if not lines:
            return []

        items: List[AgendaItem] = []
        current_title: Optional[str] = None
        current_lines: List[str] = []
        start_page: int = 1

        for line in lines:
            if self._is_header(line):
                # Save previous item if exists
                if current_title and current_lines:
                    full_text = "\n".join(current_lines)
                    locations = self.geo_extractor.extract_locations(full_text)
                    ord_id = self._extract_ordinance_id(current_title + " " + full_text)
                    classification = self.topic_classifier.classify_and_summarize(current_title + "\n" + full_text)
                    items.append(AgendaItem(
                        item_id=str(uuid.uuid4())[:8],
                        doc_title=doc_title,
                        title=current_title,
                        full_text=full_text,
                        category=classification.category,
                        summary_bullets=classification.summary_bullets,
                        ordinance_id=ord_id,
                        page_start=start_page,
                        page_end=start_page,
                        locations=locations
                    ))
                current_title = line
                current_lines = [line]
            else:
                if current_title:
                    current_lines.append(line)
                else:
                    # Header before first explicit item match (e.g. Call to order / Notice)
                    current_title = line
                    current_lines = [line]

        # Flush final item
        if current_title and current_lines:
            full_text = "\n".join(current_lines)
            locations = self.geo_extractor.extract_locations(full_text)
            ord_id = self._extract_ordinance_id(current_title + " " + full_text)
            classification = self.topic_classifier.classify_and_summarize(current_title + "\n" + full_text)
            items.append(AgendaItem(
                item_id=str(uuid.uuid4())[:8],
                doc_title=doc_title,
                title=current_title,
                full_text=full_text,
                category=classification.category,
                summary_bullets=classification.summary_bullets,
                ordinance_id=ord_id,
                page_start=start_page,
                page_end=start_page,
                locations=locations
            ))

        return items

    def detect_municipality(self, text: str, filename: str = "") -> str:
        candidates = [
            "Virginia Beach", "Richmond", "Fairfax", "Norfolk",
            "Alexandria", "Chesapeake", "Arlington", "Roanoke",
            "Hampton", "Newport News", "Portsmouth", "Williamsburg"
        ]
        norm_filename = re.sub(r'[\_\-\.]+', ' ', filename)
        combined = f"{norm_filename} {text[:2000]}"
        for city in candidates:
            if re.search(rf"\b{re.escape(city)}\b", combined, re.IGNORECASE):
                return city
        return "Virginia Beach"


    def detect_meeting_date(self, text: str) -> Optional[str]:
        date_pattern = re.compile(
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
            re.IGNORECASE
        )
        match = date_pattern.search(text[:3000])
        if match:
            return match.group(0).strip()
        iso_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text[:3000])
        if iso_match:
            return iso_match.group(1).strip()
        return None

    def parse_pdf_agenda(self, pdf_path: str | Path) -> List[AgendaItem]:
        """
        Reads a PDF packet, tracks page offsets for each item, and segments into AgendaItems with categories and parcels.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF packet not found: {path}")

        doc_title = path.name
        page_tagged_lines: List[Tuple[int, str]] = []

        with pymupdf.open(path) as doc:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                for line in text.splitlines():
                    clean = line.strip()
                    if clean:
                        page_tagged_lines.append((page_num + 1, clean))

        if not page_tagged_lines:
            return []

        items: List[AgendaItem] = []
        current_title: Optional[str] = None
        current_lines: List[str] = []
        current_page_start: int = 1
        current_page_end: int = 1

        for page_idx, line in page_tagged_lines:
            if self._is_header(line):
                if current_title and current_lines:
                    full_text = "\n".join(current_lines)
                    locations = self.geo_extractor.extract_locations(full_text)
                    ord_id = self._extract_ordinance_id(current_title + " " + full_text)
                    classification = self.topic_classifier.classify_and_summarize(current_title + "\n" + full_text)
                    items.append(AgendaItem(
                        item_id=str(uuid.uuid4())[:8],
                        doc_title=doc_title,
                        title=current_title,
                        full_text=full_text,
                        category=classification.category,
                        summary_bullets=classification.summary_bullets,
                        ordinance_id=ord_id,
                        page_start=current_page_start,
                        page_end=current_page_end,
                        locations=locations
                    ))
                current_title = line
                current_lines = [line]
                current_page_start = page_idx
                current_page_end = page_idx
            else:
                if current_title:
                    current_lines.append(line)
                    current_page_end = page_idx
                else:
                    current_title = line
                    current_lines = [line]
                    current_page_start = page_idx
                    current_page_end = page_idx

        # Flush final item
        if current_title and current_lines:
            full_text = "\n".join(current_lines)
            locations = self.geo_extractor.extract_locations(full_text)
            ord_id = self._extract_ordinance_id(current_title + " " + full_text)
            classification = self.topic_classifier.classify_and_summarize(current_title + "\n" + full_text)
            items.append(AgendaItem(
                item_id=str(uuid.uuid4())[:8],
                doc_title=doc_title,
                title=current_title,
                full_text=full_text,
                category=classification.category,
                summary_bullets=classification.summary_bullets,
                ordinance_id=ord_id,
                page_start=current_page_start,
                page_end=current_page_end,
                locations=locations
            ))

        return items

