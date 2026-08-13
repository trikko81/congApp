import os
import sys
import json
import gzip
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.vector_store import VectorStoreManager

def load_bundle(bundle_path: Path) -> List[Dict[str, Any]]:
    if str(bundle_path).endswith(".gz"):
        with gzip.open(bundle_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
    else:
        with open(bundle_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    if isinstance(data, dict):
        return data.get("chunks", [])
    elif isinstance(data, list):
        return data
    return []

def ingest_bundle_file(bundle_path: Path, db_path: Optional[str] = None, batch_size: int = 500) -> int:
    resolved_db_path = db_path or os.getenv("QDRANT_DB_PATH", "./qdrant_db")
    chunks = load_bundle(bundle_path)

    if not chunks:
        print(f"Warning: No valid vector chunks found in {bundle_path}")
        return 0

    print(f"Loaded {len(chunks)} pre-computed vectors from {bundle_path.name}.")
    print(f"Indexing directly into Qdrant database ({resolved_db_path}) with ZERO local CPU/GPU load...")

    vsm = VectorStoreManager(db_path=resolved_db_path)
    indexed_count = vsm.index_batch_raw(chunks, batch_size=batch_size)

    print(f"✓ Successfully indexed {indexed_count} chunks into Qdrant storage!")
    return indexed_count

def main() -> None:
    parser = argparse.ArgumentParser(description="Local Zero-Strain Vector Stream Ingester")
    parser.add_argument("--bundle", type=str, required=True, help="Path to pre-computed vector bundle (.json or .json.gz)")
    parser.add_argument("--db-path", type=str, default="./qdrant_db", help="Path to local Qdrant database")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch insertion size")
    args = parser.parse_args()

    bundle_file = Path(args.bundle)
    if not bundle_file.is_absolute():
        bundle_file = project_root / bundle_file

    if not bundle_file.exists():
        print(f"Error: Bundle file not found: {bundle_file}")
        return

    ingest_bundle_file(bundle_file, db_path=args.db_path, batch_size=args.batch_size)

if __name__ == "__main__":
    main()
