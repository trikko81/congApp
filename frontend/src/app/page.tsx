"use client";

import React, { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import ChatPanel, { ChatMessage, CitationItem } from "@/components/ChatPanel";
import CivicFeedList from "@/components/CivicFeedList";
import LocalImpactPanel from "@/components/LocalImpactPanel";
import TopicFilters from "@/components/TopicFilters";
import {
  ChatApiResponse,
  CivicFeedItem,
  FeedResponse,
  TopicCategory,
  UploadApiResponse,
} from "@/types/civic";
import {
  Landmark,
  FileText,
  MapPin,
  Sparkles,
  ArrowLeftRight,
  Square,
  BookOpen,
  Terminal,
  Palette,
  Newspaper,
  MessageSquare,
} from "lucide-react";


// Dynamically load the PDF viewer to avoid SSR hydration mismatches.
const PdfViewer = dynamic(() => import("@/components/PdfViewer"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center text-xs text-muted-foreground">
      Initializing PDF Viewer...
    </div>
  ),
});

async function fetchApi(endpoint: string, options?: RequestInit): Promise<Response> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  // Same-origin requests use the Next.js rewrite. Never retry a write against a
  // second server because the first request may already have succeeded.
  return fetch(`${baseUrl || ""}${endpoint}`, options);
}

