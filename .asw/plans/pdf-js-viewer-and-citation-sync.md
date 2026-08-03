# pdf-js-viewer-and-citation-sync

## TL;DR
Replace the static HTML paper sheet mock in `frontend/src/app/page.tsx` with an interactive PDF.js / canvas viewer using `pdfjs-dist`, integrate document fetching from the backend API (or static fallback), and implement citation sync so clicking a citation badge ([S5087..., Page 2, ¶1]) auto-scrolls the viewer to the exact page and renders a highlighted overlay box over the target paragraph/bbox.

## Objective
Provide a fully interactive PDF viewer in `frontend/src/app/page.tsx` powered by `pdfjs-dist` (or `react-pdf`), with smooth page rendering, scroll-into-view navigation, and animated paragraph highlight overlays whenever a citation badge (`[S5087..., Page 2, ¶1]`) is clicked.

## Non-goals
- Modifying backend endpoints or Qdrant vector storage schemas.
- Adding complex multi-document comparison split-screens beyond the current left-panel/right-panel layout.

## Discovery
- `frontend/src/app/page.tsx`: Currently renders a mock HTML paper template inside `.pdf-placeholder` and `.pdf-canvas-mock`.
- `frontend/src/app/globals.css`: Contains CSS rules for `.pdf-placeholder`, `.pdf-canvas-mock`, `.highlight-box`, and theme CSS variables (`--accent-primary`, `--bg-paper`, `--border-subtle`, etc.).
- `.agents/skills/pdf-highlight-sync/SKILL.md`: Defines the interaction workflow: badge click -> extract page & paragraph -> scroll viewer to page -> render highlight overlay on target paragraph/chunk.
- `TEMPPDF/`: Sample PDFs available (`S5087_Clean_Air_Act_Renewable_Biomass_Amendment.pdf`, `S4949_Rivers_and_Harbors_Conservation_Act.pdf`, etc.).
- PDF Rendering requirements: Next.js 16 (App Router) environment requires client-side rendering (`use client`) and dynamic worker configuration for PDF.js.

## Decisions
- **PDF Library**: Install `pdfjs-dist` (or lightweight react wrapper) to render PDF pages onto HTML5 `<canvas>` elements inside a scrollable container.
- **Worker Configuration**: Configure `pdfjsLib.GlobalWorkerOptions.workerSrc` using a CDN URL (e.g. `unpkg.com` / `cdnjs`) or static public worker file to ensure compatibility with Next.js SSR/client hydration.
- **Component Architecture**: Create `frontend/src/components/PdfViewer.tsx` to handle canvas rendering, page virtualization/stacking, canvas scaling, and overlay rendering.
- **Citation Sync Protocol**:
  - `Citation` interface extended to include optional `bbox?: [number, number, number, number]` (normalized or PDF coordinates `[x0, y0, x1, y1]`).
  - Active citation state passed down to `PdfViewer`.
  - Auto-scroll to target page canvas element using `Element.scrollIntoView({ behavior: 'smooth' })` or container `scrollTo`.
  - Draw/position absolute HTML overlay highlight box on top of the rendered page canvas scaled to match canvas display dimensions.

## TODOs

- [ ] **Task 1: Install PDF.js dependency & create reusable `PdfViewer` component**
  - Files: `frontend/package.json`, `frontend/src/components/PdfViewer.tsx`
  - RED: Run `npm run build --prefix frontend` (fails/checks component structure before implementation).
  - GREEN: Install `pdfjs-dist` (matching Next.js 16 / React 19 compatibility). Create `frontend/src/components/PdfViewer.tsx` accepting `pdfUrl`, `currentPage`, `activeCitation`, and callback for page changes. Load PDF document asynchronously, render page canvases sequentially or per active page with crisp resolution scaling (devicePixelRatio).
  - Real-surface QA: Render `PdfViewer` in a test route/standalone section with a sample PDF URL and confirm pages render clearly onto canvas.
  - Evidence: Successful `npm run build --prefix frontend` and visible canvas elements in DOM.
  - Cleanup: Remove temporary test props or mock canvas fallbacks.
  - Commit: NO (Report draft message: `feat(frontend): create interactive PDF.js canvas viewer component`)

