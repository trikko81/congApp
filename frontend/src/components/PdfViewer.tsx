"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import * as pdfjsLib from "pdfjs-dist";

// Configure pdfjs worker source: prefer local worker in public/, fallback to CDN
if (typeof window !== "undefined") {
  pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
}

export interface CitationHighlight {
  docTitle: string;
  page: number;
  paragraph?: number;
  snippet?: string;
  bbox?: [number, number, number, number]; // [x0, y0, x1, y1] normalized (0..1) or PDF units
}

interface PdfViewerProps {
  pdfUrl: string;
  activeCitation?: CitationHighlight | null;
}

interface RenderedPage {
  pageNumber: number;
  viewportWidth: number;
  viewportHeight: number;
  unscaledWidth: number;
  unscaledHeight: number;
  scale: number;
  textItems: Array<{ str: string; x: number; y: number; width: number; height: number }>;
}

interface HighlightBox {
  left: number;
  top: number;
  width: number;
  height: number;
}

function normalizedWords(value: string): string[] {
  return value.toLocaleLowerCase().match(/[\p{L}\p{N}]+/gu) ?? [];
}

export default function PdfViewer({ pdfUrl, activeCitation }: PdfViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef<{ [pageNumber: number]: HTMLDivElement | null }>({});
  const wrapperRefs = useRef<{ [pageNumber: number]: HTMLDivElement | null }>({});
  const renderTasksRef = useRef<{ [pageNumber: number]: pdfjsLib.RenderTask | null }>({});

  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [numPages, setNumPages] = useState<number>(0);
  const [renderedPages, setRenderedPages] = useState<{ [pageNumber: number]: RenderedPage }>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const cancelRenderTasks = () => {
    Object.values(renderTasksRef.current).forEach((task) => {
      try {
        task?.cancel();
      } catch {}
    });
    renderTasksRef.current = {};
  };

  useEffect(() => {
    let isMounted = true;
    cancelRenderTasks();

    const tryLoad = async () => {
      // Normalize filename from any path or URL format
      let rawName = pdfUrl.split("/").pop() || pdfUrl;
      rawName = rawName.split("?")[0].split("#")[0];
      if (!rawName.toLowerCase().endsWith(".pdf")) {
        rawName = `${rawName}.pdf`;
      }
      const encodedName = encodeURIComponent(rawName);
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";

      const urlsToTry = [
        `/api/documents/${encodedName}`,
        `${apiBase}/api/documents/${encodedName}`,
        `http://localhost:8001/api/documents/${encodedName}`,
        pdfUrl.startsWith("/") ? pdfUrl : `/api/documents/${encodedName}`,
      ];

      for (const url of urlsToTry) {
        if (!isMounted) return;
        try {
          const loadingTask = pdfjsLib.getDocument(url);
          const doc = await loadingTask.promise;
          if (!isMounted) return;
          setPdfDoc(doc);
          setNumPages(doc.numPages);
          setLoading(false);
          return;
        } catch (err) {
          console.warn(`Failed to load PDF from ${url}:`, err);
        }
      }

      if (isMounted) {
        setError(`Could not open “${rawName}”. Confirm the document is available on the backend and try again.`);
        setLoading(false);
      }
    };

    tryLoad();

    return () => {
      isMounted = false;
      cancelRenderTasks();
    };
  }, [pdfUrl, retryCount]);

  const renderPage = useCallback(
    async (pageNumber: number, wrapperEl: HTMLDivElement) => {
      if (!pdfDoc) return;
      try {
        const page = await pdfDoc.getPage(pageNumber);
        const unscaledViewport = page.getViewport({ scale: 1.0 });

        const availableWidth =
          wrapperEl.clientWidth ||
          (containerRef.current ? containerRef.current.clientWidth - 48 : 600);
        const baseScale = Math.min(availableWidth / unscaledViewport.width, 1.4);

        const pixelRatio = window.devicePixelRatio || 1;
        const scaledViewport = page.getViewport({ scale: baseScale * pixelRatio });
        const displayViewport = page.getViewport({ scale: baseScale });

        const displayWidth = Math.floor(displayViewport.width);
        const displayHeight = Math.floor(displayViewport.height);

        let canvas = wrapperEl.querySelector<HTMLCanvasElement>("canvas");
        if (!canvas) {
          canvas = document.createElement("canvas");
          wrapperEl.prepend(canvas);
        }

        canvas.width = Math.floor(scaledViewport.width);
        canvas.height = Math.floor(scaledViewport.height);
        canvas.style.width = `${displayWidth}px`;
        canvas.style.height = `${displayHeight}px`;

        const ctx = canvas.getContext("2d");
        if (ctx) {
          if (renderTasksRef.current[pageNumber]) {
            try {
              renderTasksRef.current[pageNumber]?.cancel();
            } catch {}
          }

          const renderTask = page.render({
            canvasContext: ctx,
            viewport: scaledViewport,
          });
          renderTasksRef.current[pageNumber] = renderTask;

          try {
            await renderTask.promise;
          } catch (err: unknown) {
            if (
              err &&
              typeof err === "object" &&
              "name" in err &&
              err.name === "RenderingCancelledException"
            ) {
              return;
            }
            throw err;
          }
        }

        const textItems: Array<{
          str: string;
          x: number;
          y: number;
          width: number;
          height: number;
        }> = [];
        try {
          const textContent = await page.getTextContent();
          textContent.items.forEach((item) => {
            if ("str" in item && typeof item.str === "string" && item.str.trim() && "transform" in item) {
              const tx = item.transform;
              const [ptX, ptY] = displayViewport.convertToViewportPoint(tx[4], tx[5]);
              const itemWidth = ("width" in item && typeof item.width === "number" ? item.width : 0) * baseScale;
              const itemHeight = ("height" in item && typeof item.height === "number" ? item.height : 12) * baseScale;
              textItems.push({
                str: item.str,
                x: ptX,
                y: ptY - itemHeight,
                width: itemWidth,
                height: itemHeight,
              });
            }
          });
        } catch (e) {
          console.warn("Could not extract text content for page", pageNumber, e);
        }

        setRenderedPages((prev) => ({
          ...prev,
          [pageNumber]: {
            pageNumber,
            viewportWidth: displayWidth,
            viewportHeight: displayHeight,
            unscaledWidth: unscaledViewport.width,
            unscaledHeight: unscaledViewport.height,
            scale: baseScale,
            textItems,
          },
        }));
      } catch (err: unknown) {
        if (
          !err ||
          typeof err !== "object" ||
          !("name" in err) ||
          err.name !== "RenderingCancelledException"
        ) {
          console.error(`Error rendering PDF page ${pageNumber}:`, err);
        }
      }
    },
    [pdfDoc]
  );

  // Trigger page rendering when pdfDoc or numPages changes
  useEffect(() => {
    if (!pdfDoc || numPages === 0) return;

    for (let i = 1; i <= numPages; i++) {
      const el = wrapperRefs.current[i];
      if (el) {
        renderPage(i, el);
      }
    }
  }, [pdfDoc, numPages, renderPage]);

  // Handle citation auto-scroll (centered)
  useEffect(() => {
    if (!activeCitation || !activeCitation.page) return;

    const targetCardEl = cardRefs.current[activeCitation.page];
    if (targetCardEl) {
      targetCardEl.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  }, [activeCitation]);

  // Only highlight a passage when its complete normalized phrase is present.
  // Matching arbitrary individual words made unrelated paragraphs look cited.
  const getHighlightBoxes = (pageNumber: number): HighlightBox[] => {
    if (!activeCitation || activeCitation.page !== pageNumber) return [];
    const pageMeta = renderedPages[pageNumber];
    if (!pageMeta) return [];

    const wanted = normalizedWords(activeCitation.snippet ?? "");
    // Prefer the actual quoted passage. A paragraph bbox can be broad and may
    // highlight unrelated text when the quote is available but doesn't match.
    if (!wanted.length && activeCitation.bbox && activeCitation.bbox.length === 4) {
      const [x0, y0, x1, y1] = activeCitation.bbox;
      if (x1 <= 1.0 && y1 <= 1.0) {
        return [{ left: x0 * pageMeta.viewportWidth, top: y0 * pageMeta.viewportHeight, width: (x1 - x0) * pageMeta.viewportWidth, height: (y1 - y0) * pageMeta.viewportHeight }];
      }
      // PDF coordinates have a bottom-left origin; CSS coordinates have a top-left origin.
      const left = (x0 / pageMeta.unscaledWidth) * pageMeta.viewportWidth;
      const right = (x1 / pageMeta.unscaledWidth) * pageMeta.viewportWidth;
      const top = ((pageMeta.unscaledHeight - y1) / pageMeta.unscaledHeight) * pageMeta.viewportHeight;
      const bottom = ((pageMeta.unscaledHeight - y0) / pageMeta.unscaledHeight) * pageMeta.viewportHeight;
      return [{ left, top, width: right - left, height: bottom - top }];
    }
    if (!wanted.length) return [];

    const tokens = pageMeta.textItems.flatMap((item) =>
      Array.from(item.str.matchAll(/[\p{L}\p{N}]+/gu), (match) => {
        const start = match.index ?? 0;
        const tokenWidth = (item.width * match[0].length) / Math.max(1, item.str.length);
        return {
          word: match[0].toLocaleLowerCase(),
          box: {
            left: item.x + (item.width * start) / Math.max(1, item.str.length),
            top: item.y,
            width: Math.max(2, tokenWidth),
            height: item.height,
          },
        };
      })
    );

    for (let start = 0; start <= tokens.length - wanted.length; start++) {
      if (!wanted.every((word, offset) => tokens[start + offset].word === word)) continue;
      const matchedTokens = tokens.slice(start, start + wanted.length);
      const staysInReadingFlow = matchedTokens.slice(1).every((token, offset) => {
        const previous = matchedTokens[offset].box;
        const current = token.box;
        const verticalGap = current.top - previous.top;
        const sameLine = Math.abs(verticalGap) <= Math.max(3, previous.height * 0.55);
        if (sameLine) {
          const horizontalGap = current.left - (previous.left + previous.width);
          return horizontalGap >= -8 && horizontalGap <= Math.max(40, previous.height * 7);
        }
        return verticalGap > 0 && verticalGap <= Math.max(16, previous.height * 2.5);
      });
      if (!staysInReadingFlow) continue;

      const boxes = matchedTokens.map((token) => token.box);
      // Merge neighboring words on the same text line. Keep separate boxes on
      // wrapped lines so the highlight never paints over intervening content.
      const lines: HighlightBox[] = [];
      for (const box of boxes) {
        const previous = lines[lines.length - 1];
        if (previous && Math.abs(previous.top - box.top) < Math.max(4, box.height * 0.45) && box.left <= previous.left + previous.width + 8) {
          const right = Math.max(previous.left + previous.width, box.left + box.width);
          previous.left = Math.min(previous.left, box.left);
          previous.width = right - previous.left;
          previous.top = Math.min(previous.top, box.top);
          previous.height = Math.max(previous.height, box.height);
        } else {
          lines.push({ ...box });
        }
      }
      return lines;
    }

    return [];
  };

  return (
    <div className="pdf-viewer-scroll-container" ref={containerRef}>
      {loading && (
        <div className="pdf-viewer-status">
          <div className="typing-indicator" style={{ display: "inline-flex" }}>
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
          </div>
          <span>Loading PDF Document...</span>
        </div>
      )}

      {error && (
        <div className="pdf-viewer-status pdf-viewer-error flex flex-col items-center gap-3 w-full p-4" role="alert">
          <p className="text-xs font-medium">{error}</p>
          <button
            type="button"
            className="rounded-md border border-border px-3 py-1.5 text-xs text-foreground hover:bg-muted"
            onClick={() => {
              setError(null);
              setLoading(true);
              setRenderedPages({});
              setRetryCount((count) => count + 1);
            }}
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && (
        <div className="pdf-pages-stack">
          {Array.from({ length: numPages }, (_, idx) => idx + 1).map((pageNum) => {
            const highlightBoxes = getHighlightBoxes(pageNum);
            const pageMeta = renderedPages[pageNum];

            return (
              <div
                key={pageNum}
                className="pdf-page-card"
                ref={(el) => {
                  cardRefs.current[pageNum] = el;
                }}
              >
                <div className="pdf-page-header">
                  <span>
                    Page {pageNum} of {numPages}
                  </span>
                </div>

                <div
                  className="pdf-canvas-wrapper"
                  style={{
                    position: "relative",
                    width: pageMeta ? `${pageMeta.viewportWidth}px` : "100%",
                    height: pageMeta ? `${pageMeta.viewportHeight}px` : "auto",
                    margin: "0 auto",
                  }}
                  ref={(el) => {
                    wrapperRefs.current[pageNum] = el;
                  }}
                >
                  {/* Canvas is dynamically prepended here */}

                  {highlightBoxes.map((box, index) => (
                    <div
                      key={`${pageNum}-${index}`}
                      className="pdf-highlight-overlay"
                      style={{
                        top: `${Math.max(0, Math.round(box.top - 2))}px`,
                        left: `${Math.max(0, Math.round(box.left - 2))}px`,
                        width: `${Math.max(3, Math.round(box.width + 4))}px`,
                        height: `${Math.max(3, Math.round(box.height + 4))}px`,
                      }}
                      aria-label={index === 0 ? `Citation text on page ${pageNum}` : undefined}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
