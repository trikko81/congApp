"use client";

import { useEffect, useRef, useState } from "react";

interface LegislativeLawItem {
  bill_id: string;
  title: string;
  state: string;
  enactment_year: number;
  summary: string;
  url: string;
}

interface LegislativeSearchResponse {
  results: LegislativeLawItem[];
}


interface LegislativeSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  apiBaseUrl: string;
  onLawSelect?: (docTitle: string) => void;
}

export default function LegislativeSearchModal({
  isOpen,
  onClose,
  apiBaseUrl,
  onLawSelect,
}: LegislativeSearchModalProps) {
  const [query, setQuery] = useState("clean energy");
  const [stateFilter, setStateFilter] = useState("Virginia");
  const [yearRange, setYearRange] = useState("2016-2026");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<LegislativeLawItem[]>([]);
  const [statusMsg, setStatusMsg] = useState("");
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
    );
    focusable?.[0]?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key === "Tab" && focusable?.length) {
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      previousFocus?.focus();
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSearch = async () => {
    setLoading(true);
    setStatusMsg("");
    setResults([]);
    try {
      const url = `${apiBaseUrl}/api/legislative/search?query=${encodeURIComponent(
        query
      )}&state=${encodeURIComponent(stateFilter)}&years=${encodeURIComponent(
        yearRange
      )}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: LegislativeSearchResponse = await res.json();
      setResults(data.results || []);
      if ((data.results || []).length === 0) {
        setStatusMsg("No Virginia legislative laws found matching criteria.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatusMsg(`Search failed: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(4px)",
        zIndex: 999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1rem",
        overflowY: "auto",
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="legislative-search-title"
        style={{
          background: "#1e293b",
          border: "1px solid rgba(255, 255, 255, 0.15)",
          borderRadius: "12px",
          width: "100%",
          maxWidth: "720px",
          color: "#f8fafc",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
          overflow: "hidden",
          maxHeight: "calc(100dvh - 2rem)",
          overflowY: "auto",
        }}
      >
        <div
          style={{
            padding: "1.25rem 1.5rem",
            borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <h2 id="legislative-search-title" style={{ margin: 0, fontSize: "1.25rem", fontWeight: 600 }}>
              Virginia Legislative Law Finder (2016–2026)
            </h2>
            <p style={{ margin: "4px 0 0 0", fontSize: "0.85rem", color: "#94a3b8" }}>
              Fetch state laws & Google Colab free batch processing pipeline
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close legislative search"
            style={{
              background: "transparent",
              border: "none",
              color: "#94a3b8",
              fontSize: "1.5rem",
              cursor: "pointer",
            }}
          >
            ×
          </button>
        </div>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            void handleSearch();
          }}
          style={{ padding: "1rem" }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "10px", marginBottom: "1rem" }}>
            <div>
              <label htmlFor="legislative-query" style={{ display: "block", fontSize: "0.75rem", color: "#94a3b8", marginBottom: "4px" }}>
                Topic / Keyword
              </label>
              <input
                id="legislative-query"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. clean energy, zoning"
                style={{
                  width: "100%",
                  padding: "0.6rem 0.8rem",
                  background: "#0f172a",
                  border: "1px solid #334155",
                  borderRadius: "6px",
                  color: "#f8fafc",
                }}
              />
            </div>

            <div>
              <label htmlFor="legislative-state" style={{ display: "block", fontSize: "0.75rem", color: "#94a3b8", marginBottom: "4px" }}>
                Jurisdiction
              </label>
              <select
                id="legislative-state"
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
                style={{
                  width: "100%",
                  padding: "0.6rem 0.8rem",
                  background: "#0f172a",
                  border: "1px solid #334155",
                  borderRadius: "6px",
                  color: "#f8fafc",
                }}
              >
                <option value="Virginia">Virginia (Default)</option>
              </select>
            </div>

            <div>
              <label htmlFor="legislative-years" style={{ display: "block", fontSize: "0.75rem", color: "#94a3b8", marginBottom: "4px" }}>
                Session Year
              </label>
              <select
                id="legislative-years"
                value={yearRange}
                onChange={(e) => setYearRange(e.target.value)}
                style={{
                  width: "100%",
                  padding: "0.6rem 0.8rem",
                  background: "#0f172a",
                  border: "1px solid #334155",
                  borderRadius: "6px",
                  color: "#f8fafc",
                }}
              >
                <option value="2016-2026">All 10 Years (2016–2026)</option>
                <option value="2026-2026">2026 Regular Session</option>
                <option value="2025-2025">2025 Regular Session</option>
                <option value="2024-2024">2024 Regular Session</option>
                <option value="2023-2023">2023 Regular Session</option>
                <option value="2022-2022">2022 Regular Session</option>
                <option value="2021-2021">2021 Regular Session</option>
                <option value="2020-2020">2020 Regular Session</option>
                <option value="2019-2019">2019 Regular Session</option>
                <option value="2018-2018">2018 Regular Session</option>
                <option value="2017-2017">2017 Regular Session</option>
                <option value="2016-2016">2016 Regular Session</option>
              </select>
            </div>
          </div>


          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "0.75rem",
              background: "#3b82f6",
              color: "#ffffff",
              border: "none",
              borderRadius: "6px",
              fontWeight: 600,
              cursor: "pointer",
              marginBottom: "1rem",
            }}
          >
            {loading ? "Searching Virginia Legislation..." : "Search Enacted Virginia Laws"}
          </button>

          {statusMsg && (
            <p role="status" style={{ color: "#cbd5e1", fontSize: "0.85rem", margin: "0 0 1rem 0" }}>{statusMsg}</p>
          )}

          <div style={{ maxHeight: "240px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "8px" }}>
            {results.map((item) => {
              const filename = `Virginia_${item.bill_id}_${item.enactment_year}.pdf`;
              return (
                <div
                  key={item.bill_id}
                  style={{
                    padding: "0.85rem",
                    background: "#0f172a",
                    border: "1px solid #334155",
                    borderRadius: "6px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      <span
                        style={{
                          background: "#1e3a8a",
                          color: "#93c5fd",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          fontSize: "0.75rem",
                          fontWeight: 600,
                        }}
                      >
                        {item.bill_id} ({item.enactment_year})
                      </span>
                      <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>{item.title}</span>
                    </div>
                    <p style={{ margin: "4px 0 0 0", fontSize: "0.8rem", color: "#94a3b8" }}>{item.summary}</p>
                  </div>

                  <button
                    type="button"
                    onClick={() => {
                      if (onLawSelect) onLawSelect(filename);
                      onClose();
                    }}
                    style={{
                      background: "#10b981",
                      color: "#ffffff",
                      border: "none",
                      padding: "0.4rem 0.8rem",
                      borderRadius: "4px",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                    }}
                  >
                    View PDF
                  </button>
                </div>
              );
            })}
          </div>
        </form>
      </div>
    </div>
  );
}
