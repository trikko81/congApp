"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { ArrowUpRight, CalendarDays, FileText, MapPin, Search, Sparkles } from "lucide-react";
import type { CitationItem } from "@/components/ChatPanel";
import type { LocalImpactResponse } from "@/types/civic";

interface LocalImpactPanelProps {
  onOpenPdf: (citation: CitationItem) => void;
  onAskAboutBill: (query: string) => void;
}

function formatDate(value: string): string {
  const date = new Date(`${value}T12:00:00`);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function LocalImpactPanel({ onOpenPdf, onAskAboutBill }: LocalImpactPanelProps) {
  const [location, setLocation] = useState("Virginia Beach");
  const [data, setData] = useState<LocalImpactResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const requestedLocation = location.trim();
    if (!requestedLocation) return;

    setLoading(true);
    setError(null);
    setData(null);
    try {
      const response = await fetch(
        `/api/impact/latest?location=${encodeURIComponent(requestedLocation)}`
      );
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || `Search failed (${response.status})`);
      }
      setData(payload as LocalImpactResponse);
      setLocation(payload.location || requestedLocation);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not search local bills.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="flex-1 overflow-y-auto bg-background p-4 sm:p-6" aria-labelledby="local-impact-title">
      <div className="mx-auto max-w-2xl space-y-5">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
            <MapPin size={13} /> Your place, in plain language
          </div>
          <h2 id="local-impact-title" className="text-xl font-semibold text-foreground">
            Your Local Impact
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Find recently enacted Virginia bills that explicitly mention your city or locality.
          </p>
        </div>

        <form onSubmit={search} className="flex flex-col gap-2 rounded-xl border border-border bg-card p-3 sm:flex-row">
          <label className="sr-only" htmlFor="local-impact-location">City or locality in Virginia</label>
          <div className="flex min-w-0 flex-1 items-center gap-2 px-2">
            <MapPin size={15} className="shrink-0 text-muted-foreground" />
            <input
              id="local-impact-location"
              value={location}
              onChange={(event) => setLocation(event.target.value)}
              placeholder="For example, Virginia Beach"
              maxLength={100}
              className="min-w-0 flex-1 bg-transparent py-2 text-sm text-foreground outline-none placeholder:text-muted-foreground"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !location.trim()}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:cursor-wait disabled:opacity-60"
          >
            <Search size={14} /> {loading ? "Searching…" : "Find recent bills"}
          </button>
        </form>

        {error && <p role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</p>}

        {data && (
          <div className="space-y-3" aria-live="polite">
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
              <span>Latest bills that mention <strong className="text-foreground">{data.location}</strong></span>
              {data.dataset_as_of && <span>Data through {formatDate(data.dataset_as_of)}</span>}
            </div>

            {data.matches.length === 0 ? (
              <div className="rounded-xl border border-border bg-card p-5">
                <h3 className="font-semibold text-foreground">No direct locality mention found</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  The current handoff has no enacted bill that explicitly names {data.location}. Statewide
                  laws may still apply. Try asking the assistant about a topic that matters to you.
                </p>
              </div>
            ) : data.matches.map((bill) => (
              <article key={`${bill.bill_id}-${bill.chapter_id}`} className="rounded-xl border border-border bg-card p-4 shadow-sm sm:p-5">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-[11px] font-semibold text-emerald-700 dark:text-emerald-300">
                    <MapPin size={11} /> Locality mentioned
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                    <CalendarDays size={13} /> Enacted {formatDate(bill.approved_date)}
                  </span>
                </div>

                <div className="text-xs font-semibold text-primary">
                  {bill.bill_id} <span className="text-muted-foreground">·</span> {bill.chapter_id}
                </div>
                <h3 className="mt-1 text-base font-semibold leading-snug text-foreground">{bill.title}</h3>
                <p className="mt-3 rounded-lg bg-muted/60 p-3 text-sm leading-relaxed text-foreground/85">
                  “{bill.excerpt}”
                </p>
                <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                  The bill text names this locality. That is a useful lead, but the cited provision determines
                  who is actually covered.
                </p>

                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => onOpenPdf({
                      docTitle: bill.doc_title,
                      page: bill.page,
                      snippet: bill.excerpt,
                      ordinanceId: bill.bill_id,
                      chapterId: bill.chapter_id,
                    })}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3.5 py-2.5 text-[0.8125rem] font-semibold text-foreground transition hover:bg-muted"
                  >
                    <FileText size={13} /> Open cited PDF page {bill.page}
                  </button>
                  <button
                    type="button"
                    onClick={() => onAskAboutBill(
                      `For someone in ${data.location}, explain what Virginia ${bill.bill_id} (${bill.chapter_id}) changes, who is covered, and when it takes effect. Use only the enacted text and cite the PDF page. Distinguish a direct local provision from a general Virginia rule.`
                    )}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-primary/10 px-3.5 py-2.5 text-[0.8125rem] font-semibold text-primary transition hover:bg-primary/15"
                  >
                    <Sparkles size={13} /> What does this mean for me?
                    <ArrowUpRight size={12} />
                  </button>
                </div>
              </article>
            ))}

            <p className="text-xs leading-relaxed text-muted-foreground">
              {data.coverage_status === "partial"
                ? `Coverage is partial: ${data.skipped_count} source records were skipped. `
                : ""}
              This section finds explicit locality mentions in the available 2026 Virginia handoff; it does not
              identify every statewide law that could affect residents.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
