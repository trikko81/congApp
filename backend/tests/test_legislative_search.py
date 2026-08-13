import os
from pathlib import Path
import pytest
from backend.legislative_search import VirginiaLegislativeSearcher, LegislativeDocument

def test_virginia_legislative_search_init() -> None:
    searcher = VirginiaLegislativeSearcher(default_state="Virginia", start_year=2016, end_year=2026)
    assert searcher.default_state == "Virginia"
    assert searcher.start_year == 2016
    assert searcher.end_year == 2026

def test_search_virginia_laws() -> None:
    searcher = VirginiaLegislativeSearcher(default_state="Virginia", start_year=2016, end_year=2026)
    results = searcher.search(query="clean energy", limit=3)
    assert isinstance(results, list)
    assert len(results) > 0
    doc = results[0]
    assert isinstance(doc, LegislativeDocument)
    assert doc.state == "Virginia"
    assert 2016 <= doc.enactment_year <= 2026
    assert doc.title != ""

def test_download_virginia_pdf(tmp_path: Path) -> None:
    searcher = VirginiaLegislativeSearcher(default_state="Virginia", start_year=2016, end_year=2026)
    results = searcher.search(query="clean energy", limit=1)
    assert len(results) > 0
    doc = results[0]
    
    downloaded_file = searcher.download_pdf(doc, target_dir=tmp_path)
    assert downloaded_file.exists()
    assert downloaded_file.suffix == ".pdf"
