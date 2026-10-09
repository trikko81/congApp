"use client";

import React from "react";
import { CivicFeedItem } from "@/types/civic";
import { MapPin, FileText, ExternalLink, Calendar, Building2 } from "lucide-react";

interface CivicFeedListProps {
  items: CivicFeedItem[];
  selectedItemId?: string;
  onSelectItem: (item: CivicFeedItem) => void;
}

export default function CivicFeedList({
  items,
  selectedItemId,
  onSelectItem,
}: CivicFeedListProps) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center text-muted-foreground">
        <FileText size={36} className="mb-2 opacity-40" />
        <p className="font-medium">No municipal items found in this category.</p>
        <p className="mt-2 max-w-sm text-sm leading-relaxed">Upload an agenda packet or select &quot;All&quot; to see all items.</p>
      </div>
    );
  }

  return (
    <div className="civic-feed-list mx-auto w-full max-w-4xl space-y-4 p-4 sm:p-6">
      {items.map((item) => {
        const isSelected = selectedItemId === item.id;

        return (
          <div
            key={item.id}
            onClick={() => onSelectItem(item)}
            onKeyDown={(event) => {
              if (event.target !== event.currentTarget) return;
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelectItem(item);
              }
            }}
            role="button"
            tabIndex={0}
            aria-pressed={isSelected}
            className={`feed-card rounded-2xl border p-5 transition-all duration-150 cursor-pointer shadow-sm sm:p-6 ${
              isSelected
                ? "border-primary bg-primary/5 ring-1 ring-primary shadow-md"
                : "border-border bg-card hover:border-border/80 hover:shadow"
            }`}
          >
            {/* Header: Category Badge & Ordinance ID */}
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="feed-category-badge inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border">
                {item.category}
              </span>
              {item.ordinance_id && (
                <span className="text-xs font-mono font-medium text-muted-foreground bg-muted px-2.5 py-1 rounded-md">
                  {item.ordinance_id}
                </span>
              )}
            </div>

            {/* Title */}
            <h3 className="font-semibold text-base sm:text-[1.0625rem] text-foreground mb-3 leading-snug">
              {item.title}
            </h3>

            {/* Neutral Bullet Points */}
            {item.summary_bullets && item.summary_bullets.length > 0 && (
              <ul className="space-y-2 mb-4 text-sm text-muted-foreground leading-6">
                {item.summary_bullets.map((bullet, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <span aria-hidden="true" className="mt-[0.6rem] h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground/70" />
                    <span className="min-w-0 text-foreground/90">{bullet}</span>
                  </li>
                ))}
              </ul>
            )}

            {/* Parcel Locations / Addresses Tag */}
            {item.locations && item.locations.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 mb-4 pt-3 border-t border-border/50">
                {item.locations.map((loc, lIdx) => (
                  <button
                    key={lIdx}
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectItem(item);
                    }}
                    className="inline-flex items-center gap-1.5 text-xs font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 px-2.5 py-1 rounded-md hover:bg-emerald-500/20 transition cursor-pointer"
                  >
                    <MapPin size={11} className="text-emerald-500" />
                    <span>{loc.address || loc.parcel_id || loc.raw_match}</span>
                  </button>
                ))}
              </div>
            )}

            {/* Footer: Metadata & Grounded Citation */}
            <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 text-xs text-muted-foreground pt-3 border-t border-border/40">
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
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

              <div className="inline-flex items-center gap-1.5 text-primary font-medium hover:underline">
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
