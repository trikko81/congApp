# Virginia 10-Year Full Legislative Laws & Bills Colab Extraction Engine (2016–2026)

## TL;DR
Build an automated, zero-local-strain extraction engine that runs in Google Colab's free cloud environment to harvest, parse, and vectorize all enacted Virginia laws and chaptered bills from 2016 to 2026 across all regular and special sessions, producing pre-computed Qdrant vector packages that stream directly into CongApp's vector database (`qdrant_db`).

## Objective
Extract and index 100% of enacted Virginia legislation (all House and Senate chaptered bills / Acts of Assembly across 2016–2026) using Google Colab's free T4 GPU runtime, offloading all network bandwidth, PDF parsing, and vector computations from the user's local machine.

## Non-goals
- Performing heavy multi-gigabyte PDF processing or GPU embedding on the local user machine.
- Storing thousands of raw PDF files permanently on local disk (only indexed vectors + text payloads reside in Qdrant DB).
- Scraping unpassed/failed bills (focus strictly on enacted laws, chaptered acts, and adopted legislation).

## Discovery
- `lis.virginia.gov`: Virginia Legislative Information System provides structured session directories for all regular and special sessions from 2016 to 2026 (e.g., `https://lis.virginia.gov/cgi-bin/legp604.exe?{session_code}+lst+APP` for Approved/Chaptered bills).
- `backend/vector_store.py`: Supports `index_batch_raw()` to insert pre-computed 384-dimensional FastEmbed vectors directly into `qdrant_db` in milliseconds per batch without CPU overhead.
- `backend/main.py`: Exposes `POST /api/ingest/batch` for streaming vector payloads.
- `notebooks/colab_ingest_pipeline.ipynb`: Initial prototype notebook available for full-scale extension.

## Decisions
- **Cloud Execution Environment**: A dedicated Google Colab notebook (`notebooks/virginia_all_laws_colab.ipynb`) and companion Python script (`notebooks/virginia_crawler.py`) will run entirely in Colab memory / ephemeral storage.
- **Session Coverage (2016–2026)**:
  - 2016 (161 Regular, 162 Special)
  - 2017 (171 Regular)
  - 2018 (181 Regular, 182 Special)
  - 2019 (191 Regular, 192 Special)
  - 2020 (201 Regular, 202 Special)
  - 2021 (211 Regular, 212 Special)
  - 2022 (221 Regular, 222 Special)
  - 2023 (231 Regular)
  - 2024 (241 Regular, 242 Special)
  - 2025 (251 Regular)
  - 2026 (261 Regular)
- **Checkpointed Output & Delivery**: Colab script checkpoints every session into compressed JSON bundles (`va_laws_{year}.json.gz`), which can be synced directly via API or downloaded into `qdrant_db`.
- **Database Schema**: Full payload preservation with `state="Virginia"`, `enactment_year`, `session_id`, `bill_id`, `chapter_id`, `doc_title`, `text_chunk`, and `url`.

## TODOs

