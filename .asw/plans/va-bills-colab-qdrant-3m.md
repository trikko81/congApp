# Virginia Bills (Past 3 Months) GPU Colab & Qdrant Ingestion Plan

## TL;DR
Build an automated ingestion pipeline that scrapes all chaptered/passed legislation across Virginia from the past 3 months (via Virginia LIS and Open States / LegiScan APIs), processes full text and generates 384-dimensional dense vectors on Google Colab (leveraging T4/A100 GPU compute via `fastembed` with `BAAI/bge-small-en-v1.5`), and syncs the resulting payload directly into CongApp's local/remote Qdrant vector database (`ordinance_rag` collection).

## Objective
Enable users to harvest, embed, and query all Virginia legislation enacted within the last 3 months using GPU-accelerated Colab processing and seamless Qdrant vector ingestion without taxing local CPU/RAM resources.

## Non-goals
- Modifying the core frontend chat or PDF viewer UI logic.
- Scraping non-Virginia state jurisdictions during this specific job.
- Altering the existing 384-dim cosine distance schema in `vector_store.py`.

## Discovery
- `notebooks/virginia_crawler.py`: Contains LIS parser and session code mappings for Virginia legislative sessions.
- `notebooks/virginia_all_laws_colab.ipynb` & `notebooks/colab_runner.py`: Existing Colab execution pipelines with `fastembed` (`BAAI/bge-small-en-v1.5`).
- `backend/vector_store.py`: Local Qdrant manager expecting 384-dim vectors (`ordinance_rag` collection).
- `backend/legislative_search.py`: Query interface for legislative chunk lookup and semantic similarity search.

## Decisions
- **Source Filtering (3-Month Window)**: Target bills enacted or chaptered within the rolling 90-day window (e.g., current 2025/2026 active session batches and special sessions).
- **Embedding Model**: `BAAI/bge-small-en-v1.5` (384-dim, FastEmbed ONNX Runtime GPU support in Colab).
- **Colab Export & Sync Formats**: Produce both a compressed vector snapshot (`va_bills_past_3_months_qdrant.json.gz`) downloadable from Colab, and an optional direct Qdrant REST upload cell for immediate database synchronization.
- **Chunking Strategy**: 250-word chunks with 25-word overlap, preserving chapter metadata, bill ID, sponsor, date of enactment, and official LIS full text URL.

## TODOs
- [ ] **Task 1: Virginia 3-Month Bill Scraper & Session Filter Module**
  - Files: `backend/legislative_search.py`, `notebooks/virginia_crawler.py`
  - RED: Write a unit test `backend/tests/test_va_recent_bills.py` verifying that bills are correctly fetched and filtered strictly to the past 90 days.
  - GREEN: Implement `fetch_va_recent_passed_bills(days=90)` scraping approved acts and LIS chaptered lists, pulling full statutory text.
  - Real-surface QA: Execute `python -m pytest backend/tests/test_va_recent_bills.py` and confirm date boundary parsing.
  - Evidence: `backend/tests/test_va_recent_bills.py` logs passing.
  - Cleanup: Remove any temporary sample response dumps.
  - Commit: YES (`feat(ingest): add 3-month Virginia legislative crawler module`)

- [ ] **Task 2: Colab GPU Vectorization Notebook & Script**
  - Files: `notebooks/virginia_recent_bills_colab.ipynb`, `notebooks/colab_runner.py`
  - RED: Add test case checking GPU-enabled FastEmbed batch processing and JSON payload vector validity (384 dimensions per chunk).
  - GREEN: Create `virginia_recent_bills_colab.ipynb` with step-by-step cells (Install -> Scrape 3-Month Bills -> GPU Batch Embed with `BAAI/bge-small-en-v1.5` -> Export/Upload to Qdrant).
  - Real-surface QA: Run dry-run embedding test with synthetic legislation text verifying 384-dim vector outputs.
  - Evidence: Output `.json.gz` contains valid vector embeddings and complete metadata.
  - Cleanup: Clean temporary notebooks cache.
  - Commit: YES (`feat(colab): add GPU accelerated 3-month Virginia legislative embedding notebook`)

- [ ] **Task 3: Direct Qdrant Ingestion & Local Sync Handler**
  - Files: `backend/vector_store.py`, `backend/stream_ingest.py`
  - RED: Test importing generated JSON/GZ payload directly into `VectorStoreManager` with point count verification.
  - GREEN: Add batch vector import method `import_external_vectors_payload(json_path)` into `backend/vector_store.py`.
  - Real-surface QA: Ingest sample vector bundle into local `qdrant_db` and execute semantic search query "Virginia budget and taxes past 3 months".
  - Evidence: Successful vector search results returned with high cosine similarity.
  - Cleanup: Reset test points from vector collection.
  - Commit: YES (`feat(db): add vector payload batch importer for Qdrant`)

## Parallel Execution Waves
- **Wave 1**: Task 1 (Scraper logic) & Task 3 (Qdrant importer handler)
- **Wave 2**: Task 2 (Colab GPU notebook integration tying scraper and vector generation together)

## Dependency Matrix
| Task | Depends on | Blocks | Can parallelize with |
|---|---|---|---|
| 1 | none | 2 | 3 |
| 3 | none | 2 | 1 |
| 2 | 1, 3 | none | none |

## Final Verification Wave
- [ ] Run full pytest suite across `backend/tests/`.
- [ ] Validate Colab notebook run instructions in `notebooks/virginia_recent_bills_colab.ipynb`.
- [ ] Perform semantic search test against indexed 3-month Virginia legislative points in Qdrant.
- [ ] Review git status and package surface.

Next: `start-work va-bills-colab-qdrant-3m`
