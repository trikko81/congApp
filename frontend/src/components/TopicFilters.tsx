"use client";

import React from "react";
import { TopicCategory } from "@/types/civic";
import { Layers, Landmark, Home, GraduationCap, ShieldAlert, Trees, FileText } from "lucide-react";

interface TopicFiltersProps {
  selectedCategory: TopicCategory;
  onSelectCategory: (cat: TopicCategory) => void;
  counts?: Record<string, number>;
}

const CATEGORIES: { label: TopicCategory; icon: React.ReactNode }[] = [
  { label: "All", icon: <Layers size={14} /> },
  { label: "Taxes & Budget", icon: <Landmark size={14} /> },
  { label: "Zoning & Land Use", icon: <Home size={14} /> },
  { label: "Education & School Board", icon: <GraduationCap size={14} /> },
  { label: "Public Safety & Infrastructure", icon: <ShieldAlert size={14} /> },
  { label: "Parks & Environment", icon: <Trees size={14} /> },
  { label: "General Governance & Administration", icon: <FileText size={14} /> },
];

export default function TopicFilters({
  selectedCategory,
  onSelectCategory,
  counts = {},
}: TopicFiltersProps) {
  return (
    <div className="topic-filter-bar flex items-center gap-2 overflow-x-auto py-2.5 px-4 border-b border-border bg-card/60 backdrop-blur">
      {CATEGORIES.map(({ label, icon }) => {
        const isSelected = selectedCategory === label;
        const count = counts[label] ?? (label === "All" ? Object.values(counts).reduce((a, b) => a + b, 0) : 0);

        return (
          <button
            key={label}
            onClick={() => onSelectCategory(label)}
            className={`topic-pill inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-150 whitespace-nowrap cursor-pointer ${
              isSelected
                ? "bg-primary text-primary-foreground shadow-sm scale-105 font-semibold"
                : "bg-muted/70 text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            {icon}
            <span>{label}</span>
            {count > 0 && (
              <span
                className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] ${
                  isSelected ? "bg-primary-foreground/20 text-primary-foreground" : "bg-border text-muted-foreground"
                }`}
              >
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
