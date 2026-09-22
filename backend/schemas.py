from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field

class SearchRequest(BaseModel):
    query: str = Field(..., description="Query string for vector similarity search")
    limit: int = Field(default=5, ge=1, le=50, description="Top-k number of results to return")
    doc_title: Optional[str] = Field(default=None, description="Optional document title filter")
    enable_synthesis: bool = Field(default=True, description="Whether to generate LLM synthesized answer")
    state_filter: Optional[str] = Field(default=None, description="Optional state/location filter e.g. Virginia")
    date_range: Optional[str] = Field(default=None, description="Optional date range filter e.g. past week")

class SearchResultItem(BaseModel):
    id: str
    score: float
    doc_title: str
    page: int
    paragraph: int
    text_chunk: str
    snippet: str
    bbox: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SearchResponse(BaseModel):
    results: List[SearchResultItem]
    synthesized_answer: Optional[str] = Field(default=None, description="Conversational answer synthesized from search results")
    llm_provider: Optional[str] = Field(default=None, description="LLM provider used for synthesis")
    citations: Optional[List[Dict[str, Any]]] = Field(default=None, description="Grounded citations referenced in answer")

class BatchChunkPayload(BaseModel):
    doc_title: str
    text_chunk: str
    page: int = Field(default=1)
    paragraph: int = Field(default=1)
    section: Optional[str] = Field(default=None)
    ordinance_id: Optional[str] = Field(default=None)
    date: Optional[str] = Field(default=None)
    state: Optional[str] = Field(default="Virginia")
    vector: Optional[List[float]] = Field(default=None)

class BatchIngestRequest(BaseModel):
    chunks: List[BatchChunkPayload]

class BatchIngestResponse(BaseModel):
    status: str
    indexed_count: int
    message: str

class LegislativeSearchResultItem(BaseModel):
    bill_id: str
    title: str
    state: str
    enactment_year: int
    summary: str
    url: str

class LegislativeSearchResponse(BaseModel):
    results: List[LegislativeSearchResultItem]


class TopicCategory(str, Enum):
    TAXES_BUDGET = "Taxes & Budget"
    ZONING_LAND_USE = "Zoning & Land Use"
    EDUCATION_SCHOOLS = "Education & School Board"
    PUBLIC_SAFETY = "Public Safety & Infrastructure"
    PARKS_REC_ENVIRONMENT = "Parks & Environment"
    GENERAL_ADMIN = "General Governance & Administration"

class ParcelLocation(BaseModel):
    raw_match: str
    address: Optional[str] = None
    parcel_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    confidence: float = Field(default=1.0)

class AgendaItem(BaseModel):
    item_id: str
    doc_title: str
    title: str
    full_text: str
    summary_bullets: List[str] = Field(default_factory=list)
    category: TopicCategory = Field(default=TopicCategory.GENERAL_ADMIN)
    ordinance_id: Optional[str] = None
    page_start: int = Field(default=1)
    page_end: int = Field(default=1)
    locations: List[ParcelLocation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CivicFeedEntry(BaseModel):
    item_id: str
    doc_title: str
    municipality: str = Field(default="Virginia Beach")
    date: Optional[str] = None
    title: str
    category: TopicCategory
    summary_bullets: List[str]
    ordinance_id: Optional[str] = None
    page_start: int
    locations: List[ParcelLocation] = Field(default_factory=list)
    geojson_feature: Optional[Dict[str, Any]] = None

class FeedResponse(BaseModel):
    entries: List[CivicFeedEntry]
    total: int

class UploadResponse(BaseModel):
    status: str
    filename: str
    total_pages: int
    total_items: int
    categories_found: Dict[str, int]
    parcels_found: int
    entries: List[CivicFeedEntry]

class ChatRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, str]]] = Field(default=None)
    municipality: Optional[str] = Field(default=None)

class ChatResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    parcels: List[Dict[str, Any]] = Field(default_factory=list)
    active_tab_suggestion: str = Field(default="pdf")
