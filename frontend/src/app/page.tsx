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

  const [turns, setTurns] = useState<Turn[]>([
    {
      id: "turn-1",
      userMessage: {
        id: "msg-1",
        sender: "user",
        text: "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
      },
      assistantMessage: {
        id: "msg-2",
        sender: "assistant",
        text: "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
        citations: [
          {
            docTitle: "S5087_Clean_Air_Act_Renewable_Biomass_Amendment.pdf",
            page: 1,
            paragraph: 2,
            snippet: "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo.",
          },
        ],
      },
    },
  ]);

  const [inputQuery, setInputQuery] = useState("");
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>({
    docTitle: "S5087_Clean_Air_Act_Renewable_Biomass_Amendment.pdf",
    page: 1,
    paragraph: 2,
    snippet:
      "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo.",
  });

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

  const handleSend = () => {
    if (!inputQuery.trim() || isTyping) return;

    const turnId = `turn-${Date.now()}`;
    const userMsg: Message = {
      id: `msg-${Date.now()}`,
      sender: "user",
      text: inputQuery,
    };

    const newTurn: Turn = {
      id: turnId,
      userMessage: userMsg,
    };

    setTurns((prev) => [...prev, newTurn]);
    setInputQuery("");
    setIsTyping(true);

    setTimeout(() => {
      const assistantMsg: Message = {
        id: `msg-${Date.now() + 1}`,
        sender: "assistant",
        text: `Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt.`,
        citations: [
          {
            docTitle: "S5087_Clean_Air_Act_Renewable_Biomass_Amendment.pdf",
            page: 2,
            paragraph: 1,
            snippet: "Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit, sed quia non numquam eius modi tempora incidunt ut labore et dolore magnam aliquam quaerat voluptatem.",
          },
        ],
      };

      setTurns((prev) =>
        prev.map((t) =>
          t.id === turnId ? { ...t, assistantMessage: assistantMsg } : t
        )
      );
      setIsTyping(false);
    }, 700);
  };

  return (
    <div className="main-viewport">
      {/* Full Width Top Navigation Bar */}
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
          {/* Interactive Theme Selector Dropdown */}
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

      {/* 80% Centered Container with Inset Floating Panes */}
      <main className="app-container">
        <div className="app-wrapper">
          {/* Left Column: Interactive Chat Interface (40% Width) */}
          <section className="left-panel">
            <header className="panel-header">
              <div className="panel-header-title-group">
                <span className="panel-header-title">Grounded Intelligence Agent</span>
                <span className="badge-tag">Zero Hallucination</span>
              </div>
            </header>

            <div className="chat-feed" ref={chatFeedRef}>
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
                  placeholder="Lorem ipsum dolor sit amet..."
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
