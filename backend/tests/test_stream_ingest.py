import pytest
import json
import gzip
from pathlib import Path
from unittest.mock import MagicMock, patch
from backend.stream_ingest import ingest_bundle_file

def test_ingest_json_bundle(tmp_path: Path) -> None:
    sample_data = {
        "chunks": [
            {
                "doc_title": "Virginia_HB_894_2016.pdf",
                "text_chunk": "Virginia Solar Energy Development Act enacted 2016.",
                "page": 1,
                "paragraph": 1,
                "section": "Chapter 748",
                "ordinance_id": "HB 894",
                "date": "2016-07-01",
                "state": "Virginia",
                "vector": [0.05] * 384
            }
        ]
    }
    json_file = tmp_path / "bundle.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(sample_data, f)

    mock_vsm = MagicMock()
    mock_vsm.index_batch_raw.return_value = 1

    with patch("backend.stream_ingest.VectorStoreManager", return_value=mock_vsm):
        count = ingest_bundle_file(json_file, db_path=":memory:")
        assert count == 1
        mock_vsm.index_batch_raw.assert_called_once()

def test_ingest_gzip_bundle(tmp_path: Path) -> None:
    sample_data = {
        "chunks": [
            {
                "doc_title": "Virginia_SB_100_2026.pdf",
                "text_chunk": "Virginia Data Center Clean Power Act enacted 2026.",
                "page": 1,
                "paragraph": 1,
                "section": "Chapter 10",
                "ordinance_id": "SB 100",
                "date": "2026-07-01",
                "state": "Virginia",
                "vector": [0.02] * 384
            }
        ]
    }
    gz_file = tmp_path / "bundle.json.gz"
    with gzip.open(gz_file, "wt", encoding="utf-8") as f:
        json.dump(sample_data, f)

    mock_vsm = MagicMock()
    mock_vsm.index_batch_raw.return_value = 1

    with patch("backend.stream_ingest.VectorStoreManager", return_value=mock_vsm):
        count = ingest_bundle_file(gz_file, db_path=":memory:")
        assert count == 1