- [x] Task 1: Virginia LIS Session & Chaptered Bill Crawler (`notebooks/virginia_crawler.py`)
  - Files:
    - [NEW] [notebooks/virginia_crawler.py](file:///d:/Documents/Juan_Elias/congApp/notebooks/virginia_crawler.py)
    - [NEW] [backend/tests/test_virginia_crawler.py](file:///d:/Documents/Juan_Elias/congApp/backend/tests/test_virginia_crawler.py)
  - RED: Test fails when querying LIS session indexes (missing crawler module).
  - GREEN: Implement `VirginiaLISCrawler` with session codes (2016-2026), parsing chaptered bills, titles, full legal text, and official LIS URLs with rate limiting and retry logic.
  - Real-surface QA: Run `python notebooks/virginia_crawler.py --year 2024 --sample 3` and verify extracted chaptered bills with full text.
  - Evidence: Verified JSON output containing valid Virginia chaptered legislation for session 2024.
  - Cleanup: Remove temporary sample JSON.
  - Commit: YES `feat(crawler): add Virginia LIS 10-year session and chaptered bill crawler`

- [x] Task 2: Google Colab Full-Scale Extraction & GPU Vectorization Notebook
  - Files:
    - [NEW] [notebooks/virginia_all_laws_colab.ipynb](file:///d:/Documents/Juan_Elias/congApp/notebooks/virginia_all_laws_colab.ipynb)
    - [MODIFY] [notebooks/colab_runner.py](file:///d:/Documents/Juan_Elias/congApp/notebooks/colab_runner.py)
  - RED: Colab notebook lacks automated session loop or batch checkpointing.
  - GREEN: Create ready-to-run Google Colab notebook with one-click GPU execution: loops all sessions (2016–2026), tokenizes, embeds via FastEmbed CUDA/CPU in Colab memory, and streams batches to user API or Google Drive.
  - Real-surface QA: Execute notebook cell test run for a sample year (2024) in dry-run mode and verify vector generation throughput.
  - Evidence: Validated output payload with 384-dimensional embeddings and zero local CPU strain.
  - Cleanup: Remove test artifact.
  - Commit: YES `feat(colab): create Google Colab 10-year Virginia law batch vectorization notebook`

- [x] Task 3: Local Fast-Stream Ingestion Utility (`backend/stream_ingest.py`)
  - Files:
    - [NEW] [backend/stream_ingest.py](file:///d:/Documents/Juan_Elias/congApp/backend/stream_ingest.py)
    - [NEW] [backend/tests/test_stream_ingest.py](file:///d:/Documents/Juan_Elias/congApp/backend/tests/test_stream_ingest.py)
  - RED: Test fails when ingesting pre-computed Colab payload bundles.
  - GREEN: Implement streaming receiver that reads Colab bundle files or API streams and directly writes into `qdrant_db` in 1,000-chunk batches without re-embedding.
  - Real-surface QA: Run `python -m backend.stream_ingest --bundle test_bundle.json` and verify Qdrant point count increases without local GPU usage.
  - Evidence: Qdrant database collection statistics showing indexed points.
  - Cleanup: Remove test points.
  - Commit: YES `feat(backend): add streaming batch vector ingestion utility`

- [x] Task 4: UI & Search Integration for Full Virginia Legislative Archive
  - Files:
    - [MODIFY] [frontend/src/components/LegislativeSearchModal.tsx](file:///d:/Documents/Juan_Elias/congApp/frontend/src/components/LegislativeSearchModal.tsx)
    - [MODIFY] [frontend/src/app/page.tsx](file:///d:/Documents/Juan_Elias/congApp/frontend/src/app/page.tsx)
  - RED: Modal only shows mock items or lacks year-by-year 2016-2026 session selection.
  - GREEN: Update Legislative Search modal to allow querying across all 10 years of Virginia sessions and display Colab ingestion status badges.
  - Real-surface QA: Open browser UI, filter by Virginia 2016–2026, verify search citations link to enacted Virginia chapters.
  - Evidence: Visual inspection of UI search citations.
  - Cleanup: Reset UI state.
  - Commit: YES `feat(frontend): support full 10-year Virginia legislative search archive`

## Parallel Execution Waves

```text
Wave 1:
- Task 1: Virginia LIS Session & Chaptered Bill Crawler
- Task 3: Local Fast-Stream Ingestion Utility

Wave 2:
- Task 2: Google Colab Full-Scale Extraction & GPU Vectorization Notebook (depends on Task 1)
- Task 4: UI & Search Integration for Full Virginia Legislative Archive (depends on Task 3)

Critical path:
Task 1 -> Task 2 -> Final Verification
```

## Dependency Matrix

| Task | Depends on | Blocks | Can parallelize with |
|---|---|---|---|
| 1 | none | 2 | Task 3 |
| 2 | 1 | none | Task 4 |
| 3 | none | 4 | Task 1 |
| 4 | 3 | none | Task 2 |

## Final Verification Wave

- [x] Automated Test Suite: Run `pytest backend/tests/` to verify crawler, streaming ingestion, and search APIs.
- [x] Colab Execution Proof: Verify `virginia_crawler.py` and `colab_runner.py` run seamlessly in Colab environment.
- [x] Qdrant Storage Verification: Verify database points contain full Virginia legislative metadata and zero raw PDFs left on local disk.
- [x] UI Citation Smoke: Verify search queries retrieve Virginia law chunks with full chapter and year citations.

Next: `start-work virginia-full-10yr-laws-colab-extractor`
