import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.schemas import (
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    BatchIngestRequest,
    BatchIngestResponse,
    LegislativeSearchResponse,
    LegislativeSearchResultItem
)
from backend.vector_store import VectorStoreManager
from backend.llm_synthesis import LLMSynthesisService
from backend.legislative_search import VirginiaLegislativeSearcher


vector_store_manager: Optional[VectorStoreManager] = None
llm_synthesis_service: Optional[LLMSynthesisService] = None

def get_vector_store_manager() -> VectorStoreManager:
    if vector_store_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store manager is not initialized"
        )
    return vector_store_manager

def get_llm_synthesis_service() -> LLMSynthesisService:
    global llm_synthesis_service
    if llm_synthesis_service is None:
        llm_synthesis_service = LLMSynthesisService()
    return llm_synthesis_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store_manager, llm_synthesis_service
    db_path = os.getenv("QDRANT_DB_PATH", "./qdrant_db")
    try:
        vector_store_manager = VectorStoreManager(db_path=db_path)
    except Exception as exc:
        print(f"Warning: Could not initialize VectorStoreManager on startup: {exc}")
        vector_store_manager = None
    llm_synthesis_service = LLMSynthesisService()
    yield
    vector_store_manager = None
    llm_synthesis_service = None

app = FastAPI(
    title="CongApp RAG Governance API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "CongApp RAG Governance API is running",
        "docs": "/docs",
        "health": "/api/health"
    }

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

def safe_int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

@app.post("/api/search", response_model=SearchResponse)
def search_documents(request: SearchRequest):
    vsm = get_vector_store_manager()
    synthesis_svc = get_llm_synthesis_service()

    extracted_filters = synthesis_svc.extract_query_filters(request.query)

    filter_dict = {}
    if request.doc_title:
        filter_dict["doc_title"] = request.doc_title
    if request.state_filter or extracted_filters.get("state_filter"):
        filter_dict["state"] = request.state_filter or extracted_filters.get("state_filter")
    if request.date_range or extracted_filters.get("date_range"):
        filter_dict["date_range"] = request.date_range or extracted_filters.get("date_range")

    results_data = vsm.search(
        query=request.query,
        limit=request.limit,
        filter_dict=filter_dict if filter_dict else None
    )

    formatted_results = []
    raw_chunks_for_synthesis = []

    for item in results_data:
        payload = item.get("payload", {})
        meta = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        bbox = meta.get("bbox")
        text_chunk = payload.get("text_chunk", "")
        doc_title = payload.get("doc_title") or meta.get("source_path") or meta.get("doc_title") or "Document"
        page = safe_int(payload.get("page") or meta.get("page"))
        paragraph = safe_int(payload.get("paragraph") or meta.get("paragraph"))

        formatted_results.append(
            SearchResultItem(
                id=str(item.get("id")),
                score=float(item.get("score", 0.0)),
                doc_title=doc_title,
                page=page,
                paragraph=paragraph,
                text_chunk=text_chunk,
                snippet=text_chunk,
                bbox=bbox,
                metadata=meta
            )
        )
        raw_chunks_for_synthesis.append({
            "doc_title": doc_title,
            "page": page,
            "paragraph": paragraph,
            "text_chunk": text_chunk,
            "snippet": text_chunk
        })

    synthesized_answer = None
    llm_provider = None
    citations = None

    if request.enable_synthesis and raw_chunks_for_synthesis:
        try:
            synth_result = synthesis_svc.synthesize(request.query, raw_chunks_for_synthesis)
            synthesized_answer = synth_result.get("synthesized_answer")
            llm_provider = synth_result.get("llm_provider")
            citations = synth_result.get("citations")
        except Exception as exc:
            print(f"Error during LLM synthesis: {exc}")

    return SearchResponse(
        results=formatted_results,
        synthesized_answer=synthesized_answer,
        llm_provider=llm_provider,
        citations=citations
    )



@app.get("/api/documents/{name}")
def get_document(name: str):
    safe_filename = Path(name).name
    pdf_dir = Path("TEMPPDF").resolve()
    file_path = (pdf_dir / safe_filename).resolve()

    try:
        file_path.relative_to(pdf_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{safe_filename}' not found"
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=safe_filename
    )

@app.post("/api/ingest/batch", response_model=BatchIngestResponse)
def batch_ingest(request: BatchIngestRequest):
    vsm = get_vector_store_manager()
    raw_payloads = [chunk.model_dump() for chunk in request.chunks]
    indexed_count = vsm.index_batch_raw(raw_payloads)
    return BatchIngestResponse(
        status="success",
        indexed_count=indexed_count,
        message=f"Indexed {indexed_count} raw chunks into Qdrant"
    )

@app.get("/api/legislative/search", response_model=LegislativeSearchResponse)
def legislative_search(
    query: str = "clean energy",
    state: str = "Virginia",
    years: str = "2016-2026",
    limit: int = 5
):
    start_year, end_year = 2016, 2026
    if "-" in years:
        parts = years.split("-")
        try:
            start_year, end_year = int(parts[0]), int(parts[1])
        except ValueError:
            pass

    searcher = VirginiaLegislativeSearcher(default_state=state, start_year=start_year, end_year=end_year)
    results = searcher.search(query=query, limit=limit)
    
    pdf_dir = Path("TEMPPDF").resolve()
    items = []
    for doc in results:
        searcher.download_pdf(doc, pdf_dir)
        items.append(
            LegislativeSearchResultItem(
                bill_id=doc.bill_id,
                title=doc.title,
                state=doc.state,
                enactment_year=doc.enactment_year,
                summary=doc.summary,
                url=doc.url
            )
        )
    return LegislativeSearchResponse(results=items)