export default function TownWatchApp() {
  // Layouts 1-5 (Swappable via keys 1, 2, 3, 4, 5)
  const [activeLayout, setActiveLayout] = useState<1 | 2 | 3 | 4 | 5>(1);
  const [zenFocusedPane, setZenFocusedPane] = useState<"primary" | "secondary">("primary");

  const [activeCitation, setActiveCitation] = useState<{
    docTitle: string;
    page: number;
    snippet?: string;
  } | null>({
    docTitle: "Virginia_Beach_City_Council_Agenda_2026.pdf",
    page: 1,
  });

  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [leftPanelMode, setLeftPanelMode] = useState<"chat" | "feed" | "impact">("chat");
  const [feedItems, setFeedItems] = useState<CivicFeedItem[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<TopicCategory>("All");
  const [topicCounts, setTopicCounts] = useState<Record<string, number>>({});
  const [feedError, setFeedError] = useState<string | null>(null);
  const [selectedFeedItemId, setSelectedFeedItemId] = useState<string | undefined>();

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "msg-1",
      sender: "assistant",
      text: "### Welcome to TownWatch Civic Intelligence\nUpload municipal council agendas, ordinances, or meeting packets to synthesize civic intelligence. Query **zoning variances**, **millage rate adjustments**, or **capital project authorizations**.\n\n*Click any citation badge below to jump directly to the verified legal source page.*",
      citations: [
        {
          docTitle: "Virginia_Beach_City_Council_Agenda_2026.pdf",
          page: 1,
          ordinanceId: "RES-2026-44",
          snippet: "RESOLUTION NO. 2026-44: FISCAL YEAR 2026-2027 REAL PROPERTY TAX LEVY",
        },
        {
          docTitle: "Virginia_Beach_City_Council_Agenda_2026.pdf",
          page: 2,
          ordinanceId: "ORD-2026-102",
          snippet: "Ordinance 2026-102 approving setback reduction for Parcel 104-55-A.",
        },
      ],
      timestamp: "12:00 PM",
    },
  ]);

  const fetchFeed = useCallback(async (topic?: TopicCategory, signal?: AbortSignal) => {
    try {
      const topicQuery = topic && topic !== "All" ? `?topic=${encodeURIComponent(topic)}` : "";
      const res = await fetchApi(`/api/feed${topicQuery}`, { signal });
      if (!res.ok) throw new Error(`Feed request failed (${res.status})`);
      const data: FeedResponse = await res.json();
      const items: CivicFeedItem[] = (data.entries || []).map((e) => ({
          id: e.item_id,
          title: e.title,
          municipality: e.municipality || "Virginia Beach",
          date: e.date,
          category: e.category,
          summary_bullets: e.summary_bullets || [],
          ordinance_id: e.ordinance_id,
          page_start: e.page_start,
          page_end: e.page_end || e.page_start,
          doc_title: e.doc_title,
          locations: e.locations || [],
      }));
      setFeedItems(items);
      setFeedError(null);

      const counts: Record<string, number> = {};
      items.forEach((item) => {
        counts[item.category] = (counts[item.category] || 0) + 1;
      });
      setTopicCounts(counts);
    } catch {
      if (signal?.aborted) return;
      setFeedError("Unable to load civic items. Check that the backend is running, then try again.");
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    // Synchronize the selected topic with the backend feed.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchFeed(selectedTopic, controller.signal);
    return () => controller.abort();
  }, [fetchFeed, selectedTopic]);

  const handleSelectFeedItem = (item: CivicFeedItem) => {
    setSelectedFeedItemId(item.id);
    setActiveCitation({
      docTitle: item.doc_title,
      page: item.page_start,
      snippet: item.summary_bullets.length > 0 ? item.summary_bullets[0] : item.title,
    });
    if (activeLayout === 5) {
      setZenFocusedPane("secondary");
    }
  };


  // Hydrate stored layout preferences
  useEffect(() => {
    try {
      const savedLayout = localStorage.getItem("townwatch_layout");
      const layoutNum =
        savedLayout && ["1", "2", "3", "4", "5"].includes(savedLayout)
          ? (Number(savedLayout) as 1 | 2 | 3 | 4 | 5)
          : 1;
      // Applying persisted UI preferences after hydration is intentional.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setActiveLayout(layoutNum);
      if (typeof document !== "undefined") {
        document.documentElement.setAttribute("data-theme", String(layoutNum));
        document.body.className = `theme-${layoutNum}`;
      }
    } catch {
      // Ignore localStorage access restrictions
    }
  }, []);

  const handleUpdateLayout = useCallback((layout: 1 | 2 | 3 | 4 | 5) => {
    setActiveLayout(layout);
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-theme", String(layout));
      document.body.className = `theme-${layout}`;
    }
    try {
      localStorage.setItem("townwatch_layout", String(layout));
    } catch {
      // Layout remains active for this session if storage is unavailable.
    }
  }, []);

  // Keyboard shortcut listener: 1, 2, 3, 4, 5 (guarded against inputs)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeEl = document.activeElement;
      const tagName = activeEl?.tagName.toUpperCase();
      if (
        tagName === "INPUT" ||
        tagName === "TEXTAREA" ||
        tagName === "SELECT" ||
        (activeEl as HTMLElement)?.isContentEditable
      ) {
        return;
      }

      if (e.key === "1") handleUpdateLayout(1);
      else if (e.key === "2") handleUpdateLayout(2);
      else if (e.key === "3") handleUpdateLayout(3);
      else if (e.key === "4") handleUpdateLayout(4);
      else if (e.key === "5") handleUpdateLayout(5);
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleUpdateLayout]);

  const handleSendMessage = async (query: string) => {
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);

    try {
      const res = await fetchApi("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      if (res.ok) {
        const data: ChatApiResponse = await res.json();
        const botMsg: ChatMessage = {
          id: `msg-${Date.now() + 1}`,
          sender: "assistant",
          text: data.answer || "No details found.",
          citations: (data.citations || []).map((c) => ({
            docTitle: c.doc_title || "Document",
            page: c.page || 1,
            snippet: c.snippet || "",
            ordinanceId: c.ordinance_id || c.doc_title,
            chapterId: c.chapter_id,
          })),
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };

        setMessages((prev) => [...prev, botMsg]);

      } else {
        throw new Error(`API returned ${res.status}`);
      }
    } catch (error) {
      const reason = error instanceof Error ? error.message : "unknown error";
      const botMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        sender: "assistant",
        text: `The civic search request failed (${reason}). No answer was generated.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, botMsg]);
    } finally {
      setIsStreaming(false);
    }
  };

  const handleUploadFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setMessages((prev) => [...prev, {
        id: `msg-${Date.now()}`,
        sender: "assistant",
        text: "Choose a PDF file. The upload endpoint does not accept ZIP or JSON files.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      }]);
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setMessages((prev) => [...prev, {
        id: `msg-${Date.now()}`,
        sender: "assistant",
        text: "This PDF exceeds the 50 MB upload limit.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      }]);
      return;
    }

    setIsStreaming(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetchApi("/api/ingest/upload", {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data: UploadApiResponse = await res.json();
        const categoriesList = Object.entries(data.categories_found || {})
          .map(([cat, count]) => `• **${cat}**: ${count} item(s)`)
          .join("\n");

        const uploadMsg: ChatMessage = {
          id: `msg-${Date.now()}`,
          sender: "assistant",
          text: `📥 **Successfully Ingested & Vectorized:** \`${data.filename}\`\n\n- **Total Pages**: ${data.total_pages}\n- **Synthesized Agenda Items**: ${data.total_items}\n- **Geocoded Parcels**: ${data.parcels_found}\n\n**Categories Identified:**\n${categoriesList}\n\nYou can now ask questions about this document and open cited pages in the PDF viewer.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setMessages((prev) => [...prev, uploadMsg]);

        setActiveCitation({
          docTitle: data.filename,
          page: 1,
        });
        if (activeLayout === 5) setZenFocusedPane("secondary");
        fetchFeed(selectedTopic);
      } else {
        throw new Error(`Upload returned status ${res.status}`);
      }
    } catch (error) {
      const reason = error instanceof Error ? error.message : "unknown error";
      const uploadMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        sender: "assistant",
        text: `The upload of **${file.name}** failed (${reason}). The file was not confirmed as indexed.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, uploadMsg]);
    } finally {
      setIsStreaming(false);
    }
  };

  const handleCitationClick = (citation: CitationItem) => {
    let docTitle = (citation.docTitle || "").trim();
    if (!docTitle) {
      docTitle = "Virginia_Beach_City_Council_Agenda_2026.pdf";
    }
    if (!docTitle.toLowerCase().endsWith(".pdf")) {
      docTitle = `${docTitle}.pdf`;
    }

    setActiveCitation({
      docTitle,
      page: citation.page || 1,
      snippet: citation.snippet,
    });
    // In Zen Focus layout (5), unhide secondary pane automatically
    if (activeLayout === 5) {
      setZenFocusedPane("secondary");
    }
  };

  // Layout preset helper classes
  const layoutClassMap: Record<number, string> = {
    1: "layout-preset-1",
    2: "layout-preset-2",
    3: "layout-preset-3",
    4: "layout-preset-4",
    5: "layout-preset-5",
  };

  return (
    <div
      className={`townwatch-workspace theme-${activeLayout}`}
      data-theme={String(activeLayout)}
    >
      {/* ── Apple frosted glass header ── */}
      <header className="townwatch-header">
        {/* Brand */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: "var(--accent-primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 2px 8px rgba(0,0,0,0.18)",
              flexShrink: 0,
            }}
          >
            <Landmark size={17} color="#fff" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <h1
                style={{
                  fontSize: "0.875rem",
                  fontWeight: 700,
                  letterSpacing: "-0.01em",
                  color: "var(--text-dark)",
                  fontFamily: "var(--font-main)",
                }}
              >
                TownWatch
              </h1>
              <span
                style={{
                  fontSize: "0.65rem",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  background: "var(--accent-light)",
                  color: "var(--accent-primary)",
                  padding: "2px 7px",
                  borderRadius: 100,
                }}
              >
                Civic intelligence
              </span>
            </div>
            <p
              style={{
                fontSize: "0.7rem",
                color: "var(--text-muted)",
                fontFamily: "var(--font-main)",
                display: "none",
              }}
              className="sm:block"
            >
              Municipal updates, grounded in public records
            </p>
          </div>
        </div>

        {/* Right: theme pills and PDF viewer indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <div className="theme-pill-group">
            {([
              [1, "Light", <Sparkles key="s" size={11} />],
              [2, "Dark", <Square key="sq" size={11} />],
              [3, "Sand", <BookOpen key="b" size={11} />],
              [4, "Night", <Terminal key="t" size={11} />],
              [5, "Glass", <Palette key="p" size={11} />],
            ] as [1 | 2 | 3 | 4 | 5, string, React.ReactNode][]).map(([num, label, icon]) => (
              <button
                key={num}
                onClick={() => handleUpdateLayout(num)}
                title={`Theme ${num}: ${label} (Press '${num}')`}
                aria-label={`Use ${label} theme and layout`}
                aria-pressed={activeLayout === num}
                className={`theme-pill${activeLayout === num ? " active" : ""}`}
              >
                {icon}
                <span>{num}</span>
                <span style={{ fontSize: "0.68rem", opacity: 0.75 }}>{label}</span>
              </button>
            ))}
          </div>

          <div className="tab-pill-group">
            <span className="tab-pill active" aria-current="page">
              <FileText size={11} />
              <span className="hidden sm:inline">PDF Evidence</span>
            </span>
          </div>
        </div>
      </header>

      {/* ── Main Workspace ── */}
      <main className={`townwatch-layout-container ${layoutClassMap[activeLayout]} relative`}>
        {/* Left Pane: LLM Civic RAG Synthesis or Structured Civic Feed */}
        <section
          className={`h-full overflow-hidden flex flex-col ${
            activeLayout === 5
              ? zenFocusedPane === "primary"
                ? "zen-active"
                : "zen-hidden"
              : ""
          }`}
        >
          {/* Assistant, civic feed, and locality-focused law view */}
          <div className="left-mode-header shrink-0 border-b border-border bg-card/70 px-3 py-3">
            <div className="left-mode-tabs" role="group" aria-label="TownWatch sections">
              <button
                onClick={() => setLeftPanelMode("chat")}
                aria-pressed={leftPanelMode === "chat"}
                className={`tab-pill left-mode-tab${leftPanelMode === "chat" ? " active" : ""}`}
              >
                <MessageSquare size={14} />
                <span>AI Assistant</span>
              </button>
              <button
                onClick={() => setLeftPanelMode("feed")}
                aria-pressed={leftPanelMode === "feed"}
                className={`tab-pill left-mode-tab${leftPanelMode === "feed" ? " active" : ""}`}
              >
                <Newspaper size={14} />
                <span>Civic Feed</span>
                {feedItems.length > 0 && (
                  <span className={`left-mode-count${leftPanelMode === "feed" ? " active" : ""}`}>
                    {feedItems.length}
                  </span>
                )}
              </button>
              <button
                onClick={() => setLeftPanelMode("impact")}
                aria-pressed={leftPanelMode === "impact"}
                className={`tab-pill left-mode-tab${leftPanelMode === "impact" ? " active" : ""}`}
              >
                <MapPin size={14} />
                <span>Your area</span>
              </button>
            </div>
            <p className="left-mode-description">
              {leftPanelMode === "chat"
                ? "Answers grounded in your documents"
                : leftPanelMode === "feed"
                  ? "Recent council agenda items"
                  : "Recent laws mentioning your locality"}
            </p>
          </div>

          {leftPanelMode === "chat" ? (
            <div className="flex-1 overflow-hidden flex flex-col">
              <ChatPanel
                messages={messages}
                isStreaming={isStreaming}
                onSendMessage={handleSendMessage}
                onUploadFile={handleUploadFile}
                onCitationClick={handleCitationClick}
              />
            </div>
          ) : leftPanelMode === "feed" ? (
            <div className="flex-1 overflow-hidden flex flex-col bg-background">
              <TopicFilters
                selectedCategory={selectedTopic}
                onSelectCategory={(cat) => {
                  setSelectedTopic(cat);
                }}
                counts={topicCounts}
              />
              {feedError && (
                <div className="api-error-banner" role="status">
                  <span>{feedError}</span>
                  <button type="button" onClick={() => fetchFeed(selectedTopic)}>Retry</button>
                </div>
              )}
              <div className="flex-1 overflow-y-auto">
                <CivicFeedList
                  items={feedItems}
                  selectedItemId={selectedFeedItemId}
                  onSelectItem={handleSelectFeedItem}
                />
              </div>
            </div>
          ) : (
            <LocalImpactPanel
              onOpenPdf={handleCitationClick}
              onAskAboutBill={(query) => {
                setLeftPanelMode("chat");
                void handleSendMessage(query);
              }}
            />
          )}
        </section>

        {/* Right Pane: PDF evidence viewer */}
        <section
          className={`h-full flex flex-col overflow-hidden ${
            activeLayout === 5
              ? zenFocusedPane === "secondary"
                ? "zen-active"
                : "zen-hidden"
              : ""
          }`}
          style={{
            background: "var(--bg-elevated)",
            borderLeft: "0.5px solid var(--border-subtle)",
          }}
        >
          <div className="h-full w-full flex flex-col">
              <div
                style={{
                  padding: "8px 16px",
                  borderBottom: "0.5px solid var(--border-subtle)",
                  background: "var(--bg-panel)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  fontSize: "0.78rem",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                  <FileText size={13} style={{ color: "var(--accent-primary)" }} />
                  <span
                    style={{ fontWeight: 600, color: "var(--text-dark)" }}
                    className="truncate max-w-sm"
                  >
                    {activeCitation?.docTitle || "Municipal Agenda Packet"}
                  </span>
                </div>
                {activeCitation && (
                  <span
                    style={{
                      fontSize: "0.7rem",
                      background: "var(--accent-light)",
                      color: "var(--accent-primary)",
                      padding: "2px 8px",
                      borderRadius: 6,
                      fontWeight: 600,
                    }}
                  >
                    Verified Page {activeCitation.page}
                  </span>
                )}
              </div>
              <div className="flex-1 overflow-hidden relative">
                <PdfViewer
                  key={activeCitation?.docTitle || "default-document"}
                  pdfUrl={`/api/documents/${
                    activeCitation?.docTitle || "Virginia_Beach_City_Council_Agenda_2026.pdf"
                  }`}
                  activeCitation={activeCitation}
                />
              </div>
          </div>
        </section>

        {/* Zen mode quick-swap switcher (Layout 5) */}
        {activeLayout === 5 && (
          <div style={{ position: "absolute", bottom: 24, right: 24, zIndex: 40 }}>
            <button
              onClick={() =>
                setZenFocusedPane(zenFocusedPane === "primary" ? "secondary" : "primary")
              }
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "9px 20px",
                borderRadius: 100,
                background: "var(--accent-primary)",
                color: "#fff",
                border: "none",
                fontWeight: 600,
                fontSize: "0.8rem",
                fontFamily: "var(--font-main)",
                cursor: "pointer",
                boxShadow: "0 4px 18px rgba(0,0,0,0.22)",
              }}
            >
              <ArrowLeftRight size={14} />
              <span>
                Switch to {zenFocusedPane === "primary" ? "PDF Evidence" : "Civic AI Synthesis"}
              </span>
            </button>
          </div>
        )}
      </main>

    </div>
  );
}
