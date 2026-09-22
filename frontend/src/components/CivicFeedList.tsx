"use client";

import React from "react";
import { CivicFeedItem } from "@/types/civic";
import { MapPin, FileText, ExternalLink, Calendar, Building2 } from "lucide-react";

interface CivicFeedListProps {
  items: CivicFeedItem[];
  selectedItemId?: string;
  onSelectItem: (item: CivicFeedItem) => void;
  onSelectParcel?: (item: CivicFeedItem, parcelIndex: number) => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  "Taxes & Budget": "bg-amber-500/10 text-amber-600 border-amber-500/20 dark:text-amber-400",
  "Zoning & Land Use": "bg-emerald-500/10 text-emerald-600 border-emerald-500/20 dark:text-emerald-400",
  "Education & School Board": "bg-blue-500/10 text-blue-600 border-blue-500/20 dark:text-blue-400",
  "Public Safety & Infrastructure": "bg-rose-500/10 text-rose-600 border-rose-500/20 dark:text-rose-400",
  "Parks & Environment": "bg-teal-500/10 text-teal-600 border-teal-500/20 dark:text-teal-400",
  "General Governance & Administration": "bg-slate-500/10 text-slate-600 border-slate-500/20 dark:text-slate-400",
};

export default function CivicFeedList({
  items,
  selectedItemId,
  onSelectItem,
  onSelectParcel,
}: CivicFeedListProps) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center text-muted-foreground">
        <FileText size={36} className="mb-2 opacity-40" />
        <p className="font-medium">No municipal items found in this category.</p>
        <p className="text-xs mt-1">Upload an agenda packet or select &quot;All&quot; to see all items.</p>
      </div>
    );
  }

  return (
    <div className="civic-feed-list space-y-3.5 p-4 overflow-y-auto max-h-[calc(100vh-180px)]">
      {items.map((item) => {
        const isSelected = selectedItemId === item.id;
        const colorClass = CATEGORY_COLORS[item.category] || CATEGORY_COLORS["General Governance & Administration"];

        return (
          <div
            key={item.id}
            onClick={() => onSelectItem(item)}
            className={`feed-card rounded-xl border p-4 transition-all duration-150 cursor-pointer shadow-sm ${
              isSelected
                ? "border-primary bg-primary/5 ring-1 ring-primary shadow-md"
                : "border-border bg-card hover:border-border/80 hover:shadow"
            }`}
          >
            {/* Header: Category Badge & Ordinance ID */}
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${colorClass}`}>
                {item.category}
              </span>
              {item.ordinance_id && (
                <span className="text-[11px] font-mono font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded">
                  {item.ordinance_id}
                </span>
              )}
            </div>

            {/* Title */}
            <h3 className="font-semibold text-sm text-foreground mb-2 leading-snug">
              {item.title}
            </h3>

            {/* Neutral Bullet Points */}
            {item.summary_bullets && item.summary_bullets.length > 0 && (
              <ul className="space-y-1 mb-3 text-xs text-muted-foreground list-disc list-inside">
                {item.summary_bullets.map((bullet, idx) => (
                  <li key={idx} className="leading-relaxed">
                    <span className="text-foreground/90">{bullet}</span>
                  </li>
                ))}
              </ul>
            )}

            {/* Parcel Locations / Addresses Tag */}
            {item.locations && item.locations.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 mb-3 pt-1 border-t border-border/50">
                {item.locations.map((loc, lIdx) => (
                  <button
                    key={lIdx}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectItem(item);
                      if (onSelectParcel) onSelectParcel(item, lIdx);
                    }}
                    className="inline-flex items-center gap-1 text-[11px] font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 px-2 py-0.5 rounded hover:bg-emerald-500/20 transition cursor-pointer"
                  >
                    <MapPin size={11} className="text-emerald-500" />
                    <span>{loc.address || loc.parcel_id || loc.raw_match}</span>
                  </button>
                ))}
              </div>
            )}

            {/* Footer: Metadata & Grounded Citation */}
            <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-2 border-t border-border/40">
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-1">
                  <Building2 size={12} />
                  {item.municipality}
                </span>
                {item.date && (
                  <span className="inline-flex items-center gap-1">
                    <Calendar size={12} />
                    {item.date}
                  </span>
                )}
              </div>

              <div className="inline-flex items-center gap-1 text-primary font-medium hover:underline text-[11px]">
                <FileText size={11} />
                <span>Page {item.page_start}</span>
                <ExternalLink size={10} />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
