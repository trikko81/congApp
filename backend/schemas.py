from typing import List, Dict, Any, Optional
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

