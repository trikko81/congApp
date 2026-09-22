export type TopicCategory =
  | "All"
  | "Taxes & Budget"
  | "Zoning & Land Use"
  | "Education & School Board"
  | "Public Safety & Infrastructure"
  | "Parks & Environment"
  | "General Governance & Administration";

export interface ParcelLocation {
  raw_match: string;
  address?: string;
  parcel_id?: string;
  latitude?: number;
  longitude?: number;
  confidence: number;
}

export interface CivicFeedItem {
  id: string;
  title: string;
  municipality: string;
  date?: string;
  category: TopicCategory;
  summary_bullets: string[];
  ordinance_id?: string;
  page_start: number;
  page_end?: number;
  doc_title: string;
  locations: ParcelLocation[];
}
