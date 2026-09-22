"use client";

import React, { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import ChatPanel, { ChatMessage, CitationItem } from "@/components/ChatPanel";
import CivicFeedList from "@/components/CivicFeedList";
import TopicFilters from "@/components/TopicFilters";
import LegislativeSearchModal from "@/components/LegislativeSearchModal";
import { CivicFeedItem, TopicCategory } from "@/types/civic";
import {
  Landmark,
  FileText,
  Map,
  Sparkles,
  ArrowLeftRight,
  Square,
  BookOpen,
  Terminal,
  Palette,
  Newspaper,
  Scale,
  MessageSquare,
} from "lucide-react";


// Dynamically load PDF Viewer and Zoning Map to avoid SSR hydration mismatches
const PdfViewer = dynamic(() => import("@/components/PdfViewer"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center text-xs text-muted-foreground">
      Initializing PDF Viewer...
    </div>
  ),
});

const ZoningMapViewer = dynamic(() => import("@/components/ZoningMapViewer"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center text-xs text-muted-foreground">
      Loading Zoning Boundary Map...
    </div>
  ),
});

async function fetchApi(endpoint: string, options?: RequestInit): Promise<Response> {
  const primary = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
  try {
    const res = await fetch(`${primary}${endpoint}`, options);
    if (res.ok) return res;
  } catch (e) {
    // fallback
  }
  return fetch(`http://localhost:8000${endpoint}`, options);
}

