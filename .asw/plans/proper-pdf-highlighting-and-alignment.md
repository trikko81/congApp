# proper-pdf-highlighting-and-alignment

## TL;DR
Fix PDF document alignment and citation highlighting in `frontend/src/components/PdfViewer.tsx` and `frontend/src/app/globals.css`. Correct container scale calculations so the PDF page canvas fits perfectly within the card margins, implement text snippet bounding box (bbox) matching, and refactor the highlight overlay to render as a non-obscuring translucent highlighter with external floating badge tags so document text remains 100% aligned, legible, and viewable.

## Objective
1. Correct PDF canvas scaling and text layer alignment so PDF pages render crisply without horizontal overflow or boundary misalignment.
2. Replace opaque purple text overlay boxes with translucent text highlights and external floating badges so highlight overlays never obscure or block PDF document text.
3. Add text snippet bounding-box matching using PDF.js `getTextContent()` when exact backend bbox coordinates are absent, ensuring highlights align precisely with target document lines.

## Non-goals
- Modifying backend Qdrant vector database storage or indexing schemas.
- Changing top navigation bar styling or theme selectors.

## Discovery
- `frontend/src/components/PdfViewer.tsx`: Uses `containerEl.clientWidth` on `.pdf-page-card` (which includes 32px padding), causing canvas scaling misalignment and width overflow inside `.pdf-canvas-wrapper`.
- `frontend/src/components/PdfViewer.tsx`: Highlights current citation by placing `.pdf-highlight-overlay` with heavy background and text snippets directly over document text (e.g. line 16), blocking underlying PDF text readability.
- `frontend/src/app/globals.css`: Contains CSS definitions for `.pdf-page-card`, `.pdf-canvas-wrapper`, and `.pdf-highlight-overlay`. `.pdf-highlight-overlay` currently has internal text elements (`.pdf-highlight-tag`, `.pdf-highlight-snippet-preview`) that sit on top of target PDF lines.
- `backend/parser.py`: Generates block `bbox` `(x0, y0, x1, y1)` in 72 DPI PDF point space. Scaling logic in `PdfViewer.tsx` must convert PDF point coordinates accurately to current canvas viewport space.

## Decisions
- **Container Scale Matching**: Measure `.pdf-canvas-wrapper` client width (or subtract card padding) when calculating `pdfjs` viewport scale so canvas width matches inner container bounds exactly.
- **Translucent Highlighter Overlay**: Change `.pdf-highlight-overlay` styling to a clean translucent text highlight (`rgba(254, 240, 138, 0.45)` amber/yellow or theme primary glow with subtle 1.5px border).
- **External Floating Tag**: Move citation tag badge to float above the highlight box (`top: -24px` / `-26px`), and remove internal text snippet preview from inside the highlight rectangle so PDF document text remains completely unobstructed.
- **Dynamic Text Snippet BBox Resolution**: Extract page text content via `page.getTextContent()` to match snippet text when explicit `bbox` is missing, avoiding hardcoded vertical offset approximations (`120 + (paragraph-1)*110`).
- **Centered Auto-Scroll**: Configure target page scrolling to `block: "center"` so highlighted citations scroll into clear view in the middle of the right panel.

## TODOs

- [x] **Task 1: Fix PDF Canvas Alignment & Container Scale Calculation**
  - Files: `frontend/src/components/PdfViewer.tsx`, `frontend/src/app/globals.css`
  - RED: Observe canvas scale calculated from outer `.pdf-page-card` clientWidth (including padding), resulting in canvas overflow and misaligned borders.
  - GREEN:
    - Update `renderPage` in `PdfViewer.tsx` to target `.pdf-canvas-wrapper` width for scale calculation.
    - Set canvas display width/height matching viewport dimensions with `devicePixelRatio` crisp scaling.
    - Adjust CSS in `globals.css` so `.pdf-canvas-wrapper` centers canvas cleanly with zero horizontal overflow.
  - Real-surface QA: Load page in browser at `http://localhost:3000`, inspect `.pdf-canvas-wrapper` and canvas bounds; verify canvas aligns cleanly inside card borders.
  - Evidence: DOM inspection confirming canvas width matches inner wrapper width with aligned page margins.
  - Cleanup: Remove temporary debug logs.
  - Commit: NO (Report draft message: `fix(frontend): align pdf canvas scale with inner container width`)

- [x] **Task 2: Implement Dynamic Text Snippet BBox Matching**
  - Files: `frontend/src/components/PdfViewer.tsx`
  - RED: Missing or fallback citations rely on crude fixed vertical offset formula (`120 + (paragraph-1)*110`) which places highlight boxes on arbitrary lines.
  - GREEN:
    - Add text content resolution (`page.getTextContent()`) inside `PdfViewer.tsx`.
    - Match `activeCitation.snippet` words against text items to derive target text line bounding box `[x0, y0, x1, y1]`.
    - Scale bbox from PDF points space (`72 DPI`) to canvas viewport space (`left`, `top`, `width`, `height`).
  - Real-surface QA: Click citation badge without explicit bbox; verify highlight overlay box resolves directly to the matching text line on the PDF page.
  - Evidence: Console log / DOM check showing calculated highlight top/left coordinates matching exact line bounds.
  - Cleanup: Clear temporary log dumps.
  - Commit: NO (Report draft message: `feat(frontend): add dynamic text snippet bbox matching for pdf viewer`)

- [x] **Task 3: Refactor Highlight Overlay Styling (Non-Obscuring Highlighter & External Floating Tag)**
  - Files: `frontend/src/components/PdfViewer.tsx`, `frontend/src/app/globals.css`
  - RED: Purple overlay badge and snippet preview render inside `.pdf-highlight-overlay`, covering document text (e.g. line 16).
  - GREEN:
    - Redesign `.pdf-highlight-overlay` in `globals.css` to act as a translucent text highlighter fill (`background: rgba(254, 240, 138, 0.45)`, `border: 1.5px solid #eab308`).
    - Position tag badge (`Citation Match • Page X`) OUTSIDE the highlight rectangle (floating above top edge `top: -24px`), with `pointer-events: none`.
    - Remove snippet text block inside overlay rectangle so PDF text underneath is 100% legible and viewable.
    - Update `scrollIntoView` options to `{ behavior: "smooth", block: "center" }`.
  - Real-surface QA: Click citation badge in chat panel; verify highlight overlay highlights line text with translucent tint, tag floats neatly above, and document text remains fully legible.
  - Evidence: Screen / visual check confirming target text is clear, unblocked, and centered.
  - Cleanup: Remove test styles.
  - Commit: NO (Report draft message: `fix(frontend): refactor pdf highlight overlay to prevent text obscuration`)

## Parallel Execution Waves
- Wave 1: Task 1 (Canvas Alignment & Container Scale)
- Wave 2: Task 2 (Dynamic Text Snippet BBox Matching)
- Wave 3: Task 3 (Refactor Highlight Overlay & External Tag)

## Dependency Matrix
| Task | Depends on | Blocks | Can parallelize with |
|---|---|---|---|
| 1 | None | 2, 3 | None |
| 2 | Task 1 | 3 | None |
| 3 | Task 2 | Final Verification | None |

## Final Verification Wave
- [x] Run frontend build: `npm run build --prefix frontend`.
- [x] Verify zero build or compilation errors across TypeScript components.
- [x] Manual QA pass: Highlight overlay renders translucent yellow tint over exact target lines, tag badge floats above (`top: -24px`), and document text is 100% visible and unblocked.

Next: `start-work proper-pdf-highlighting-and-alignment`