- [ ] **Task 2: Replace static paper sheet mock in `frontend/src/app/page.tsx` with `PdfViewer`**
  - Files: `frontend/src/app/page.tsx`, `frontend/src/app/globals.css`
  - RED: Inspect `page.tsx` right panel (currently contains static HTML `.pdf-canvas-mock`).
  - GREEN: Import `PdfViewer` into `page.tsx` dynamically with `ssr: false` to avoid SSR window/worker issues. Replace the `.pdf-placeholder` mock code in the right panel with `<PdfViewer />`. Bind `pdfUrl` to backend document endpoint `/api/documents/{selectedCitation.docTitle}` (with fallback local path `/TEMPPDF/...` or public asset).
  - Real-surface QA: Load Next.js page (`npm run dev --prefix frontend`) and select a citation to verify raw PDF renders dynamically in right panel instead of static HTML mock text.
  - Evidence: DOM inspection confirming canvas element rendered inside right panel `.right-panel`.
  - Cleanup: None.
  - Commit: NO (Report draft message: `feat(frontend): replace static paper sheet mock with PDF.js viewer in main page`)

- [ ] **Task 3: Implement Citation Sync (Auto-scroll & Highlight Bounding Box Overlay)**
  - Files: `frontend/src/components/PdfViewer.tsx`, `frontend/src/app/globals.css`
  - RED: Clicking citation badge updates `selectedCitation` state, but canvas does not scroll or draw paragraph highlight box.
  - GREEN:
    1. Attach `ref` map to each rendered page container. When `selectedCitation.page` changes, calculate target page container and call `scrollIntoView({ behavior: "smooth", block: "start" })`.
    2. Compute highlight overlay bounding box using citation metadata (`bbox` or paragraph text match coordinates). Overlay absolute `<div>` with `border: 2px solid var(--accent-primary)`, semi-transparent background fill (`rgba(79, 70, 229, 0.18)` or theme variable), pulsing animation (`@keyframes highlightPulse`), and clear target label tag (`Page X, ¶Y`).
  - Real-surface QA: Click citation badge `[S5087..., Page 2, ¶1]` in left chat panel. Verify right panel auto-scrolls to Page 2 container and renders animated highlight box directly over target paragraph.
  - Evidence: Screen/DOM snapshot or browser evidence showing target page in view with highlight overlay.
  - Cleanup: Clear temporary inline debug logs.
  - Commit: NO (Report draft message: `feat(frontend): add citation sync auto-scroll and paragraph highlight overlay`)

## Parallel Execution Waves
- Wave 1: Task 1 (PDF.js installation & `PdfViewer` component)
- Wave 2: Task 2 (Replace static mock in `page.tsx`)
- Wave 3: Task 3 (Citation auto-scroll & highlight overlay sync)

## Dependency Matrix
| Task | Depends on | Blocks | Can parallelize with |
|---|---|---|---|
| 1 | None | 2 | None |
| 2 | Task 1 | 3 | None |
| 3 | Task 2 | Final Verification | None |

## Final Verification Wave
- [ ] Run Next.js lint & build: `npm run lint --prefix frontend` and `npm run build --prefix frontend`.
- [ ] Verify zero console runtime errors when switching theme dropdowns ("Modern Slate", "High Contrast Monochrome", etc.).
- [ ] Execute manual verification: launch dev server (`npm run dev --prefix frontend`), click citation badges in chat feed, verify smooth auto-scroll to Page 2 and active highlight box drawing around paragraph 1.

Next: `start-work pdf-js-viewer-and-citation-sync`
