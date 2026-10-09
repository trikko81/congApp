"""Colab pipeline helpers for downloading Virginia's official 2026 chaptered laws."""

from __future__ import annotations

import csv
import gzip
import hashlib
import html
import json
import re
import zipfile
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable


LIS_API_BASE = "https://lis.virginia.gov"
LIS_BLOB_BASE = "https://lis.blob.core.windows.net/lisfiles"
LIS_WEB_API_KEY = "FCE351B6-9BD8-46E0-B18F-5572F4CCA5B9"
DEFAULT_START_DATE = date(2026, 1, 1)


def parse_lis_date(value: str) -> date:
    """Parse LIS dates, which are published as M/D/YYYY."""
    value = (value or "").strip()
    if not value:
        raise ValueError("LIS chaptered bill is missing its Governor action date")
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unrecognized LIS date: {value!r}")


def parse_lis_bills_csv(
    csv_text: str,
    session_code: str,
    start_date: date = DEFAULT_START_DATE,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """Select approved, chaptered House/Senate bills by Governor approval date."""
    end_date = end_date or date.today()
    reader = csv.DictReader(csv_text.lstrip("\ufeff").splitlines())
    required = {
        "Bill_id", "Bill_description", "Last_governor_action_date", "Approved",
        "Vetoed", "Chapter_id",
    }
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise ValueError(f"Unexpected LIS Bills.CSV columns for {session_code}")

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in reader:
        bill_id = (row.get("Bill_id") or "").strip().upper()
        chapter_id = (row.get("Chapter_id") or "").strip().upper()
        if not re.fullmatch(r"(?:HB|SB)\d+", bill_id):
            continue
        if (row.get("Approved") or "").strip().upper() != "Y":
            continue
        if (row.get("Vetoed") or "").strip().upper() == "Y":
            continue
        if not re.fullmatch(r"CHAP\d+", chapter_id):
            continue

        approved_date = parse_lis_date(row.get("Last_governor_action_date", ""))
        if not start_date <= approved_date <= end_date:
            continue
        identity = f"{session_code}:{bill_id}"
        if identity in seen:
            continue
        seen.add(identity)
        result.append({
            "bill_id": bill_id,
            "title": (row.get("Bill_description") or "").strip(),
            "chapter_id": chapter_id,
            "chapter_number": int(chapter_id.removeprefix("CHAP")),
            "session_code": session_code,
            "approved_date": approved_date.isoformat(),
        })
    return result


def select_2026_sessions(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [
        session for session in sessions
        if int(session.get("SessionYear", 0)) == 2026
        and str(session.get("SessionCode", "")).startswith("2026")
    ]
    if not selected or not any(session.get("SessionType") == "Regular" for session in selected):
        raise RuntimeError("LIS did not return the 2026 regular session; refusing to produce a partial export")
    return sorted(selected, key=lambda session: session["SessionCode"])


class _LISHTMLText(HTMLParser):
    """Convert chapter HTML to readable text while retaining struck text markers."""

    BLOCK_TAGS = {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "br"}
    SKIP_TAGS = {"script", "style", "noscript"}
    STRIKE_TAGS = {"del", "s", "strike"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0
        self.strike_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in self.STRIKE_TAGS:
            self.parts.append(" ~~")
            self.strike_depth += 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")
        else:
            # LIS chapter HTML sometimes wraps individual words/phrases in spans.
            # Keep boundaries so adjacent inline elements don't become "enactedby".
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in self.STRIKE_TAGS and self.strike_depth:
            self.parts.append("~~ ")
            self.strike_depth -= 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")
        else:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)


def lis_html_to_text(source_html: str) -> str:
    parser = _LISHTMLText()
    parser.feed(source_html or "")
    text = html.unescape("".join(parser.parts))
    # The public LIS API currently returns section signs as U+FFFD in a few HTML strings.
    text = text.replace("\ufffd\ufffd", "§§")
    text = re.sub(r"\ufffd(?=\s*(?:\d|§))", "§", text)
    lines = [re.sub(r"[\t \xa0]+", " ", line).strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    enactment_clause = re.compile(
        r"Be\s+it\s+enacted\s+by\s+the\s+General\s+Assembly\s+of\s+Virginia\s*:",
        re.IGNORECASE,
    )
    if not enactment_clause.search(text):
        preview = text[:500].replace("\n", " | ")
        raise ValueError(
            "Chapter text is empty or missing the official enactment clause; "
            f"extracted {len(text)} characters. Beginning of extracted text: {preview!r}"
        )
    if len(text) < 120:
        raise ValueError("Chapter text is unexpectedly short")
    return text


def split_legal_text(text: str, target_chars: int = 1800, overlap_chars: int = 200) -> list[str]:
    """Split text on word boundaries, retaining a small overlap between chunks."""
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start
        size = 0
        while end < len(words) and (size + len(words[end]) + (1 if end > start else 0) <= target_chars or end == start):
            size += len(words[end]) + (1 if end > start else 0)
            end += 1
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        next_start = end
        overlap_size = 0
        while next_start > start and overlap_size < overlap_chars:
            next_start -= 1
            overlap_size += len(words[next_start]) + 1
        start = max(start + 1, next_start)
    return chunks


def make_qdrant_chunks(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Build text-only CongApp payloads; local stream_ingest computes vectors."""
    text_chunks = split_legal_text(record["text"])
    pdf_name = f"Virginia_{record['session_code']}_{record['bill_id']}_{record['chapter_id']}.pdf"
    result = []
    for index, text_chunk in enumerate(text_chunks, start=1):
        chunk_id = ":".join(("Virginia", record["session_code"], record["bill_id"], record["chapter_id"], str(index)))
        result.append({
            "chunk_id": chunk_id,
            "doc_title": pdf_name,
            "text_chunk": text_chunk,
            "page": index,
            "paragraph": index,
            "section": f"Acts of Assembly {record['chapter_id']}",
            "ordinance_id": record["bill_id"],
            "date": record["approved_date"],
            "state": "Virginia",
            "bill_id": record["bill_id"],
            "chapter_id": record["chapter_id"],
            "session_code": record["session_code"],
            "source_url": record["source_url"],
            "vector": None,
        })
    return result


def write_law_pdf(record: dict[str, Any], chunks: list[dict[str, Any]], output_path: Path) -> None:
    """Write a paginated PDF with one indexed text chunk per page."""
    import pymupdf

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page_rect = pymupdf.paper_rect("letter")
    content_rect = page_rect + (44, 42, -44, -42)
    writer = pymupdf.DocumentWriter(str(output_path))
    page_count = 0
    try:
        for index, chunk in enumerate(chunks, start=1):
            top = (
                f"<h1>{html.escape(record['bill_id'])} — Chapter {record['chapter_number']}</h1>"
                f"<p><b>{html.escape(record['title'])}</b></p>"
                f"<p>Approved {html.escape(record['approved_date'])} · Session {html.escape(record['session_code'])}</p>"
                f"<p><a href=\"{html.escape(record['source_url'], quote=True)}\">Official LIS chapter text</a></p>"
                f"<p><b>Text section {index} of {len(chunks)}</b></p><hr/>"
            )
            body = html.escape(chunk["text_chunk"]).replace("\n", "<br/>")
            markup = (
                "<html><head><style>body{font-family:sans-serif;font-size:9pt;line-height:1.3}"
                "h1{font-size:15pt;color:#16324f}p{margin:5pt 0}a{color:#245b86}</style></head>"
                f"<body>{top}<p>{body}</p></body></html>"
            )
            story = pymupdf.Story(html=markup)
            more = True
            start_page = page_count + 1
            while more:
                device = writer.begin_page(page_rect)
                more, _filled = story.place(content_rect)
                story.draw(device)
                writer.end_page()
                page_count += 1
            chunk["page"] = start_page
    finally:
        writer.close()


def save_exports(records: list[dict[str, Any]], output_dir: Path, end_date: date) -> Path:
    """Write PDFs, JSONL archive, text-only Qdrant bundle, manifest, and ZIP."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir = output_dir / "pdfs"
    all_chunks: list[dict[str, Any]] = []
    jsonl_path = output_dir / "virginia_2026_enacted_laws.jsonl"

    with jsonl_path.open("w", encoding="utf-8", newline="\n") as archive:
        for record in records:
            chunks = make_qdrant_chunks(record)
            pdf_path = pdf_dir / f"Virginia_{record['session_code']}_{record['bill_id']}_{record['chapter_id']}.pdf"
            write_law_pdf(record, chunks, pdf_path)
            record["pdf_file"] = pdf_path.name
            archive.write(json.dumps(record, ensure_ascii=False) + "\n")
            all_chunks.extend(chunks)

    bundle_path = output_dir / "virginia_2026_qdrant.json.gz"
    with gzip.open(bundle_path, "wt", encoding="utf-8") as bundle:
        json.dump({"total": len(all_chunks), "chunks": all_chunks}, bundle, ensure_ascii=False)

    manifest = {
        "state": "Virginia",
        "start_date": DEFAULT_START_DATE.isoformat(),
        "end_date": end_date.isoformat(),
        "records": len(records),
        "chunks": len(all_chunks),
        "sessions": sorted({record["session_code"] for record in records}),
        "source": "Virginia Legislative Information System (LIS)",
        "local_import": "python -m backend.stream_ingest --bundle virginia_2026_qdrant.json.gz",
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    zip_path = output_dir / "virginia_2026_enacted_laws_handoff.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(manifest_path, manifest_path.name)
        archive.write(jsonl_path, jsonl_path.name)
        archive.write(bundle_path, bundle_path.name)
        for pdf_path in sorted(pdf_dir.glob("*.pdf")):
            archive.write(pdf_path, f"pdfs/{pdf_path.name}")
    return zip_path


def _ensure_json_response(response: Any, label: str) -> dict[str, Any]:
    response.raise_for_status()
    try:
        data = response.json()
    except Exception as exc:
        raise RuntimeError(f"LIS returned invalid JSON for {label}") from exc
    if not isinstance(data, dict) or data.get("Success") is False:
        raise RuntimeError(f"LIS request failed for {label}: {data!r}")
    return data


def scrape_2026_laws(
    start_date: date = DEFAULT_START_DATE,
    end_date: date | None = None,
    output_dir: Path = Path("/content/virginia_2026_export"),
) -> tuple[list[dict[str, Any]], Path]:
    """Scrape session CSVs, retrieve exact chapter HTML through LIS public API, and export."""
    import httpx

    from datetime import timezone
    try:
        from zoneinfo import ZoneInfo
        today = datetime.now(ZoneInfo("America/New_York")).date()
    except Exception:
        today = datetime.now(timezone.utc).date()
    end_date = end_date or today
    if start_date > end_date:
        raise ValueError("The start date must be on or before the end date")

    headers = {"WebAPIKey": LIS_WEB_API_KEY, "Content-Type": "application/json; charset=utf-8"}
    records: list[dict[str, Any]] = []
    with httpx.Client(timeout=45.0, follow_redirects=True) as client:
        sessions_resp = client.get(f"{LIS_API_BASE}/Session/api/GetSessionShallowListAsync/", headers=headers)
        sessions_data = _ensure_json_response(sessions_resp, "2026 session list")
        sessions = select_2026_sessions(sessions_data.get("Sessions", []))

        for session in sessions:
            session_code = session["SessionCode"]
            csv_url = f"{LIS_BLOB_BASE}/{session_code}/BILLS.CSV"
            csv_response = client.get(csv_url)
            csv_response.raise_for_status()
            candidates = parse_lis_bills_csv(csv_response.text, session_code, start_date, end_date)
            for offset in range(0, len(candidates), 50):
                batch = candidates[offset:offset + 50]
                payload = {
                    "SessionCode": session_code,
                    "LegislationNumbers": [{"LegislationNumber": bill["bill_id"]} for bill in batch],
                }
                bill_list_resp = client.post(
                    f"{LIS_API_BASE}/AdvancedLegislationSearch/api/GetLegislationListAsync",
                    headers=headers,
                    json=payload,
                )
                bill_data = _ensure_json_response(bill_list_resp, f"{session_code} bill metadata")
                bills_by_id = {
                    bill.get("LegislationNumber", "").upper(): bill
                    for bill in bill_data.get("Legislations", [])
                }
                for candidate in batch:
                    bill_metadata = bills_by_id.get(candidate["bill_id"])
                    if not bill_metadata or not bill_metadata.get("LegislationID"):
                        raise RuntimeError(f"Missing LIS bill metadata for {session_code}/{candidate['bill_id']}")
                    if bill_metadata.get("ChapterNumber", "").upper() != candidate["chapter_id"]:
                        raise RuntimeError(f"Chapter number mismatch for {session_code}/{candidate['bill_id']}")

                    text_resp = client.get(
                        f"{LIS_API_BASE}/LegislationText/api/GetLegislationTextByIDAsync",
                        headers=headers,
                        params={"legislationID": bill_metadata["LegislationID"]},
                    )
                    text_data = _ensure_json_response(text_resp, f"{session_code}/{candidate['bill_id']} chapter text")
                    versions = [
                        version for version in text_data.get("TextsList", [])
                        if version.get("DocumentCode", "").upper() == candidate["chapter_id"]
                        and str(version.get("LegislationVersion", "")).lower() == "chaptered"
                    ]
                    if len(versions) != 1:
                        raise RuntimeError(
                            f"Expected one official {candidate['chapter_id']} text for "
                            f"{session_code}/{candidate['bill_id']}; found {len(versions)}"
                        )
                    official_text = lis_html_to_text(versions[0].get("DraftText", ""))
                    title = candidate["title"] or bill_metadata.get("Description", "").strip()
                    if not title:
                        raise RuntimeError(f"Missing official title for {session_code}/{candidate['bill_id']}")
                    records.append({
                        **candidate,
                        "title": title,
                        "session_name": session.get("DisplayName", session.get("SessionType", "")),
                        "text": official_text,
                        "source_url": (
                            f"{LIS_API_BASE}/bill-details/{session_code}/{candidate['bill_id']}"
                            f"/text/{candidate['chapter_id']}"
                        ),
                        "retrieved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    })

    if not records:
        raise RuntimeError("No chaptered House or Senate bills were found in the requested date range")
    identities = [(record["session_code"], record["bill_id"], record["chapter_id"]) for record in records]
    if len(identities) != len(set(identities)):
        raise RuntimeError("LIS returned duplicate chaptered bill identities")
    zip_path = save_exports(records, output_dir, end_date)
    return records, zip_path
