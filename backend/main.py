import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.schemas import SearchRequest, SearchResponse, SearchResultItem
from backend.vector_store import VectorStoreManager

vector_store_manager: Optional[VectorStoreManager] = None

def get_vector_store_manager() -> VectorStoreManager:
    if vector_store_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store manager is not initialized"
        )
    return vector_store_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store_manager
    db_path = os.getenv("QDRANT_DB_PATH", "./qdrant_db")
    try:
        vector_store_manager = VectorStoreManager(db_path=db_path)
    except Exception as exc:
        print(f"Warning: Could not initialize VectorStoreManager on startup: {exc}")
        vector_store_manager = None
    yield
    vector_store_manager = None

app = FastAPI(
    title="CongApp RAG Governance API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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

@app.post("/api/search", response_model=SearchResponse)
def search_documents(request: SearchRequest):
    vsm = get_vector_store_manager()
    
    filter_dict = {}
    if request.doc_title:
        filter_dict["doc_title"] = request.doc_title

    results_data = vsm.search(
        query=request.query,
        limit=request.limit,
        filter_dict=filter_dict if filter_dict else None
    )

    formatted_results = []
    for item in results_data:
        payload = item.get("payload", {})
        meta = payload.get("metadata", {})
        bbox = meta.get("bbox") if isinstance(meta, dict) else None

        formatted_results.append(
            SearchResultItem(
                id=str(item.get("id")),
                score=float(item.get("score", 0.0)),
                doc_title=payload.get("doc_title", ""),
                page=int(payload.get("page", 0)),
                paragraph=int(payload.get("paragraph", 0)),
                text_chunk=payload.get("text_chunk", ""),
                snippet=payload.get("text_chunk", ""),
                bbox=bbox,
                metadata=meta if isinstance(meta, dict) else {}
            )
        )

    return SearchResponse(results=formatted_results)

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
