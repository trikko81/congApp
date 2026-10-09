import json
import sys
from datetime import date
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notebooks"))

from virginia_2026_colab_pipeline import (  # noqa: E402
    lis_html_to_text,
    parse_lis_bills_csv,
    save_exports,
    select_2026_sessions,
    split_legal_text,
)
from backend.stream_ingest import load_bundle  # noqa: E402
from backend.vector_store import VectorStoreManager  # noqa: E402
from qdrant_client.http.models import UpdateStatus  # noqa: E402


FIXTURES = Path(__file__).parent / "fixtures"


def test_notebook_embeds_the_tested_pipeline_helpers():
    notebook = json.loads((ROOT / "notebooks/virginia_recent_bills_colab.ipynb").read_text(encoding="utf-8"))
    helper_cell = next(cell for cell in notebook["cells"] if "pipeline-library" in cell.get("metadata", {}).get("tags", []))
    embedded_source = "".join(helper_cell["source"])
    source_module = (ROOT / "notebooks/virginia_2026_colab_pipeline.py").read_text(encoding="utf-8")
    assert embedded_source == source_module


def test_csv_filters_inclusive_approved_bill_window_and_deduplicates():
    csv_text = (FIXTURES / "lis_2026_bills.csv").read_text(encoding="utf-8")
    bills = parse_lis_bills_csv(
        csv_text,
        "20261",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 10, 6),
    )
    assert [(bill["bill_id"], bill["chapter_id"], bill["approved_date"]) for bill in bills] == [
        ("HB10", "CHAP0001", "2026-01-01"),
        ("SB20", "CHAP0042", "2026-10-06"),
    ]


def test_session_selection_includes_regular_and_special_but_not_other_years():
    sessions = [
        {"SessionCode": "20271", "SessionYear": 2027, "SessionType": "Regular"},
        {"SessionCode": "20262", "SessionYear": 2026, "SessionType": "Special"},
        {"SessionCode": "20261", "SessionYear": 2026, "SessionType": "Regular"},
    ]
    selected = select_2026_sessions(sessions)
    assert [session["SessionCode"] for session in selected] == ["20261", "20262"]


def test_chapter_html_extracts_full_text_and_marks_struck_language():
    source = (FIXTURES / "lis_2026_chapter.html").read_text(encoding="utf-8")
    text = lis_html_to_text(source)
    assert "Be it enacted by the General Assembly of Virginia:" in text
    assert "§ 12.3-4" in text
    assert "This unique fixture phrase proves complete extraction." in text
    assert "~~Repealed language~~" in text


def sample_record():
    text = lis_html_to_text((FIXTURES / "lis_2026_chapter.html").read_text(encoding="utf-8"))
    return {
        "bill_id": "HB10",
        "title": "First enacted act; test.",
        "chapter_id": "CHAP0001",
        "chapter_number": 1,
        "session_code": "20261",
        "session_name": "Regular Session",
        "approved_date": "2026-01-01",
        "text": text,
        "source_url": "https://lis.virginia.gov/bill-details/20261/HB10/text/CHAP0001",
        "retrieved_at": "2026-10-06T12:00:00-04:00",
    }


def test_text_chunking_covers_long_text_with_overlap():
    text = " ".join(f"word{i}" for i in range(900))
    chunks = split_legal_text(text, target_chars=300, overlap_chars=40)
    assert len(chunks) > 1
    assert chunks[0].split()[-1] in chunks[1].split()[:10]
    assert chunks[-1].split()[-1] == "word899"


def test_export_creates_complete_pdf_archive_and_text_only_qdrant_bundle(tmp_path):
    record = sample_record()
    zip_path = save_exports([record], tmp_path, date(2026, 10, 6))
    assert zip_path.exists()
    pdf_path = tmp_path / "pdfs" / "Virginia_20261_HB10_CHAP0001.pdf"
    with pymupdf.open(pdf_path) as pdf:
        pdf_text = "\n".join(page.get_text() for page in pdf)
    assert "phrase proves complete extraction" in pdf_text
    assert "Repealed language" in pdf_text

    archive_rows = [json.loads(line) for line in (tmp_path / "virginia_2026_enacted_laws.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(archive_rows) == 1
    assert archive_rows[0]["text"] == record["text"]

    bundle_chunks = load_bundle(tmp_path / "virginia_2026_qdrant.json.gz")
    assert bundle_chunks
    assert all(chunk["vector"] is None for chunk in bundle_chunks)
    assert all(chunk["state"] == "Virginia" and chunk["date"] == "2026-01-01" for chunk in bundle_chunks)
    assert all(chunk["source_url"] == record["source_url"] for chunk in bundle_chunks)
    assert bundle_chunks[0]["chunk_id"].startswith("Virginia:20261:HB10:CHAP0001:")

    import zipfile
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    assert "manifest.json" in names
    assert "virginia_2026_enacted_laws.jsonl" in names
    assert "virginia_2026_qdrant.json.gz" in names
    assert "pdfs/Virginia_20261_HB10_CHAP0001.pdf" in names


def test_local_qdrant_ingester_embeds_text_only_chunks_and_reuses_chunk_identity():
    class FakeClient:
        def __init__(self):
            self.upserts = []

        def upsert(self, **kwargs):
            self.upserts.append(kwargs)
            return type("Operation", (), {"status": UpdateStatus.COMPLETED})()

    manager = object.__new__(VectorStoreManager)
    manager.collection_name = "test"
    manager.client = FakeClient()
    manager.embed_texts = lambda texts: [[0.1, 0.2, 0.3] for _ in texts]
    payload = {
        "chunk_id": "Virginia:20261:HB10:CHAP0001:1",
        "doc_title": "Virginia_20261_HB10_CHAP0001.pdf",
        "text_chunk": "Official law text from the chaptered bill.",
        "vector": None,
    }

    assert manager.index_batch_raw([dict(payload)]) == 1
    assert manager.index_batch_raw([dict(payload)]) == 1
    first_point = manager.client.upserts[0]["points"][0]
    second_point = manager.client.upserts[1]["points"][0]
    assert first_point.id == second_point.id
    assert first_point.vector == [0.1, 0.2, 0.3]
    assert first_point.payload["chunk_id"] == payload["chunk_id"]
