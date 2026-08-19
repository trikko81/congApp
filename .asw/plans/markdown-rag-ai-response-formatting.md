# Markdown RAG AI Response Formatting and Boilerplate Removal

## TL;DR
Implement rich GitHub-flavored Markdown rendering in the frontend chat interface for DeepSeek and LLM RAG responses while stripping all hardcoded pre-added introductory/trailer boilerplate text from both the backend synthesis layer (`backend/llm_synthesis.py`) and the frontend message handler (`frontend/src/app/page.tsx`).

## Objective
Render structured, clean Markdown typography (headings, bold text, lists, code spans, blockquotes, and citation badges) for AI synthesized responses without any artificial boilerplate prefixes (e.g., *"Based on the analysis of retrieved..."*) or static suffixes (*"Click any citation badge below..."*).

## Non-goals
- Modifying the underlying Qdrant vector retrieval or cosine distance math.
- Altering the PDF.js canvas split-screen layout or zoom coordinate system.
- Replacing the DeepSeek API provider integration.

## Discovery
- `frontend/src/app/page.tsx`: Currently renders `turn.assistantMessage.text` using a plain `<p style={{ whiteSpace: "pre-wrap" }}>` element, displaying raw markdown characters (`###`, `**`, `-`) as unformatted plaintext. In addition, lines 128-137 inject hardcoded intro and trailer strings.
- `backend/llm_synthesis.py`: Prompt and fallback methods (`_fallback_synthesis`) inject hardcoded preface sentences ("Based on the analysis...", "Click any citation badge below...").
- `frontend/src/app/globals.css`: Contains chat message card styles (`.message-assistant`), but lacks dedicated markdown typography rules (`.markdown-content h1-h4`, `ul`, `ol`, `li`, `code`, `blockquote`, `table`).

## Decisions
- **Markdown Component**: Implement a zero-dependency, safe React Markdown parser or component in `frontend/src/components/MarkdownRenderer.tsx` that transforms headings (`#`, `##`, `###`), bold (`**text**`), italics (`*text*`), unordered/ordered lists (`-`, `1.`), inline code, and blockquotes into native JSX elements.
- **Boilerplate Elimination**:
  - Update `backend/llm_synthesis.py` system prompt to mandate direct, structured markdown responses with zero preamble or filler disclaimers.
  - Clean `_fallback_synthesis` in `backend/llm_synthesis.py` to output atomic structured markdown bullets without pre-added headers/footers.
  - Remove hardcoded template boilerplate in `frontend/src/app/page.tsx` so only the raw LLM response is displayed.
- **Typography & Theming**: Add markdown typography rules in `frontend/src/app/globals.css` respecting the active dynamic theme (`slate`, `contrast`, `coastal`, `charcoal`, `warm`).

---

## TODOs

- [ ] **Task 1: Strip Pre-Added Boilerplate from Backend LLM Synthesis**
  - Files: `backend/llm_synthesis.py`
  - References: `backend/llm_synthesis.py:116-123`, `backend/llm_synthesis.py:263-283`
  - What to do:
    - Update DeepSeek / LLM system prompt to instruct: "Respond directly in clean GitHub-flavored Markdown. Do not include introductory pleasantries, meta-commentary, or repetitive preambles."
    - Update `_fallback_synthesis` to return clean markdown bullet points without `"Based on the analysis..."` or `"Click any citation badge below..."`.
  - What not to do: Do not remove citation extraction or token cleanup logic.
  - RED: Run `pytest backend/tests/test_llm.py` with assertion checking absence of boilerplate wrappers.
  - GREEN: Update test assertions and verify all tests in `backend/tests/test_llm.py` pass.
  - Real-surface QA: Execute `python -m backend.llm_synthesis` test harness to verify raw clean markdown output.
  - Evidence: `backend/tests/test_llm.py` output.
  - Cleanup: Remove any temporary test script artifacts.
  - Commit: YES (Subject: `fix(backend): remove pre-added boilerplate from LLM synthesis`)

