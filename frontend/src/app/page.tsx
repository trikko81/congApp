"use client";

import { useState, useEffect, useRef } from "react";
import dynamic from "next/dynamic";

const PdfViewer = dynamic(() => import("@/components/PdfViewer"), {
  ssr: false,
  loading: () => (
    <div className="pdf-viewer-status">
      <span>Initializing Canvas Viewer...</span>
    </div>
  ),
});

interface Citation {
  docTitle: string;
  page: number;
  paragraph: number;
  snippet: string;
  bbox?: [number, number, number, number];
}

interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  citations?: Citation[];
}

interface Turn {
  id: string;
  userMessage: Message;
  assistantMessage?: Message;
}

export default function OrdinanceRAGPage() {
  const [theme, setTheme] = useState<"slate" | "contrast" | "coastal" | "charcoal" | "warm">("slate");
  const [isTyping, setIsTyping] = useState(false);

  const [turns, setTurns] = useState<Turn[]>([]);

  const [inputQuery, setInputQuery] = useState("");
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  const chatFeedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (chatFeedRef.current) {
      chatFeedRef.current.scrollTo({
        top: chatFeedRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [turns, isTyping]);

  const handleSend = async () => {
    if (!inputQuery.trim() || isTyping) return;

    const queryText = inputQuery.trim();
    const turnId = `turn-${Date.now()}`;
    const userMsg: Message = {
      id: `msg-${Date.now()}`,
      sender: "user",
      text: queryText,
    };

    const newTurn: Turn = {
      id: turnId,
      userMessage: userMsg,
    };

    setTurns((prev) => [...prev, newTurn]);
    setInputQuery("");
    setIsTyping(true);

    try {
      let res: Response;
      try {
        res = await fetch("http://localhost:8000/api/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: queryText, limit: 3 }),
        });
      } catch {
        res = await fetch("http://localhost:8001/api/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: queryText, limit: 3 }),
        });
      }

      if (!res.ok) {
        throw new Error(`Search API error: ${res.status} ${res.statusText}`);
      }

      const data = await res.json();
      const results: Array<{
        doc_title: string;
        page: number;
        paragraph: number;
        text_chunk: string;
        snippet: string;
        bbox?: [number, number, number, number];
      }> = data.results || [];

      let assistantText = "";
      const citations: Citation[] = [];

      if (results.length === 0) {
        assistantText = `No relevant ordinance sections found matching "${queryText}".`;
      } else {
        assistantText = `Found ${results.length} relevant excerpt${results.length > 1 ? "s" : ""} in the bill index:\n\n` +
          results.map((r, i) => `[${i + 1}] "${r.text_chunk || r.snippet}"`).join("\n\n");

        results.forEach((r) => {
          const cit: Citation = {
            docTitle: r.doc_title,
            page: r.page,
            paragraph: r.paragraph,
            snippet: r.text_chunk || r.snippet,
            bbox: r.bbox,
          };
          citations.push(cit);
        });

        if (citations.length > 0) {
          setSelectedCitation(citations[0]);
        }
      }

      const assistantMsg: Message = {
        id: `msg-${Date.now() + 1}`,
        sender: "assistant",
        text: assistantText,
        citations: citations.length > 0 ? citations : undefined,
      };

      setTurns((prev) =>
        prev.map((t) =>
          t.id === turnId ? { ...t, assistantMessage: assistantMsg } : t
        )
      );
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      console.error("Failed to query FastAPI search API:", err);
      const assistantMsg: Message = {
        id: `msg-${Date.now() + 1}`,
        sender: "assistant",
        text: `Unable to connect to backend search engine (http://localhost:8000/api/search). Please ensure the FastAPI server is running. (${errorMessage})`,
      };

      setTurns((prev) =>
        prev.map((t) =>
          t.id === turnId ? { ...t, assistantMessage: assistantMsg } : t
        )
      );
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="main-viewport">
      <nav className="top-navbar">
        <div className="nav-brand">
          <span>ORDINANCERAG</span>
          <span className="badge-tag" style={{ background: "rgba(255,255,255,0.2)", color: "#ffffff", borderColor: "#ffffff" }}>
            v1.0 Local
          </span>
        </div>

        <div className="nav-links">
          <span className="nav-link active">Search Engine</span>
          <span className="nav-link">Bill Database</span>
          <span className="nav-link">API Docs</span>
          <span className="nav-link">Analytics</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <select
            value={theme}
            onChange={(e) => setTheme(e.target.value as "slate" | "contrast" | "coastal" | "charcoal" | "warm")}
            className="theme-selector"
          >
            <option value="slate">Modern Slate (Default)</option>
            <option value="contrast">High Contrast Monochrome</option>
            <option value="coastal">Soft Coastal (#B3C8CF)</option>
            <option value="charcoal">Muted Charcoal (#37353E)</option>
            <option value="warm">Warm Palette (#776B5D)</option>
          </select>

          <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.85)", fontFamily: "var(--font-code)" }}>
            383 Chunks Vectorized
          </span>
          <button className="nav-cta-btn">Export Vault</button>
        </div>
      </nav>

      <main className="app-container">
        <div className="app-wrapper">
          <section className="left-panel">
            <header className="panel-header">
              <div className="panel-header-title-group">
                <span className="panel-header-title">Grounded Intelligence Agent</span>
                <span className="badge-tag">Zero Hallucination</span>
              </div>
            </header>

            <div className="chat-feed" ref={chatFeedRef}>
              {turns.length === 0 && !isTyping && (
                <div className="pdf-viewer-status" style={{ border: "none", background: "transparent" }}>
                  <p>Ask a question about municipal ordinances or legislative bills to get grounded citations.</p>
                </div>
              )}

              {turns.map((turn) => (
                <div key={turn.id} className="chat-turn-group">
                  <div className="message-card message-user">
                    <p>{turn.userMessage.text}</p>
                  </div>

                  {turn.assistantMessage && (
                    <div className="message-card message-assistant">
                      <p>{turn.assistantMessage.text}</p>
                      {turn.assistantMessage.citations && (
                        <div style={{ marginTop: "10px", display: "flex", flexWrap: "wrap", gap: "6px" }}>
                          {turn.assistantMessage.citations.map((cit, idx) => (
                            <button
                              key={idx}
                              className="citation-badge"
                              onClick={() => setSelectedCitation(cit)}
                            >
                              [{cit.docTitle.replace(".pdf", "")}, Page {cit.page}, ¶{cit.paragraph}]
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {isTyping && (
                <div className="chat-turn-group">
                  <div className="message-card message-assistant" style={{ padding: "0.75rem 1.25rem" }}>
                    <div className="typing-indicator">
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="input-area">
              <div className="input-box">
                <input
                  type="text"
                  className="input-field"
                  placeholder="Search ordinance text or ask a question..."
                  value={inputQuery}
                  onChange={(e) => setInputQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                />
                <button className="send-btn" onClick={handleSend}>
                  {isTyping ? "Thinking..." : "Ask AI"}
                </button>
              </div>
            </div>
          </section>

          {/* Right Column: PDF Canvas View (60% Width) */}
          <section className="right-panel">
            <header className="panel-header">
              <div className="panel-header-title-group">
                <span className="panel-header-title">PDF Canvas Traceability</span>
                {selectedCitation && (
                  <span className="badge-tag">
                    Page {selectedCitation.page} • ¶{selectedCitation.paragraph}
                  </span>
                )}
              </div>
              <span className="filename-meta">
                {selectedCitation ? selectedCitation.docTitle : "No Document Selected"}
              </span>
            </header>

            {selectedCitation ? (
              <PdfViewer
                pdfUrl={`/${selectedCitation.docTitle}`}
                activeCitation={selectedCitation}
              />
            ) : (
              <div className="pdf-viewer-status">
                <p>Select a citation badge in the left panel to auto-scroll and highlight the PDF.</p>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
