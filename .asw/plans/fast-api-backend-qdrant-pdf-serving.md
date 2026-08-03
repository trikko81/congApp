# fast-api-backend-qdrant-pdf-serving

## TL;DR
Scaffold a FastAPI backend for `congApp` with CORS configured for `http://localhost:3000`, implement a `POST /api/search` vector retrieval endpoint querying Qdrant local database (returning page, paragraph, snippet, and bbox coordinates), and a `GET /api/documents/{name}` endpoint serving raw PDF files from the `TEMPPDF` directory.

## Objective
Provide an operational, testable REST API service in `backend/main.py` (and associated modules) that powers real-time semantic search with bounding box references and direct PDF retrieval for split-screen highlight synchronization.

## Non-goals
- Modifying vector embedding chunk logic or Qdrant collection creation logic in `backend/vector_store.py` beyond supporting clean query execution.
- Implementing frontend UI components in Next.js (handled in subsequent steps).

## Discovery
- `backend/vector_store.py`: `VectorStoreManager.search()` uses `self.client.query_points()` returning `scored_point.payload` (which contains `doc_title`, `page`, `paragraph`, `text_chunk`, and `metadata` dictionary with `bbox` `[x0, y0, x1, y1]`).
- `backend/parser.py`: Defines payload schema `DocumentChunk` with `doc_title`, `page`, `paragraph`, `text_chunk`, and `metadata: { source_path, bbox }`.
- `TEMPPDF/`: Directory containing PDF files available for retrieval (e.g. `S5087_Clean_Air_Act_Renewable_Biomass_Amendment.pdf`).
- Environment: FastAPI and Uvicorn are installed in `.venv`.

## Decisions
- Backend File Structure: Place application code in `backend/main.py` and write tests under `backend/tests/test_api.py`.
- Document Directory: Use `TEMPPDF/` at the repository root as the storage folder for PDF file serving, validating filenames to prevent path traversal attacks.
- Search API Response Model: Explicit Pydantic models for `SearchRequest` (`query`, `limit`, `doc_title` filter) and `SearchResultItem` containing `id`, `score`, `doc_title`, `page`, `paragraph`, `snippet`, `bbox` (`List[float]`), and `metadata`.
- Qdrant Connection: Reuse `VectorStoreManager` instance initialized at FastAPI app startup (lifespan or app state).

## TODOs
- [x] Task 1: Scaffold FastAPI Backend with CORS (`http://localhost:3000`) and Health Endpoint
  - Files: `backend/main.py`, `backend/tests/test_api.py`
  - RED: Run `pytest backend/tests/test_api.py -k test_health` (fails: module not found / endpoint 404).
  - GREEN: Create FastAPI instance in `backend/main.py`, add `CORSMiddleware` allowing `http://localhost:3000` (origins, methods, headers), and implement `GET /api/health`.
  - Real-surface QA: Execute `curl -s http://127.0.0.1:8000/api/health` and verify `{"status": "ok"}`.
  - Evidence: `backend/tests/test_api.py` test logs and curl JSON output.
  - Cleanup: Stop background uvicorn server if started during manual test.
  - Commit: NO (Report draft message: `feat(backend): scaffold FastAPI app with CORS and health check`)

- [x] Task 2: Implement `POST /api/search` Qdrant Vector Search Endpoint
  - Files: `backend/main.py`, `backend/schemas.py`, `backend/tests/test_api.py`
  - RED: Run `pytest backend/tests/test_api.py -k test_search_endpoint` (fails: missing search endpoint).
  - GREEN: Define request/response Pydantic models in `backend/schemas.py`. Implement `POST /api/search` in `backend/main.py` connecting to `VectorStoreManager.search()`, extracting top-k matches with `page`, `paragraph`, `text_chunk` (snippet), and `bbox` (from metadata).
  - Real-surface QA: Execute HTTP POST to `http://127.0.0.1:8000/api/search` with JSON payload `{"query": "biomass", "limit": 3}` and verify response items contain `page`, `paragraph`, `snippet`, and `bbox`.
  - Evidence: Pytest test report and sample JSON payload output.
  - Cleanup: Reset/close temporary vector store sessions after test run.
  - Commit: NO (Report draft message: `feat(backend): add POST /api/search Qdrant retrieval endpoint`)

- [x] Task 3: Implement `GET /api/documents/{name}` Raw PDF Serving Endpoint
  - Files: `backend/main.py`, `backend/tests/test_api.py`
  - RED: Run `pytest backend/tests/test_api.py -k test_get_document` (fails: endpoint non-existent / 404).
  - GREEN: Implement `GET /api/documents/{name}` using `FileResponse` to stream requested PDF from `TEMPPDF/`. Include path traversal checks (`Path(name).name`) and 404 error handling.
  - Real-surface QA: Request `curl -I http://127.0.0.1:8000/api/documents/S5087_Clean_Air_Act_Renewable_Biomass_Amendment.pdf` and check `200 OK` header with `content-type: application/pdf`.
  - Evidence: HTTP response header output and pytest assertion output.
  - Cleanup: None needed.
  - Commit: NO (Report draft message: `feat(backend): add GET /api/documents/{name} PDF serving endpoint`)

## Parallel Execution Waves
- Wave 1: Task 1 (FastAPI base app & CORS)
- Wave 2: Task 2 (Search endpoint) & Task 3 (PDF document endpoint) - run sequentially or independently once Task 1 is merged.

## Dependency Matrix
| Task | Depends on | Blocks | Can parallelize with |
|---|---|---|---|
| 1 | None | 2, 3 | None |
| 2 | Task 1 | Final Verification | Task 3 |
| 3 | Task 1 | Final Verification | Task 2 |

## Final Verification Wave
- [x] Run full backend test suite: `pytest backend/tests/`
- [x] Launch Uvicorn dev server (`uvicorn backend.main:app --port 8000`) and test both endpoints (`POST /api/search` and `GET /api/documents/{name}`) using Python `requests` or `curl`.
- [x] Code formatting and cleanliness check.

Next: `start-work fast-api-backend-qdrant-pdf-serving`