- [ ] **Task 2: Build MarkdownRenderer Component and Typography Styles**
  - Files:
    - `frontend/src/components/MarkdownRenderer.tsx`
    - `frontend/src/app/globals.css`
  - References: `frontend/src/app/globals.css:395-452`
  - What to do:
    - Create `frontend/src/components/MarkdownRenderer.tsx` supporting headings (`#`, `##`, `###`), bold, italic, lists (`-`, `*`, `1.`), blockquotes (`>`), code blocks, and inline code.
    - Add `.markdown-content` styling in `frontend/src/app/globals.css` with consistent margins, theme color inheritance, and legible line heights.
  - What not to do: Do not add external heavy unvetted NPM packages with React 19 peer dependency conflicts.
  - RED: Test rendering a complex markdown string containing headers, bold items, lists, and citations.
  - GREEN: Verify all elements render into formatted DOM nodes.
  - Real-surface QA: Render markdown sample in `MarkdownRenderer` and inspect computed styles in browser.
  - Evidence: Screenshot/DOM inspection of rendered headers and formatted lists.
  - Cleanup: Clear temporary test strings.
  - Commit: YES (Subject: `feat(frontend): add MarkdownRenderer component and typography styles`)

- [ ] **Task 3: Integrate MarkdownRenderer and Remove Frontend Boilerplate in Chat Feed**
  - Files: `frontend/src/app/page.tsx`
  - References: `frontend/src/app/page.tsx:125-138`, `frontend/src/app/page.tsx:252-273`
  - What to do:
    - Replace `<p style={{ whiteSpace: "pre-wrap" }}>{turn.assistantMessage.text}</p>` with `<MarkdownRenderer content={turn.assistantMessage.text} />`.
    - Remove hardcoded intro text (`"Based on the analysis of retrieved..."`) and trailer text (`"Click any citation badge below..."`) in `handleSend`.
  - What not to do: Do not remove citation badges or citation click-to-scroll handlers.
  - RED: Send query in frontend UI; observe whether raw hashes or clean headers render.
  - GREEN: DeepSeek / AI answer renders as styled headings, bullet points, and bold text with zero pre-added text.
  - Real-surface QA: Perform a search query (e.g. *"What is the Virginia Beach moratorium on data centers?"*) and verify clean markdown formatting.
  - Evidence: Clean chat feed DOM with rendered markdown.
  - Cleanup: Clear browser console debug logs.
  - Commit: YES (Subject: `feat(frontend): render assistant responses with MarkdownRenderer`)

---

## Parallel Execution Waves

```text
Wave 1:
- Task 1: Strip Pre-Added Boilerplate from Backend LLM Synthesis (Backend)
- Task 2: Build MarkdownRenderer Component and Typography Styles (Frontend)

Wave 2:
- Task 3: Integrate MarkdownRenderer and Remove Frontend Boilerplate in Chat Feed (Frontend)

Critical path:
Task 2 -> Task 3
```

## Dependency Matrix

| Task | Depends on | Blocks | Can parallelize with |
|---|---|---|---|
| Task 1 (Backend prompt & fallback cleanup) | none | none | Task 2 |
| Task 2 (MarkdownRenderer & CSS) | none | Task 3 | Task 1 |
| Task 3 (Frontend page.tsx integration) | Task 2 | Final Verification | none |

---

## Final Verification Wave

- [ ] **Automated Test Pass**: Run all backend pytest suites:
  ```powershell
  python -m pytest backend/tests/test_llm.py backend/tests/test_api.py -v
  ```
- [ ] **Frontend Build Verification**:
  ```powershell
  npm --prefix frontend run build
  ```
- [ ] **Manual QA Replay**:
  1. Trigger query *"What is the Virginia Beach moratorium on data centers?"*.
  2. Verify that the response begins directly with the answer (no *"Based on..."* prefix).
  3. Verify that headings, bold terms, bullet points, and citations are rendered as rich HTML.
  4. Click citation badges to confirm PDF viewer highlighting and auto-scroll remain functional.

---

Next: `start-work markdown-rag-ai-response-formatting`
