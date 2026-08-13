"""
Google Colab & Free Compute Processing Pipeline for Virginia Legislative PDFs.
Processes large PDF files into structured metadata chunks and FastEmbed vectors (BAAI/bge-small-en-v1.5).
Exports a JSON payload package ready for batch ingestion into CongApp's Qdrant Vector Store.
"""

import os
import sys
import json
import argparse
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from typing import List, Dict, Any
import pymupdf
from fastembed import TextEmbedding


def extract_pdf_chunks(
    pdf_path: Path,
    state: str = "Virginia",
    enactment_year: int = 2020,
    chunk_size_words: int = 250,
    overlap_words: int = 25
) -> List[Dict[str, Any]]:
    doc = pymupdf.open(str(pdf_path))
    doc_title = pdf_path.name
    chunks: List[Dict[str, Any]] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        words = text.split()

        if not words:
            continue

        step = chunk_size_words - overlap_words
        if step <= 0:
            step = chunk_size_words

        para_index = 1
        for i in range(0, len(words), step):
            chunk_words = words[i : i + chunk_size_words]
            chunk_text = " ".join(chunk_words)

            chunks.append({
                "doc_title": doc_title,
                "text_chunk": chunk_text,
                "page": page_num + 1,
                "paragraph": para_index,
                "section": "Virginia General Assembly Act",
                "ordinance_id": doc_title.split(".")[0],
                "date": f"{enactment_year}-01-01",
                "state": state,
                "vector": None
            })
            para_index += 1

    doc.close()
    return chunks

def embed_chunks_fastembed(chunks: List[Dict[str, Any]], model_name: str = "BAAI/bge-small-en-v1.5") -> List[Dict[str, Any]]:
    if not chunks:
        return []

    print(f"Loading FastEmbed model ({model_name}) on Colab/Free Processor...")
    embedding_model = TextEmbedding(model_name=model_name)
    texts = [c["text_chunk"] for c in chunks]

    embeddings_gen = embedding_model.embed(texts)
    for idx, vec in enumerate(embeddings_gen):
        chunks[idx]["vector"] = vec.tolist()

    print(f"Successfully generated vectors for {len(chunks)} chunks.")
    return chunks

def main() -> None:
    parser = argparse.ArgumentParser(description="Colab / Cloud / Local Batch PDF & Legislative Ingestion Engine")
    parser.add_argument("--pdf", type=str, default=None, help="Path to single target PDF file")
    parser.add_argument("--dir", type=str, default=None, help="Path to directory containing PDF files (e.g. TEMPPDF)")
    parser.add_argument("--fetch-va", action="store_true", help="Fetch and process all Virginia legislative laws (2016-2026)")
    parser.add_argument("--output", type=str, default="notebooks/ingested_chunks.json", help="Path to save output JSON")
    parser.add_argument("--state", type=str, default="Virginia", help="State jurisdiction")
    parser.add_argument("--year", type=int, default=2020, help="Enactment year (2016-2026)")
    parser.add_argument("--api-url", type=str, default=None, help="Optional API base URL e.g. http://localhost:8001 to sync to Qdrant storage via API")
    parser.add_argument("--db-direct", action="store_true", help="Directly write vectors to local Qdrant database (qdrant_db)")
    parser.add_argument("--cleanup-pdf", action="store_true", help="Automatically delete temporary PDFs after vectors are indexed in DB")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    pdf_files: List[Path] = []

    if args.fetch_va:
        from backend.legislative_search import VirginiaLegislativeSearcher
        print("Fetching Virginia Legislative Laws (2016-2026)...")
        searcher = VirginiaLegislativeSearcher(default_state=args.state, start_year=2016, end_year=2026)
        va_docs = searcher.search(query="", limit=10)
        temp_dir = project_root / "TEMPPDF"
        temp_dir.mkdir(parents=True, exist_ok=True)
        for doc in va_docs:
            saved_pdf = searcher.download_pdf(doc, temp_dir)
            pdf_files.append(saved_pdf)
        print(f"Retrieved {len(pdf_files)} Virginia legislative documents.")

    if args.pdf:
        p = Path(args.pdf)
        if not p.is_absolute():
            p = project_root / p
        if p.exists():
            pdf_files.append(p)
        else:
            print(f"Error: PDF file {p} does not exist.")

    if args.dir:
        d = Path(args.dir)
        if not d.is_absolute():
            d = project_root / d
        if d.exists() and d.is_dir():
            for f in d.glob("*.pdf"):
                if f not in pdf_files:
                    pdf_files.append(f)
        else:
            print(f"Error: Directory {d} does not exist.")

    if not pdf_files:
        print("No PDF files found to process. Use --pdf, --dir, or --fetch-va.")
        return

    print(f"\n--- Found {len(pdf_files)} PDF file(s) to process ---")
    all_chunks: List[Dict[str, Any]] = []

    for f in pdf_files:
        extracted = extract_pdf_chunks(f, state=args.state, enactment_year=args.year)
        print(f"[{f.name}] -> Extracted {len(extracted)} chunks")
        all_chunks.extend(extracted)

    if not all_chunks:
        print("No text chunks extracted.")
        return

    embedded_chunks = embed_chunks_fastembed(all_chunks)
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = project_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload_data = {"chunks": embedded_chunks}
    with open(output_path, "w", encoding="utf-8") as out_f:
        json.dump(payload_data, out_f, indent=2)

    print(f"\nSaved {len(embedded_chunks)} vectorized chunks to {output_path.name} ({output_path.stat().st_size} bytes)")

    if args.db_direct:
        from backend.vector_store import VectorStoreManager
        db_path = project_root / "qdrant_db"
        print(f"Directly indexing {len(embedded_chunks)} chunks into Qdrant storage at {db_path}...")
        vsm = VectorStoreManager(db_path=str(db_path))
        indexed_count = vsm.index_batch_raw(embedded_chunks)
        print(f"Success! Indexed {indexed_count} total chunks into local Qdrant DB.")

    if args.api_url:
        import httpx
        endpoint = f"{args.api_url.rstrip('/')}/api/ingest/batch"
        print(f"Syncing batch directly to API server at {endpoint}...")
        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.post(endpoint, json=payload_data)
                if res.status_code == 200:
                    print(f"Success! Server indexed {res.json().get('indexed_count')} chunks into Qdrant DB.")
                else:
                    print(f"Sync warning ({res.status_code}): {res.text}")
        except Exception as e:
            print(f"Could not connect to backend server: {e}")

    if args.cleanup_pdf:
        cleaned_count = 0
        for f in pdf_files:
            try:
                f.unlink(missing_ok=True)
                cleaned_count += 1
            except Exception as e:
                print(f"Could not delete {f.name}: {e}")
        print(f"Cleaned up {cleaned_count} temporary PDF(s) from disk. (Data is stored in Qdrant DB only)")


if __name__ == "__main__":
    main()