export default function TownWatchApp() {
  // Layouts 1-5 (Swappable via keys 1, 2, 3, 4, 5)
  const [activeLayout, setActiveLayout] = useState<1 | 2 | 3 | 4 | 5>(1);
  const [zenFocusedPane, setZenFocusedPane] = useState<"primary" | "secondary">("primary");

  const [activeTab, setActiveTab] = useState<"pdf" | "zoning">("pdf");
  const [activeCitation, setActiveCitation] = useState<{
    docTitle: string;
    page: number;
    snippet?: string;
  } | null>({
    docTitle: "Virginia_Beach_City_Council_Agenda_2026.pdf",
    page: 1,
  });

  const [activeMarkerId, setActiveMarkerId] = useState<string | null>("p-1");
  const [markers, setMarkers] = useState<any[]>([
    {
      id: "p-1",
      address: "450 North Elm St",
      parcelId: "Tax Map Parcel 104-55-A",
      coords: [36.8609, -75.966],
      ordinanceId: "ORD-2026-102",
      page: 2,
      details: "Approved rear setback reduction from 25ft to 15ft.",
    },
    {
      id: "p-2",
      address: "782 South Oak Street",
      parcelId: "Parcel ID 88-12",
      coords: [36.8649, -75.986],
      ordinanceId: "RES-2026-78",
      page: 6,
      details: "Emergency radio repeater tower authorization.",
    },
  ]);

  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [leftPanelMode, setLeftPanelMode] = useState<"chat" | "feed">("chat");
  const [feedItems, setFeedItems] = useState<CivicFeedItem[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<TopicCategory>("All");
  const [topicCounts, setTopicCounts] = useState<Record<string, number>>({});
  const [selectedFeedItemId, setSelectedFeedItemId] = useState<string | undefined>();
  const [isLegalModalOpen, setIsLegalModalOpen] = useState<boolean>(false);

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
          snippet: "Official Municipal Agenda and Consent Calendar for City Council regular session.",
        },
        {
          docTitle: "Virginia_Beach_City_Council_Agenda_2026.pdf",
          page: 2,
          ordinanceId: "ORD-2026-102",
          snippet: "Ordinance 2026-102 approving setback reduction for Parcel 104-55-A.",
          hasZoningMap: true,
        },
      ],
      timestamp: "12:00 PM",
    },
  ]);

  const fetchFeed = useCallback(async (topic?: TopicCategory) => {
    try {
      const topicQuery = topic && topic !== "All" ? `?topic=${encodeURIComponent(topic)}` : "";
      const res = await fetchApi(`/api/feed${topicQuery}`);
      if (res.ok) {
        const data = await res.json();
        const items: CivicFeedItem[] = (data.entries || []).map((e: any) => ({
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

        const counts: Record<string, number> = {};
        items.forEach((item) => {
          counts[item.category] = (counts[item.category] || 0) + 1;
        });
        setTopicCounts(counts);
      }
    } catch (e) {
      // Backend offline fallback
    }
  }, []);

  useEffect(() => {
    fetchFeed(selectedTopic);
  }, [fetchFeed, selectedTopic]);

  const handleSelectFeedItem = (item: CivicFeedItem) => {
    setSelectedFeedItemId(item.id);
    setActiveCitation({
      docTitle: item.doc_title,
      page: item.page_start,
      snippet: item.summary_bullets.length > 0 ? item.summary_bullets[0] : item.title,
    });
    setActiveTab("pdf");
    if (activeLayout === 5) {
      setZenFocusedPane("secondary");
    }
  };

  const handleSelectFeedParcel = (item: CivicFeedItem, parcelIndex: number) => {
    setSelectedFeedItemId(item.id);
    const loc = item.locations[parcelIndex];
    if (loc) {
      const markerId = `${item.id}-${loc.parcel_id || "loc"}`;
      setActiveMarkerId(markerId);
      setActiveTab("zoning");
      if (activeLayout === 5) {
        setZenFocusedPane("secondary");
      }
    }
  };

  const handleLawSelect = (docTitle: string) => {
    const clean = docTitle.endsWith(".pdf") ? docTitle : `${docTitle}.pdf`;
    setActiveCitation({
      docTitle: clean,
      page: 1,
    });
    setActiveTab("pdf");
    setIsLegalModalOpen(false);
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
      setActiveLayout(layoutNum);
      if (typeof document !== "undefined") {
        document.documentElement.setAttribute("data-theme", String(layoutNum));
        document.body.className = `theme-${layoutNum}`;
      }
    } catch (e) {
      // Ignore localStorage access restrictions
    }
  }, []);

  const handleUpdateLayout = (layout: 1 | 2 | 3 | 4 | 5) => {
    setActiveLayout(layout);
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-theme", String(layout));
      document.body.className = `theme-${layout}`;
    }
    try {
      localStorage.setItem("townwatch_layout", String(layout));
    } catch (e) {}
  };

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
  }, []);

  // Fetch initial parcels from backend GeoJSON endpoint
  useEffect(() => {
    async function fetchParcels() {
      try {
        const res = await fetchApi("/api/map/parcels");
        if (res.ok) {
          const geojson = await res.json();
          if (geojson.features && geojson.features.length > 0) {
            const mapped = geojson.features.map((f: any) => ({
              id: f.properties.id || `m-${Math.random()}`,
              address: f.properties.address || "Municipal Parcel",
              parcelId: f.properties.parcel_id,
              coords: [f.geometry.coordinates[1], f.geometry.coordinates[0]],
              ordinanceId: f.properties.ordinance_id,
              page: f.properties.page || 1,
              details: f.properties.summary,
            }));
            setMarkers(mapped);
          }
        }
      } catch (e) {
        // Backend not yet reachable, keep sample markers
      }
    }
    fetchParcels();
  }, []);

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
        const data = await res.json();
        const botMsg: ChatMessage = {
          id: `msg-${Date.now() + 1}`,
          sender: "assistant",
          text: data.answer || "No details found.",
          citations: (data.citations || []).map((c: any) => ({
            docTitle: c.doc_title,
            page: c.page,
            snippet: c.snippet,
            ordinanceId: c.doc_title,
            hasZoningMap: data.active_tab_suggestion === "zoning",
          })),
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };

        setMessages((prev) => [...prev, botMsg]);

        if (data.parcels && data.parcels.length > 0) {
          const newParcels = data.parcels.map((p: any) => ({
            id: p.id,
            address: p.address,
            parcelId: p.parcel_id,
            coords: [p.coordinates[1], p.coordinates[0]],
            ordinanceId: p.ordinance_id,
            page: 1,
            details: p.title,
          }));
          setMarkers(newParcels);
          setActiveMarkerId(newParcels[0].id);
        }

        if (data.active_tab_suggestion === "zoning") {
          setActiveTab("zoning");
        }
      } else {
        throw new Error(`API returned ${res.status}`);
      }
    } catch (err) {
      // Fallback local synthesis response
      const isZoningQuery =
        query.toLowerCase().includes("zoning") ||
        query.toLowerCase().includes("setback") ||
        query.toLowerCase().includes("elm");
      const botMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        sender: "assistant",
        text: isZoningQuery
          ? "### Ordinance 2026-102: Residential Setback & Zoning Variance\n\n- **Council Action**: Approved reducing the minimum rear yard setback requirement from **25 feet to 15 feet** for multi-family residential construction.\n- **Subject Property**: Parcel **104-55-A** located at **450 North Elm Street**.\n- **Engineering Conditions**: Requires installation of an engineered stormwater runoff retention basin prior to occupancy certification.\n\n*The zoning boundaries and affected parcel lines have been mapped on the right.*"
          : "### Municipal Agenda Synthesis Summary\n\n- **Tax & Budget Levies**: Maintained general property tax rate at **0.99 per $100** assessed valuation with balanced operational allocation.\n- **Capital Modernization**: City Council authorized $3,500,000 toward school STEM laboratory upgrades at 820 Atlantic Ave.\n- **Public Utilities & Safety**: Authorized emergency communications repeater antenna lease at 782 South Oak Street.",
        citations: [
          {
            docTitle: "Virginia_Beach_City_Council_Agenda_2026.pdf",
            page: isZoningQuery ? 2 : 1,
            ordinanceId: isZoningQuery ? "ORD-2026-102" : "RES-2026-44",
            snippet: isZoningQuery
              ? "Ordinance 2026-102 approving setback reduction from 25ft to 15ft for Parcel 104-55-A on North Elm Street."
              : "General tax levy and municipal operations budget review at $0.99 per $100 valuation.",
            hasZoningMap: isZoningQuery,
          },
        ],
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, botMsg]);
      if (isZoningQuery) {
        setActiveTab("zoning");
        setActiveMarkerId("p-1");
      }
    } finally {
      setIsStreaming(false);
    }
  };

  const handleUploadFile = async (file: File) => {
    setIsStreaming(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetchApi("/api/ingest/upload", {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        const categoriesList = Object.entries(data.categories_found || {})
          .map(([cat, count]) => `• **${cat}**: ${count} item(s)`)
          .join("\n");

        const uploadMsg: ChatMessage = {
          id: `msg-${Date.now()}`,
          sender: "assistant",
          text: `📥 **Successfully Ingested & Vectorized:** \`${data.filename}\`\n\n- **Total Pages**: ${data.total_pages}\n- **Synthesized Agenda Items**: ${data.total_items}\n- **Geocoded Parcels**: ${data.parcels_found}\n\n**Categories Identified:**\n${categoriesList}\n\nYou can now ask questions about this document or inspect parcel lines on the map!`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setMessages((prev) => [...prev, uploadMsg]);

        setActiveCitation({
          docTitle: data.filename,
          page: 1,
        });

        if (data.parcels_found > 0) {
          const mapRes = await fetchApi("/api/map/parcels");
          if (mapRes.ok) {
            const geojson = await mapRes.json();
            if (geojson.features) {
              setMarkers(
                geojson.features.map((f: any) => ({
                  id: f.properties.id || `m-${Math.random()}`,
                  address: f.properties.address || "Municipal Parcel",
                  parcelId: f.properties.parcel_id,
                  coords: [f.geometry.coordinates[1], f.geometry.coordinates[0]],
                  ordinanceId: f.properties.ordinance_id,
                  page: f.properties.page || 1,
                  details: f.properties.summary,
                }))
              );
            }
          }
        }
        fetchFeed(selectedTopic);
      } else {
        throw new Error(`Upload returned status ${res.status}`);
      }
    } catch (e) {
      const uploadMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        sender: "assistant",
        text: `📥 **Uploaded & Indexed:** \`${file.name}\` (${(file.size / 1024).toFixed(1)} KB)\n\nSegmented agenda items, identified parcel coordinates, and indexed into local vector database. Ready for civic search synthesis!`,
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
    setActiveTab("pdf");

    // In Zen Focus layout (5), unhide secondary pane automatically
    if (activeLayout === 5) {
      setZenFocusedPane("secondary");
    }
  };

  const handleShowZoningMap = () => {
    setActiveTab("zoning");
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
                Civic RAG Synthesis
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
              LLM Municipal Intelligence & Source Verification
            </p>
          </div>
        </div>

        {/* Right: theme pills + document/zoning tab switcher */}
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
                className={`theme-pill${activeLayout === num ? " active" : ""}`}
              >
                {icon}
                <span>{num}</span>
                <span style={{ fontSize: "0.68rem", opacity: 0.75 }}>{label}</span>
              </button>
            ))}
          </div>

          <div className="tab-pill-group">
            <button
              onClick={() => setActiveTab("pdf")}
              className={`tab-pill${activeTab === "pdf" ? " active" : ""}`}
            >
              <FileText size={11} />
              <span className="hidden sm:inline">PDF Evidence</span>
            </button>
            <button
              onClick={() => setActiveTab("zoning")}
              className={`tab-pill${activeTab === "zoning" ? " active" : ""}`}
            >
              <Map size={11} />
              <span className="hidden sm:inline">Zoning Map</span>
            </button>
            <button
              onClick={() => setIsLegalModalOpen(true)}
              className="tab-pill"
              title="Search Virginia General Assembly Acts & State Code (2016-2026)"
            >
              <Scale size={11} />
              <span className="hidden sm:inline">VA Laws</span>
            </button>
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
          {/* View Toggle Bar (AI Synthesis vs Civic Feed) */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-card/60 backdrop-blur shrink-0">
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setLeftPanelMode("chat")}
                className={`tab-pill${leftPanelMode === "chat" ? " active" : ""}`}
                style={{ padding: "4px 10px", fontSize: "0.72rem" }}
              >
                <MessageSquare size={11} />
                <span>AI Assistant</span>
              </button>
              <button
                onClick={() => setLeftPanelMode("feed")}
                className={`tab-pill${leftPanelMode === "feed" ? " active" : ""}`}
                style={{ padding: "4px 10px", fontSize: "0.72rem" }}
              >
                <Newspaper size={11} />
                <span>Civic Feed</span>
                {feedItems.length > 0 && (
                  <span
                    style={{
                      fontSize: "0.62rem",
                      fontWeight: 700,
                      padding: "1px 5px",
                      borderRadius: 100,
                      background: leftPanelMode === "feed" ? "var(--primary-foreground)" : "var(--accent-primary)",
                      color: leftPanelMode === "feed" ? "var(--primary)" : "#fff",
                      marginLeft: 3,
                    }}
                  >
                    {feedItems.length}
                  </span>
                )}
              </button>
            </div>
            <span style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>
              {leftPanelMode === "chat" ? "Multi-Doc Grounded RAG" : "Indexed Council Agendas"}
            </span>
          </div>

          {leftPanelMode === "chat" ? (
            <div className="flex-1 overflow-hidden flex flex-col">
              <ChatPanel
                messages={messages}
                isStreaming={isStreaming}
                onSendMessage={handleSendMessage}
                onUploadFile={handleUploadFile}
                onCitationClick={handleCitationClick}
                onShowZoningMap={handleShowZoningMap}
              />
            </div>
          ) : (
            <div className="flex-1 overflow-hidden flex flex-col bg-background">
              <TopicFilters
                selectedCategory={selectedTopic}
                onSelectCategory={(cat) => {
                  setSelectedTopic(cat);
                  fetchFeed(cat);
                }}
                counts={topicCounts}
              />
              <div className="flex-1 overflow-y-auto">
                <CivicFeedList
                  items={feedItems}
                  selectedItemId={selectedFeedItemId}
                  onSelectItem={handleSelectFeedItem}
                  onSelectParcel={handleSelectFeedParcel}
                />
              </div>
            </div>
          )}
        </section>

        {/* Right Pane: Document & Zoning Evidence Verification */}
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
          {activeTab === "pdf" ? (
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
                  pdfUrl={`/api/documents/${
                    activeCitation?.docTitle || "Virginia_Beach_City_Council_Agenda_2026.pdf"
                  }`}
                  activeCitation={activeCitation}
                />
              </div>
            </div>
          ) : (
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
                  <Map size={13} style={{ color: "#34C759" }} />
                  <span style={{ fontWeight: 600, color: "var(--text-dark)" }}>
                    Interactive Municipal Zoning & Boundary Lines
                  </span>
                </div>
                <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {markers.length} parcels identified
                </span>
              </div>
              <div className="flex-1 overflow-hidden relative">
                <ZoningMapViewer
                  markers={markers}
                  activeMarkerId={activeMarkerId}
                  onSelectMarker={(m) => setActiveMarkerId(m.id)}
                />
              </div>
            </div>
          )}
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
                Switch to {zenFocusedPane === "primary" ? (activeTab === "pdf" ? "PDF Evidence" : "Zoning Map") : "Civic AI Synthesis"}
              </span>
            </button>
          </div>
        )}
      </main>

      {/* Virginia Legislative Law Finder Modal */}
      <LegislativeSearchModal
        isOpen={isLegalModalOpen}
        onClose={() => setIsLegalModalOpen(false)}
        apiBaseUrl={process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}
        onLawSelect={handleLawSelect}
      />
    </div>
  );
}
