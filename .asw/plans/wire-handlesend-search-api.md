# Wire handleSend to FastAPI /api/search (Final Integration)

## TL;DR
Connect the frontend React application (`frontend/src/app/page.tsx`) to the running FastAPI backend (`http://localhost:8000/api/search`). Upon user input, `handleSend()` will send an HTTP POST request, format the returned vector search hits into structured response text and citation objects (with page numbers, paragraph indices, and bounding boxes), and update state so clicking citation badges auto-scrolls and highlights the PDF viewer.

## Objective
Enable real end-to-end RAG functionality: replacing static mock responses in `handleSend()` with live Qdrant similarity search hits returned by FastAPI, complete with interactive citation highlights linked to PDF coordinates.

## Non-goals
- Modifying backend endpoint signatures or database schemas.
- Changing PDF rendering/highlighting math in `PdfViewer.tsx`.
- Adding auth or complex chat session persistence beyond local component state.

## Discovery
- `frontend/src/app/page.tsx`: Currently uses `setTimeout` with static mock text and mock citations. Contains state for `turns`, `isTyping`, `inputQuery`, and `selectedCitation`.
- `backend/main.py`: Exposes `@app.post("/api/search")` returning `SearchResponse` which has a list of `SearchResultItem` containing `doc_title`, `page`, `paragraph`, `text_chunk`, `snippet`, `bbox`, `score`.
- `backend/schemas.py`: `SearchRequest` schema expects `{ "query": str, "limit": int, "doc_title": Optional[str] }`.
- `frontend/src/components/PdfViewer.tsx`: Consumes `Citation` objects containing `docTitle`, `page`, `paragraph`, `snippet`, and optional `bbox`.

## Decisions
- Use `fetch('http://localhost:8000/api/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: inputQuery, limit: 3 }) })` in `handleSend()`.
- Handle errors gracefully in `handleSend()` with user feedback if the backend server is unreachable.
- Automatically select the top returned citation on query response so the PDF viewer updates immediately to the best match.

## TODOs

- [x] **Task 1: Update handleSend() in page.tsx to consume FastAPI /api/search**
  - **Files**: `frontend/src/app/page.tsx`
  - **RED**: Executing a query currently returns static hardcoded text regardless of search input.
  - **GREEN**: Executing a query fetches `http://localhost:8000/api/search`, extracts `results`, dynamically constructs response text summarizing hits, maps items to `Citation` types, and sets `selectedCitation` to top result.
  - **Real-surface QA**: Open Next.js UI, submit a query, inspect network POST request to `/api/search`, verify real snippets render in chat, click citation badge, verify PDF panel sync.
  - **Evidence**: Network payload log & rendered citation badge showing real PDF page/paragraph.
  - **Cleanup**: Remove hardcoded setTimeout block and mock initial turn citations if desired.
  - **Commit**: YES - `feat(frontend): connect handleSend to FastAPI search API`

## Parallel Execution Waves
- Wave 1: Task 1 (Single target file).

## Dependency Matrix
| Task | Depends on | Blocks | Can parallelize with |
|---|---|---|---|
| 1 | None | None | N/A |

## Final Verification Wave
- [x] Type check frontend (`npx tsc --noEmit`).
- [x] Run backend syntax check (`python -m py_compile ...`).
- [x] Verify HTTP response schema alignment between FastAPI and React state interfaces.
- [x] Manual QA verification of citation click-to-highlight behavior.

Next: `start-work wire-handlesend-search-api`
