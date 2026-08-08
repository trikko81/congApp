"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import * as pdfjsLib from "pdfjs-dist";

// Configure pdfjs worker source using CDN matching current version
pdfjsLib.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`;

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
    setLoading(true);
    setError(null);
    setRenderedPages({});

    cancelRenderTasks();

    const tryLoad = async () => {
      const filename = pdfUrl.split("/").pop() || "";
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const urlsToTry = [
        pdfUrl,
        `${apiBase}/api/documents/${filename}`,
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
        setError(`Failed to load PDF document (${filename}).`);
        setLoading(false);
      }
    };

    tryLoad();

    return () => {
      isMounted = false;
      cancelRenderTasks();
    };
  }, [pdfUrl]);

  const renderPage = useCallback(
    async (pageNumber: number, wrapperEl: HTMLDivElement) => {
      if (!pdfDoc) return;
      try {
        const page = await pdfDoc.getPage(pageNumber);
        const unscaledViewport = page.getViewport({ scale: 1.0 });
        
        const availableWidth = wrapperEl.clientWidth || (containerRef.current ? containerRef.current.clientWidth - 48 : 600);
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
            if (err && typeof err === "object" && "name" in err && err.name === "RenderingCancelledException") {
              return;
            }
            throw err;
          }
        }

        const textItems: Array<{ str: string; x: number; y: number; width: number; height: number }> = [];
        try {
          const textContent = await page.getTextContent();
          textContent.items.forEach((item: Record<string, unknown>) => {
            if ("str" in item && typeof item.str === "string" && item.str.trim()) {
              const tx = item.transform as number[];
              const [ptX, ptY] = displayViewport.convertToViewportPoint(tx[4], tx[5]);
              const itemWidth = ((item.width as number) || 0) * baseScale;
              const itemHeight = ((item.height as number) || 12) * baseScale;
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
        if (!err || typeof err !== "object" || !("name" in err) || err.name !== "RenderingCancelledException") {
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

  // Calculate overlay highlight style if citation active
  const getHighlightStyle = (pageNumber: number) => {
    if (!activeCitation || activeCitation.page !== pageNumber) return null;
    const pageMeta = renderedPages[pageNumber];
    if (!pageMeta) return null;

    let left = 20;
    let top = 100;
    let width = pageMeta.viewportWidth - 40;
    let height = 40;

    // Option A: Dynamic Snippet Text BBox Search (Most accurate)
    let snippetMatched = false;
    if (activeCitation.snippet && pageMeta.textItems.length > 0) {
      const snippetWords = activeCitation.snippet
        .toLowerCase()
        .replace(/[^\w\s]/g, "")
        .split(/\s+/)
        .filter((w) => w.length > 3);

      if (snippetWords.length > 0) {
        const matchedItems = pageMeta.textItems.filter((item) => {
          const itemText = item.str.toLowerCase();
          return snippetWords.some((w) => itemText.includes(w));
        });

        if (matchedItems.length > 0) {
          let minX = Infinity;
          let minY = Infinity;
          let maxX = -Infinity;
          let maxY = -Infinity;

          matchedItems.forEach((item) => {
            if (item.x < minX) minX = item.x;
            if (item.y < minY) minY = item.y;
            if (item.x + item.width > maxX) maxX = item.x + item.width;
            if (item.y + item.height > maxY) maxY = item.y + item.height;
          });

          left = Math.max(10, minX - 4);
          top = Math.max(6, minY - 2);
          width = Math.min(pageMeta.viewportWidth - left - 10, maxX - minX + 8);
          height = Math.max(22, maxY - minY + 4);
          snippetMatched = true;
        }
      }
    }

    // Option B: Explicit BBox passed from backend
    if (!snippetMatched && activeCitation.bbox && activeCitation.bbox.length === 4) {
      const [x0, y0, x1, y1] = activeCitation.bbox;
      if (x1 <= 1.0 && y1 <= 1.0) {
        // Normalized [0..1]
        left = x0 * pageMeta.viewportWidth;
        top = y0 * pageMeta.viewportHeight;
        width = (x1 - x0) * pageMeta.viewportWidth;
        height = (y1 - y0) * pageMeta.viewportHeight;
      } else {
        // PDF point units (72 DPI)
        left = (x0 / pageMeta.unscaledWidth) * pageMeta.viewportWidth;
        top = (y0 / pageMeta.unscaledHeight) * pageMeta.viewportHeight;
        width = ((x1 - x0) / pageMeta.unscaledWidth) * pageMeta.viewportWidth;
        height = ((y1 - y0) / pageMeta.unscaledHeight) * pageMeta.viewportHeight;
      }
    } else if (!snippetMatched && activeCitation.paragraph) {
      top = Math.min(pageMeta.viewportHeight - 60, 80 + (activeCitation.paragraph - 1) * 70);
      height = 50;
    }

    return {
      position: "absolute" as const,
      top: `${Math.max(0, Math.round(top))}px`,
      left: `${Math.max(0, Math.round(left))}px`,
      width: `${Math.max(40, Math.round(width))}px`,
      height: `${Math.max(20, Math.round(height))}px`,
    };
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
        <div className="pdf-viewer-status pdf-viewer-error">
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && (
        <div className="pdf-pages-stack">
          {Array.from({ length: numPages }, (_, idx) => idx + 1).map((pageNum) => {
            const highlightStyle = getHighlightStyle(pageNum);
            const pageMeta = renderedPages[pageNum];

            return (
              <div
                key={pageNum}
                className="pdf-page-card"
                ref={(el) => { cardRefs.current[pageNum] = el; }}
              >
                <div className="pdf-page-header">
                  <span>Page {pageNum} of {numPages}</span>
                </div>
                
                <div
                  className="pdf-canvas-wrapper"
                  style={{
                    position: "relative",
                    width: pageMeta ? `${pageMeta.viewportWidth}px` : "100%",
                    height: pageMeta ? `${pageMeta.viewportHeight}px` : "auto",
                    margin: "0 auto",
                  }}
                  ref={(el) => { wrapperRefs.current[pageNum] = el; }}
                >
                  {/* Canvas is dynamically prepended here */}
                  
                  {highlightStyle && (
                    <div className="pdf-highlight-overlay" style={highlightStyle}>
                      <span className="pdf-highlight-tag">
                        Citation Match • Page {pageNum}{activeCitation?.paragraph ? ` • ¶${activeCitation.paragraph}` : ""}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

