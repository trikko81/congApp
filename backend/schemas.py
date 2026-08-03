from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class SearchRequest(BaseModel):
    query: str = Field(..., description="Query string for vector similarity search")
    limit: int = Field(default=5, ge=1, le=50, description="Top-k number of results to return")
    doc_title: Optional[str] = Field(default=None, description="Optional document title filter")

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
