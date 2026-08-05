# LLM Synthesis Layer & Query Metadata Filter Integration

## TL;DR
Implement an LLM Synthesis Layer supporting DeepSeek API, local Ollama, OpenAI, and Anthropic Claude APIs with a clean local fallback mechanism. Update `POST /api/search` in `backend/main.py` and `backend/schemas.py` to synthesize grounded conversational answers from Qdrant vector search chunks with citations and query intent filtering (such as state/location or temporal constraints).

## Objective
Enable `POST /api/search` to take a natural language query, filter retrieved chunks (e.g., by location/state like "Virginia" or date ranges like "past week" when specified), and produce a synthesized natural language answer with grounded citations using DeepSeek API (or Ollama/OpenAI/Claude/Fallback), while maintaining backwards compatibility when synthesis is disabled or external APIs are unconfigured.

## Non-goals
- Replacing Qdrant vector search or FastEmbed embeddings.
- Mandating paid API keys (must gracefully fall back to local template-based synthesis or local Ollama when keys are missing).
- Rewriting frontend UI components in this backend layer phase.

## Discovery
- `file:///d:/Documents/Juan_Elias/congApp/backend/main.py`: Endpoint `POST /api/search` currently queries Qdrant via `VectorStoreManager` and returns un-synthesized raw text chunks.
- `file:///d:/Documents/Juan_Elias/congApp/backend/schemas.py`: Defines `SearchRequest` and `SearchResponse`. Lacks synthesis output fields and advanced filter request parameters.
- `file:///d:/Documents/Juan_Elias/congApp/backend/vector_store.py`: Supports `filter_dict` filtering for Qdrant points.
- `file:///d:/Documents/Juan_Elias/congApp/backend/tests/test_api.py`: Contains API integration test suite using FastAPI `TestClient`.
- `file:///d:/Documents/Juan_Elias/congApp/.env`: Holds environment settings including `OPENAI_API_KEY`, `LLM_MODEL`, `QDRANT_COLLECTION`. We will add DeepSeek API settings (`DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL=deepseek-chat`, `DEEPSEEK_BASE_URL=https://api.deepseek.com`).

## Decisions
- **Provider Architecture**: Create `backend/llm_synthesis.py` encapsulating provider dispatch (DeepSeek, Ollama, OpenAI, Claude, and local Fallback). DeepSeek uses OpenAI-compatible client interface with base URL `https://api.deepseek.com`.
- **Graceful Fallback**: If no API key or Ollama connection is available, default to a robust structured fallback synthesizer so tests and offline setups remain fully functional.
- **Query Filter Parsing**: Extract state/location tokens (e.g., "Virginia", "VA") and date queries ("past week", "last 7 days") from query strings to enhance Qdrant metadata filters or payload matching.
- **Schema Extensions**: Extend `SearchRequest` (`enable_synthesis`, `state_filter`, `date_range`) and `SearchResponse` (`synthesized_answer`, `llm_provider`, `citations`).

## TODOs

- [x] Task 1: Update API schemas for synthesis and filter parameters
  - Files: [`backend/schemas.py`](file:///d:/Documents/Juan_Elias/congApp/backend/schemas.py)
  - RED: Run `pytest backend/tests/test_api.py` and confirm `SearchResponse` does not yet accept `synthesized_answer` or `citations`.
  - GREEN: Update `SearchRequest` with `enable_synthesis: bool = True`, `state_filter: Optional[str] = None`, `date_range: Optional[str] = None`. Update `SearchResponse` with `synthesized_answer: Optional[str] = None`, `llm_provider: Optional[str] = None`, `citations: Optional[List[Dict[str, Any]]] = None`.
  - Real-surface QA: `python -c "from backend.schemas import SearchRequest, SearchResponse; r = SearchResponse(results=[], synthesized_answer='test'); print(r.model_dump())"`
  - Evidence: `backend/schemas.py` exports new optional schema fields cleanly.
  - Cleanup: None required.
  - Commit: YES (Subject: `feat(schemas): add llm synthesis and metadata filter fields to search schemas`)

- [x] Task 2: Build LLM Synthesis Service with DeepSeek, Ollama, OpenAI, Claude, and Fallback support
  - Files: [`backend/llm_synthesis.py`](file:///d:/Documents/Juan_Elias/congApp/backend/llm_synthesis.py) [NEW], [`backend/tests/test_llm.py`](file:///d:/Documents/Juan_Elias/congApp/backend/tests/test_llm.py) [NEW]
  - RED: Create `backend/tests/test_llm.py` expecting `LLMSynthesisService.synthesize()` to format context, generate grounded citations, handle DeepSeek API provider routing, and extract state/date filter hints. Run `pytest backend/tests/test_llm.py` (fails with ModuleNotFoundError).
  - GREEN: Implement `LLMSynthesisService` with provider routing (DeepSeek, Ollama, OpenAI, Claude, Fallback), citation construction (`[DocTitle, Page X, Par Y]`), and query filter detection (`extract_query_filters`).
  - Real-surface QA: `python -m pytest backend/tests/test_llm.py`
  - Evidence: All unit tests in `test_llm.py` pass cleanly.
  - Cleanup: Remove temporary test caches if created.
  - Commit: YES (Subject: `feat(backend): add LLMSynthesisService supporting DeepSeek Ollama OpenAI Claude and fallback synthesis`)

- [x] Task 3: Integrate synthesis layer and filter routing into POST /api/search
  - Files: [`backend/main.py`](file:///d:/Documents/Juan_Elias/congApp/backend/main.py), [`backend/tests/test_api.py`](file:///d:/Documents/Juan_Elias/congApp/backend/tests/test_api.py)
  - RED: Add test case in `backend/tests/test_api.py` asserting `POST /api/search` returns `synthesized_answer` and `citations` when `enable_synthesis=True`.
  - GREEN: Update `backend/main.py` to instantiate `LLMSynthesisService`, apply query intent filters to `VectorStoreManager.search()`, call synthesis service when requested, and populate response payload.
  - Real-surface QA: `pytest backend/tests/test_api.py` and curl/HTTP request to `http://127.0.0.1:8000/api/search`.
  - Evidence: API test suite succeeds with 100% green status.
  - Cleanup: None.
  - Commit: YES (Subject: `feat(api): integrate llm synthesis layer into search endpoint`)

## Parallel Execution Waves

Wave 1:
- Task 1: Update API schemas for synthesis and filter parameters
- Task 2: Build LLM Synthesis Service with DeepSeek, Ollama, OpenAI, Claude, and Fallback support

Wave 2:
- Task 3: Integrate synthesis layer and filter routing into POST /api/search (depends on Task 1, Task 2)

Critical path:
Task 1 + Task 2 -> Task 3

## Dependency Matrix

| Task | Depends on | Blocks | Can parallelize with |
|---|---|---|---|
| 1 | None | 3 | 2 |
| 2 | None | 3 | 1 |
| 3 | 1, 2 | None | None |

## Final Verification Wave

- [x] Execute full pytest suite: `pytest backend/tests/`
- [x] Inspect API schema validation via FastAPI TestClient endpoint calls.
- [x] Verify clean code formatting and strict type annotations per Python 3.10+ rules.
- [x] Verify zero regression on existing endpoints (`/api/health`, `/api/documents/{name}`).


Next: `start-work llm-synthesis-layer`
