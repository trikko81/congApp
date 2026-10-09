"""Find recent Virginia enacted bills that explicitly mention a locality."""

from __future__ import annotations

import gzip
import json
import os
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _data_dir() -> Path:
    configured = os.getenv("VIRGINIA_ENACTED_LAWS_DIR")
    return Path(configured).expanduser().resolve() if configured else PROJECT_ROOT / "virginia_2026_handoff"


@lru_cache(maxsize=1)
def _load_dataset() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, Any]]:
    data_dir = _data_dir()
    records_path = data_dir / "virginia_2026_enacted_laws.jsonl"
    bundle_path = data_dir / "virginia_2026_qdrant.json.gz"
    manifest_path = data_dir / "manifest.json"

    if not records_path.is_file():
        raise FileNotFoundError(f"Enacted-laws archive not found: {records_path}")

    with records_path.open("r", encoding="utf-8") as source:
        records = [json.loads(line) for line in source if line.strip()]

    chunks_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if bundle_path.is_file():
        with gzip.open(bundle_path, "rt", encoding="utf-8") as source:
            bundle = json.load(source)
        for chunk in bundle.get("chunks", []):
            doc_title = chunk.get("doc_title")
            if doc_title:
                chunks_by_doc[doc_title].append({
                    "page": chunk.get("page", 1),
                    "text_chunk": chunk.get("text_chunk", ""),
                })

    manifest: dict[str, Any] = {}
    if manifest_path.is_file():
        with manifest_path.open("r", encoding="utf-8") as source:
            manifest = json.load(source)
    return records, chunks_by_doc, manifest


def _normalize_location(location: str) -> str:
    value = re.sub(r"\s+", " ", location).strip()
    value = re.sub(r",?\s*(?:VA|Virginia)$", "", value, flags=re.IGNORECASE).strip(" ,")
    value = re.sub(r"^City of\s+", "", value, flags=re.IGNORECASE)
    aliases = {
        "vb": "Virginia Beach",
        "va beach": "Virginia Beach",
    }
    return aliases.get(value.casefold(), value)


def _excerpt(text: str, match: re.Match[str], radius: int = 180) -> str:
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    excerpt = re.sub(r"\s+", " ", text[start:end]).strip()
    if start:
        excerpt = "…" + excerpt
    if end < len(text):
        excerpt += "…"
    return excerpt


def _find_active_match(text: str, pattern: re.Pattern[str]) -> re.Match[str] | None:
    """Ignore references inside ~~struck-through~~ text from LIS chapter HTML."""
    for match in pattern.finditer(text):
        if text[:match.start()].count("~~") % 2 == 0:
            return match
    return None


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def find_latest_local_bills(location: str) -> dict[str, Any]:
    normalized = _normalize_location(location)
    if len(normalized) < 3:
        raise ValueError("Enter a city or locality name with at least 3 characters.")

    records, chunks_by_doc, manifest = _load_dataset()
    pattern = re.compile(rf"\b{re.escape(normalized)}\b", re.IGNORECASE)
    matches: list[dict[str, Any]] = []

    for record in records:
        title = record.get("title", "")
        full_text = record.get("text", "")
        text_match = _find_active_match(full_text, pattern)
        title_match = pattern.search(title)
        if not text_match and not title_match:
            continue

        doc_title = record.get("pdf_file") or (
            f"Virginia_{record.get('session_code')}_{record.get('bill_id')}_{record.get('chapter_id')}.pdf"
        )
        pdf_page = 1
        excerpt = title
        for chunk in chunks_by_doc.get(doc_title, []):
            chunk_text = chunk.get("text_chunk", "")
            if text_match:
                context_start = max(0, text_match.start() - 70)
                context_end = min(len(full_text), text_match.end() + 70)
                context = _normalized_text(full_text[context_start:context_end])
                if context and context in _normalized_text(chunk_text):
                    pdf_page = int(chunk.get("page") or 1)
                    excerpt = _excerpt(full_text, text_match)
                    break
            chunk_match = _find_active_match(chunk_text, pattern)
            if chunk_match and not text_match:
                pdf_page = int(chunk.get("page") or 1)
                excerpt = _excerpt(chunk_text, chunk_match)
                break
        if text_match:
            excerpt = _excerpt(full_text, text_match)

        matches.append({
            "bill_id": record.get("bill_id", ""),
            "title": title,
            "chapter_id": record.get("chapter_id", ""),
            "approved_date": record.get("approved_date", ""),
            "doc_title": doc_title,
            "page": pdf_page,
            "source_url": record.get("source_url", ""),
            "excerpt": excerpt,
        })

    matches.sort(key=lambda item: (item["approved_date"], item["bill_id"]), reverse=True)
    if matches:
        newest_date = matches[0]["approved_date"]
        matches = [item for item in matches if item["approved_date"] == newest_date][:3]

    return {
        "location": normalized,
        "dataset_as_of": manifest.get("end_date"),
        "coverage_status": manifest.get("status", "unknown"),
        "skipped_count": manifest.get("skipped_count", 0),
        "match_scope": "explicit_locality_mention",
        "matches": matches,
    }
