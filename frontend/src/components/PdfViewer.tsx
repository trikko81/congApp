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
  scale: number;
}

export default function PdfViewer({ pdfUrl, activeCitation }: PdfViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<{ [pageNumber: number]: HTMLDivElement | null }>({});
  
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [numPages, setNumPages] = useState<number>(0);
  const [renderedPages, setRenderedPages] = useState<{ [pageNumber: number]: RenderedPage }>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Load PDF Document
  useEffect(() => {
    let isMounted = true;

    const loadingTask = pdfjsLib.getDocument(pdfUrl);
    loadingTask.promise
      .then((doc) => {
        if (!isMounted) return;
        setPdfDoc(doc);
        setNumPages(doc.numPages);
        setLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error("Error loading PDF:", err);
        setError("Failed to load PDF document.");
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [pdfUrl]);

  // Render individual page canvas
  const renderPage = useCallback(
    async (pageNumber: number, containerEl: HTMLDivElement) => {
      if (!pdfDoc) return;
      try {
        const page = await pdfDoc.getPage(pageNumber);
        
        // Calculate scale to fit container width
        const containerWidth = containerEl.clientWidth || 600;
        const unscaledViewport = page.getViewport({ scale: 1.0 });
        const scale = containerWidth / unscaledViewport.width;
        const viewport = page.getViewport({ scale });

        // High DPI display support
        const pixelRatio = window.devicePixelRatio || 1;
        
        // Canvas setup
        let canvas = containerEl.querySelector<HTMLCanvasElement>("canvas");
        if (!canvas) {
          canvas = document.createElement("canvas");
          containerEl.prepend(canvas);
        }

        canvas.width = Math.floor(viewport.width * pixelRatio);
        canvas.height = Math.floor(viewport.height * pixelRatio);
        canvas.style.width = `${Math.floor(viewport.width)}px`;
        canvas.style.height = `${Math.floor(viewport.height)}px`;

        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.scale(pixelRatio, pixelRatio);
          const renderContext = {
            canvasContext: ctx,
            viewport: viewport,
          };
          await page.render(renderContext).promise;
        }

        setRenderedPages((prev) => ({
          ...prev,
          [pageNumber]: {
            pageNumber,
            viewportWidth: viewport.width,
            viewportHeight: viewport.height,
            scale,
          },
        }));
      } catch (err) {
        console.error(`Error rendering PDF page ${pageNumber}:`, err);
      }
    },
    [pdfDoc]
  );

  // Trigger page rendering when pdfDoc loads or window resizes
  useEffect(() => {
    if (!pdfDoc || numPages === 0) return;

    for (let i = 1; i <= numPages; i++) {
      const el = pageRefs.current[i];
      if (el) {
        renderPage(i, el);
      }
    }
  }, [pdfDoc, numPages, renderPage]);

  // Handle citation auto-scroll
  useEffect(() => {
    if (!activeCitation || !activeCitation.page) return;

    const targetPageEl = pageRefs.current[activeCitation.page];
    if (targetPageEl) {
      targetPageEl.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }, [activeCitation]);

  // Calculate overlay highlight style if citation active
  const getHighlightStyle = (pageNumber: number) => {
    if (!activeCitation || activeCitation.page !== pageNumber) return null;
    const pageMeta = renderedPages[pageNumber];
    if (!pageMeta) return null;

    // Standard default box or custom bbox
    // If bbox present [x0, y0, x1, y1] normalized (0..1) or PDF points
    let top = 180;
    let left = 40;
    let width = pageMeta.viewportWidth - 80;
    let height = 90;

    if (activeCitation.bbox && activeCitation.bbox.length === 4) {
      const [x0, y0, x1, y1] = activeCitation.bbox;
      // If normalized coordinates
      if (x1 <= 1.0 && y1 <= 1.0) {
        left = x0 * pageMeta.viewportWidth;
        top = y0 * pageMeta.viewportHeight;
        width = (x1 - x0) * pageMeta.viewportWidth;
        height = (y1 - y0) * pageMeta.viewportHeight;
      } else {
        // PDF point scale
        left = x0 * pageMeta.scale;
        top = y0 * pageMeta.scale;
        width = (x1 - x0) * pageMeta.scale;
        height = (y1 - y0) * pageMeta.scale;
      }
    } else if (activeCitation.paragraph) {
      // Estimate vertical offset based on paragraph index
      top = 120 + (activeCitation.paragraph - 1) * 110;
      height = 80;
    }

    return {
      position: "absolute" as const,
      top: `${top}px`,
      left: `${left}px`,
      width: `${width}px`,
      height: `${height}px`,
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
            return (
              <div
                key={pageNum}
                className="pdf-page-card"
                ref={(el) => { pageRefs.current[pageNum] = el; }}
              >
                <div className="pdf-page-header">
                  <span>Page {pageNum} of {numPages}</span>
                </div>
                
                <div className="pdf-canvas-wrapper" style={{ position: "relative" }}>
                  {/* Canvas injected here */}
                  
                  {highlightStyle && (
                    <div className="pdf-highlight-overlay" style={highlightStyle}>
                      <span className="pdf-highlight-tag">
                        Citation Match • Page {pageNum}{activeCitation?.paragraph ? ` • ¶${activeCitation.paragraph}` : ""}
                      </span>
                      {activeCitation?.snippet && (
                        <p className="pdf-highlight-snippet-preview">{activeCitation.snippet}</p>
                      )}
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
