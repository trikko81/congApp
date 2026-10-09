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

export interface ParcelMarker {
  id: string;
  address: string;
  parcelId?: string;
  coords: [number, number];
  ordinanceId?: string;
  page?: number;
  details?: string;
}

export interface GeoJsonParcelFeature {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number];
  };
  properties: {
    id?: string;
    address?: string;
    parcel_id?: string;
    ordinance_id?: string;
    page?: number;
    summary?: string;
  };
}

export interface FeedResponse {
  entries: Array<{
    item_id: string;
    title: string;
    municipality?: string;
    date?: string;
    category: TopicCategory;
    summary_bullets?: string[];
    ordinance_id?: string;
    page_start: number;
    page_end?: number;
    doc_title: string;
    locations?: ParcelLocation[];
  }>;
}

export interface ParcelFeatureCollection {
  features: GeoJsonParcelFeature[];
}

export interface ChatApiResponse {
  answer: string;
  citations: Array<{
    doc_title?: string;
    page?: number;
    paragraph?: number;
    snippet?: string;
    ordinance_id?: string;
    chapter_id?: string;
    source_url?: string;
  }>;
  parcels: Array<{
    id: string;
    address: string;
    parcel_id?: string;
    ordinance_id?: string;
    coordinates: [number, number];
    title?: string;
  }>;
  active_tab_suggestion?: "pdf" | "zoning";
}

export interface UploadApiResponse {
  filename: string;
  total_pages: number;
  total_items: number;
  categories_found: Record<string, number>;
  parcels_found: number;
}

export interface LocalImpactBill {
  bill_id: string;
  title: string;
  chapter_id: string;
  approved_date: string;
  doc_title: string;
  page: number;
  source_url: string;
  excerpt: string;
}

export interface LocalImpactResponse {
  location: string;
  dataset_as_of?: string | null;
  coverage_status: string;
  skipped_count: number;
  match_scope: "explicit_locality_mention";
  matches: LocalImpactBill[];
}
