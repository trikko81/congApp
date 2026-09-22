import argparse
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add workspace to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agenda_parser import AgendaParser
from backend.geo_service import GeoService
from backend.topic_classifier import TopicClassifier
from backend.vector_store import VectorStoreManager

def ingest_agenda_pdf(pdf_path: str, qdrant_path: str = "./qdrant_db"):
    path = Path(pdf_path)
    if not path.exists():
        print(f"Error: PDF packet not found: {path}")
        sys.exit(1)

    print(f"==================================================")
    print(f"[TownWatch / CivicFeed] Agenda Ingestion Engine")
    print(f"Document: {path.name} ({path.stat().st_size / 1024:.1f} KB)")
    print(f"==================================================")

    start_t = time.time()

    parser = AgendaParser()
    geo_service = GeoService()
    
    print("\n[1/4] Segmenting agenda items and parsing layout...")
    items = parser.parse_pdf_agenda(path)
    print(f"[OK] Found {len(items)} discrete agenda items.")

    print("\n[2/4] Extracting geographic parcels and geocoding...")
    total_parcels = 0
    for idx, item in enumerate(items, 1):
        if item.locations:
            total_parcels += len(item.locations)
            for loc in item.locations:
                resolved = geo_service.resolve_location(loc)
                print(f"   * Item {idx}: Found '{resolved.address or resolved.parcel_id}' -> [{resolved.longitude}, {resolved.latitude}]")

    print(f"[OK] Resolved {total_parcels} parcel/street coordinates.")

    print("\n[3/4] Categorizing topics and generating neutral resident summaries...")
    topic_counts = {}
    for item in items:
        cat_name = item.category.value
        topic_counts[cat_name] = topic_counts.get(cat_name, 0) + 1

    for cat, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   * {cat}: {count} item(s)")

    print("\n[4/4] Indexing into Qdrant Vector Store...")
    try:
        vsm = VectorStoreManager(db_path=qdrant_path)
        chunks = []
        for item in items:
            chunks.append({
                "doc_title": path.name,
                "text_chunk": f"{item.title}\n{item.full_text}",
                "page": item.page_start,
                "paragraph": 1,
                "section": item.category.value,
                "ordinance_id": item.ordinance_id,
                "summary_bullets": item.summary_bullets
            })
        indexed = vsm.index_batch_raw(chunks)
        print(f"[OK] Indexed {indexed} chunks into Qdrant collection '{vsm.collection_name}'.")
    except Exception as exc:
        print(f"Notice: Qdrant indexing notice: {exc}")

    elapsed = time.time() - start_t
    print(f"\n[DONE] Ingestion complete in {elapsed:.2f}s!")
    print(f"--------------------------------------------------")
    print(f"Summary: {len(items)} items | {total_parcels} parcels | {len(topic_counts)} categories")
    print(f"--------------------------------------------------\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TownWatch Civic Agenda Ingestion CLI")
    parser.add_argument("--file", "-f", default="TEMPPDF/sample_agendas/Virginia_Beach_City_Council_Agenda_2026.pdf", help="Path to agenda PDF")
    parser.add_argument("--qdrant", "-q", default="./qdrant_db", help="Path to Qdrant storage")
    args = parser.parse_args()

    ingest_agenda_pdf(args.file, args.qdrant)
