import os
import re
import uuid
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, Any, List, Dict
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, status, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.schemas import (
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    BatchIngestRequest,
    BatchIngestResponse,
    LegislativeSearchResponse,
    LegislativeSearchResultItem,
    TopicCategory,
    ParcelLocation,
    AgendaItem,
    CivicFeedEntry,
    FeedResponse,
    UploadResponse,
    ChatRequest,
    ChatResponse,
    LocalImpactResponse
)
from backend.vector_store import VectorStoreManager
from backend.local_impact import find_latest_local_bills
from backend.llm_synthesis import LLMSynthesisService
from backend.legislative_search import VirginiaLegislativeSearcher
from backend.agenda_parser import AgendaParser
from backend.geo_service import GeoService
from backend.topic_classifier import TopicClassifier


vector_store_manager: Optional[VectorStoreManager] = None
llm_synthesis_service: Optional[LLMSynthesisService] = None
geo_service: GeoService = GeoService()
agenda_parser: AgendaParser = AgendaParser()
topic_classifier: TopicClassifier = TopicClassifier()

# In-memory feed registry populated with baseline municipal actions & dynamic uploads
civic_feed_registry: List[CivicFeedEntry] = []

def _initialize_seed_feed():
    global civic_feed_registry
    if civic_feed_registry:
        return

    seed_items = [
        AgendaItem(
            item_id="item-seed-1",
            doc_title="Virginia_Beach_Ordinance_2026_Data_Center_Moratorium.pdf",
            title="Ordinance 2026-102: Residential Setback & Zoning Variance",
            full_text=(
                "AN ORDINANCE TO AMEND COMPREHENSIVE ZONING CODE SECTION 4.\n"
                "Approved application for a residential variance for Parcel 104-55-A located at "
                "450 North Elm Street to reduce minimum rear yard setback requirement from 25 feet to 15 feet. "
                "Conditions: Installation of engineered stormwater runoff retention basin prior to occupancy permit."
            ),
            category=TopicCategory.ZONING_LAND_USE,
            ordinance_id="ORD-2026-102",
            page_start=4,
            page_end=4,
            summary_bullets=[
                "Approved reducing minimum rear yard setback requirement from 25 feet to 15 feet for multi-family construction.",
                "Affects Parcel 104-55-A at 450 North Elm Street.",
                "Requires installation of engineered stormwater runoff basin before occupancy."
            ],
            locations=[
                ParcelLocation(raw_match="450 North Elm Street", address="450 North Elm Street", confidence=0.98),
                ParcelLocation(raw_match="Parcel 104-55-A", parcel_id="104-55-A", confidence=0.95)
            ]
        ),
        AgendaItem(
            item_id="item-seed-2",
            doc_title="Virginia_Beach_Ordinance_2026_Data_Center_Moratorium.pdf",
            title="Resolution 2026-44: Annual Real Property Tax Levy",
            full_text=(
                "RESOLUTION ADOPTING FISCAL YEAR 2026-2027 BUDGET.\n"
                "The City Council establishes the real estate tax rate at $0.99 per $100 of assessed valuation. "
                "Dedicated 0.45 mills toward school division capital fund and public infrastructure bonds."
            ),
            category=TopicCategory.TAXES_BUDGET,
            ordinance_id="RES-2026-44",
            page_start=1,
            page_end=2,
            summary_bullets=[
                "Maintained general real estate property tax rate at $0.99 per $100 assessed valuation.",
                "Appropriated municipal operations and capital improvement fund for FY 2026-2027."
            ],
            locations=[]
        ),
        AgendaItem(
            item_id="item-seed-3",
            doc_title="Virginia_Beach_Ordinance_2026_Data_Center_Moratorium.pdf",
            title="Action Item 5: High School Science Facility Capital Modernization",
            full_text=(
                "SCHOOL BOARD ACTION ITEM: Authorized $3,500,000 in bond proceeds for modernization "
                "of STEM science labs at Central High School, located at 820 Atlantic Avenue."
            ),
            category=TopicCategory.EDUCATION_SCHOOLS,
            ordinance_id="RES-2026-61",
            page_start=3,
            page_end=3,
            summary_bullets=[
                "Allocated $3,500,000 in bond proceeds for STEM laboratory renovation.",
                "Site improvements at 820 Atlantic Avenue campus."
            ],
            locations=[
                ParcelLocation(raw_match="820 Atlantic Avenue", address="820 Atlantic Avenue", confidence=0.92)
            ]
        ),
        AgendaItem(
            item_id="item-seed-4",
            doc_title="Virginia_Beach_Ordinance_2026_Data_Center_Moratorium.pdf",
            title="Resolution 2026-78: Emergency Radio Repeater Lease Agreement",
            full_text=(
                "PUBLIC SAFETY AUTHORIZATION: Authorized City Manager to execute a facility lease at "
                "782 South Oak Street for installation of digital emergency dispatch repeaters."
            ),
            category=TopicCategory.PUBLIC_SAFETY,
            ordinance_id="RES-2026-78",
            page_start=5,
            page_end=5,
            summary_bullets=[
                "Authorized lease at 782 South Oak Street for emergency communications repeater.",
                "Improves first-responder radio coverage across western municipal districts."
            ],
            locations=[
                ParcelLocation(raw_match="782 South Oak Street", address="782 South Oak Street", confidence=0.94)
            ]
        )
    ]

    for item in seed_items:
        resolved_locs = [geo_service.resolve_location(loc) for loc in item.locations]
        entry = CivicFeedEntry(
            item_id=item.item_id,
            doc_title=item.doc_title,
            municipality="Virginia Beach",
            date="2026-05-12",
            title=item.title,
            category=item.category,
            summary_bullets=item.summary_bullets,
            ordinance_id=item.ordinance_id,
            page_start=item.page_start,
            locations=resolved_locs
        )
        civic_feed_registry.append(entry)

_initialize_seed_feed()

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
    _initialize_seed_feed()
    yield
    vector_store_manager = None
    llm_synthesis_service = None

app = FastAPI(
    title="TownWatch Civic Intelligence API",
    version="2.0.0",
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
def root() -> Dict[str, Any]:
    return {
        "app": "TownWatch Civic Intelligence API",
        "version": "2.0.0",
        "endpoints": {
            "feed": "/api/feed",
            "map_parcels": "/api/map/parcels",
            "search": "/api/search",
            "chat": "/api/chat",
            "upload": "/api/ingest/upload",
            "health": "/api/health"
        }
    }

@app.get("/api/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/impact/latest", response_model=LocalImpactResponse)
def latest_local_impact(
    location: str = Query(..., min_length=3, max_length=100, description="Virginia city or locality"),
) -> LocalImpactResponse:
    try:
        return LocalImpactResponse(**find_latest_local_bills(location))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The Virginia enacted-laws handoff is not available to the backend.",
        ) from exc

def safe_int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

@app.get("/api/feed", response_model=FeedResponse)
def get_feed(
    topic: Optional[str] = Query(default=None, description="Topic Category filter"),
    municipality: Optional[str] = Query(default=None, description="Municipality name"),
    has_parcels: Optional[bool] = Query(default=None, description="Filter items with GIS parcels"),
    limit: int = Query(default=50, ge=1, le=100)
) -> FeedResponse:
    filtered = civic_feed_registry
    if topic and topic.strip() and topic.lower() != "all":
        topic_clean = topic.strip().lower()
        filtered = [
            e for e in filtered
            if e.category.value.lower() == topic_clean or topic_clean in e.category.value.lower()
        ]

    if municipality and municipality.strip():
        filtered = [e for e in filtered if municipality.lower() in e.municipality.lower()]

    if has_parcels is not None:
        if has_parcels:
            filtered = [e for e in filtered if len(e.locations) > 0]
        else:
            filtered = [e for e in filtered if len(e.locations) == 0]

    return FeedResponse(
        entries=filtered[:limit],
        total=len(filtered)
    )

@app.get("/api/map/parcels")
def get_map_parcels(
    municipality: Optional[str] = Query(default=None),
    topic: Optional[str] = Query(default=None)
) -> Dict[str, Any]:
    items_to_map: List[AgendaItem] = []
    for entry in civic_feed_registry:
        if topic and topic.strip() and topic.lower() != "all":
            if entry.category.value.lower() != topic.strip().lower() and topic.strip().lower() not in entry.category.value.lower():
                continue
        if municipality and municipality.strip():
            if municipality.lower() not in entry.municipality.lower():
                continue
        if entry.locations:
            items_to_map.append(
                AgendaItem(
                    item_id=entry.item_id,
                    doc_title=entry.doc_title,
                    title=entry.title,
                    full_text=" • ".join(entry.summary_bullets),
                    summary_bullets=entry.summary_bullets,
                    category=entry.category,
                    ordinance_id=entry.ordinance_id,
                    page_start=entry.page_start,
                    locations=entry.locations
                )
            )

    return geo_service.items_to_geojson(items_to_map, municipality=municipality)

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    query = request.query
    query_lower = query.lower()
    is_zoning = any(w in query_lower for w in ["zoning", "variance", "setback", "parcel", "elm", "land use", "subdivision"])
    bill_match = re.search(r"\b(HB|SB)\s*[-#]?\s*(\d+)\b", query, re.IGNORECASE)
    bill_filter = {"bill_id": f"{bill_match.group(1).upper()}{bill_match.group(2)}"} if bill_match else None

    vsm = vector_store_manager
    synthesis_svc = get_llm_synthesis_service()

    raw_chunks = []
    citations = []

    if vsm:
        try:
            results_data = vsm.search(query=query, limit=8, filter_dict=bill_filter)
            for item in results_data:
                payload = item.get("payload", {})
                meta = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
                text_chunk = payload.get("text_chunk", "")
                doc_title = payload.get("doc_title") or meta.get("source_path") or meta.get("doc_title") or "Document"
                page = safe_int(payload.get("page") or meta.get("page"), default=1)
                paragraph = safe_int(payload.get("paragraph") or meta.get("paragraph"), default=1)

                raw_chunks.append({
                    "doc_title": doc_title,
                    "page": page,
                    "paragraph": paragraph,
                    "text_chunk": text_chunk,
                    "snippet": text_chunk,
                    "ordinance_id": payload.get("bill_id") or payload.get("ordinance_id"),
                    "chapter_id": payload.get("chapter_id"),
                    "source_url": payload.get("source_url")
                })
        except Exception as e:
            print(f"Notice: Vector search in chat: {e}")

    # Fallback to feed registry chunks if vector store has no matches
    if not raw_chunks:
        for entry in civic_feed_registry:
            bullets_text = "\n".join(entry.summary_bullets) if entry.summary_bullets else entry.title
            snippet_text = f"{entry.title}: {' '.join(entry.summary_bullets)}" if entry.summary_bullets else entry.title

            matches_query = any(word in entry.title.lower() or any(word in b.lower() for b in entry.summary_bullets)
                                for word in query_lower.split() if len(word) > 3)

            if is_zoning and (entry.category == TopicCategory.ZONING_LAND_USE or matches_query):
                raw_chunks.append({
                    "doc_title": entry.doc_title,
                    "page": entry.page_start,
                    "paragraph": 1,
                    "text_chunk": f"{entry.title}\n{bullets_text}",
                    "snippet": snippet_text
                })
            elif not is_zoning and (matches_query or any(term in entry.title.lower() or term in entry.category.value.lower() for term in ["tax", "school", "safety", "budget"])):
                raw_chunks.append({
                    "doc_title": entry.doc_title,
                    "page": entry.page_start,
                    "paragraph": 1,
                    "text_chunk": f"{entry.title}\n{bullets_text}",
                    "snippet": snippet_text
                })
            if len(raw_chunks) >= 4:
                break

    synth = synthesis_svc.synthesize(query, raw_chunks)
    answer = synth.get("synthesized_answer", "")
    citations = synth.get("citations", [])

    matched_parcels = []
    for entry in civic_feed_registry:
        should_include_parcels = is_zoning and entry.category == TopicCategory.ZONING_LAND_USE
        if not should_include_parcels:
            for loc in entry.locations:
                key_text = (loc.address or loc.parcel_id or loc.raw_match).lower()
                if any(w in query_lower for w in key_text.split() if len(w) > 3):
                    should_include_parcels = True
                    break

        if should_include_parcels:
            for loc in entry.locations:
                resolved = geo_service.resolve_location(loc)
                matched_parcels.append({
                    "id": f"{entry.item_id}-{resolved.parcel_id or 'loc'}",
                    "title": entry.title,
                    "address": resolved.address or resolved.raw_match,
                    "parcel_id": resolved.parcel_id,
                    "ordinance_id": entry.ordinance_id,
                    "coordinates": [resolved.longitude, resolved.latitude]
                })

    return ChatResponse(
        answer=answer,
        citations=citations,
        parcels=matched_parcels,
        active_tab_suggestion="zoning" if is_zoning else "pdf"
    )

@app.post("/api/ingest/upload", response_model=UploadResponse)
async def upload_pdf_agenda(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a PDF document."
        )

    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded file exceeds maximum allowed size of 50 MB."
        )

    pdf_dir = Path("TEMPPDF").resolve()
    pdf_dir.mkdir(parents=True, exist_ok=True)
    raw_name = os.path.basename(file.filename)
    safe_filename = re.sub(r'[^\w\-\.\s]', '_', raw_name)
    if not safe_filename.lower().endswith(".pdf"):
        safe_filename += ".pdf"
    target_path = pdf_dir / safe_filename

    with open(target_path, "wb") as f:
        f.write(content)

    # Segment agenda items using layout-aware AgendaParser
    try:
        agenda_items = agenda_parser.parse_pdf_agenda(target_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse municipal agenda PDF: {exc}"
        )

    sample_text = " ".join(item.full_text for item in agenda_items[:3]) if agenda_items else ""
    detected_muni = agenda_parser.detect_municipality(sample_text, filename=safe_filename)
    detected_date = agenda_parser.detect_meeting_date(sample_text) or "2026-05-12"

    categories_count: Dict[str, int] = {}
    parcels_found = 0
    new_entries: List[CivicFeedEntry] = []
    chunks_for_qdrant = []

    for item in agenda_items:
        cat_str = item.category.value
        categories_count[cat_str] = categories_count.get(cat_str, 0) + 1
        parcels_found += len(item.locations)

        resolved_locs = [geo_service.resolve_location(loc) for loc in item.locations]
        entry = CivicFeedEntry(
            item_id=item.item_id,
            doc_title=safe_filename,
            municipality=detected_muni,
            date=detected_date,
            title=item.title,
            category=item.category,
            summary_bullets=item.summary_bullets,
            ordinance_id=item.ordinance_id,
            page_start=item.page_start,
            locations=resolved_locs
        )
        new_entries.append(entry)
        civic_feed_registry.insert(0, entry) # Prepend newest to feed

        # Prepare for vector indexing
        chunks_for_qdrant.append({
            "doc_title": safe_filename,
            "text_chunk": item.title + "\n" + item.full_text,
            "page": item.page_start,
            "paragraph": 1,
            "section": item.category.value,
            "ordinance_id": item.ordinance_id,
            "summary_bullets": item.summary_bullets
        })

    # Index into local Qdrant if available
    if vector_store_manager and chunks_for_qdrant:
        try:
            vector_store_manager.index_batch_raw(chunks_for_qdrant)
        except Exception as exc:
            print(f"Warning: indexing uploaded chunks to Qdrant: {exc}")

    # Determine total pages
    total_pages = 1
    try:
        import pymupdf
        with pymupdf.open(target_path) as doc:
            total_pages = len(doc)
    except Exception:
        pass

    return UploadResponse(
        status="success",
        filename=safe_filename,
        total_pages=total_pages,
        total_items=len(agenda_items),
        categories_found=categories_count,
        parcels_found=parcels_found,
        entries=new_entries
    )

@app.post("/api/search", response_model=SearchResponse)
def search_documents(request: SearchRequest) -> SearchResponse:
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
        meta = dict(payload.get("metadata")) if isinstance(payload.get("metadata"), dict) else {}
        for key in ("bill_id", "chapter_id", "session_code", "source_url", "date", "state", "ordinance_id", "chunk_id"):
            if payload.get(key) is not None:
                meta.setdefault(key, payload[key])
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

@app.get("/api/documents/{name:path}")
def get_document(name: str) -> FileResponse:
    import urllib.parse
    import re
    import httpx
    import pymupdf

    decoded_name = urllib.parse.unquote(name).strip()
    clean_base = os.path.basename(decoded_name)
    clean_base = re.sub(r'^(?:documents\/|\/)', '', clean_base)
    if clean_base.lower().endswith(".pdf"):
        clean_base = clean_base[:-4]
    clean_base = clean_base.strip()
    if not clean_base:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document path"
        )
    safe_filename = re.sub(r'[^\w\-\.\s]', '_', clean_base) + ".pdf"

    project_root = Path(__file__).resolve().parent.parent
    pdf_dir = (project_root / "TEMPPDF").resolve()
    pdf_dir.mkdir(parents=True, exist_ok=True)
    file_path = (pdf_dir / safe_filename).resolve()

    try:
        file_path.relative_to(pdf_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document path"
        )

    enacted_pdf_dir = Path(
        os.getenv("VIRGINIA_ENACTED_PDF_DIR", str(project_root / "virginia_2026_handoff" / "pdfs"))
    ).resolve()
    enacted_file_path = (enacted_pdf_dir / safe_filename).resolve()
    try:
        enacted_file_path.relative_to(enacted_pdf_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document path"
        )

    # Prefer the source PDF from the enacted-laws handoff so a citation opens
    # the real, paginated chapter document rather than a generated placeholder.
    if enacted_file_path.is_file() and enacted_file_path.stat().st_size > 100:
        return FileResponse(
            path=enacted_file_path,
            media_type="application/pdf",
            filename=safe_filename
        )

    # If already cached and valid, return immediately
    if file_path.exists() and file_path.is_file() and file_path.stat().st_size > 100:
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            filename=safe_filename
        )

    # 1. Search Qdrant vector database or legislative records for metadata & full text
    matched_text = None
    online_url = None
    bill_id = None
    chapter_info = "General Assembly Act"

    if vector_store_manager:
        try:
            results = vector_store_manager.search(clean_base, limit=3)
            for r in results:
                payload = r.get("payload", {})
                doc_title = payload.get("doc_title", "")
                if clean_base.lower() in doc_title.lower() or doc_title.lower() in clean_base.lower():
                    online_url = payload.get("url")
                    bill_id = payload.get("ordinance_id")
                    chapter_info = payload.get("section", "Acts of Assembly")
                    matched_text = (
                        f"COMMONWEALTH OF VIRGINIA LEGISLATION\n\n"
                        f"Bill ID: {bill_id or 'Enacted Act'} | {chapter_info}\n"
                        f"Title: {doc_title}\n"
                        f"Date: {payload.get('date', 'Recent')}\n\n"
                        f"Statutory Text & Enactment:\n{payload.get('text_chunk')}"
                    )
                    break
        except Exception as e:
            print(f"Notice: Vector search lookup during document fetch: {e}")

    # If not found in vector store, check if it matches recognized bill/act syntax
    is_legislative_query = bool(re.search(r'\b(?:hb|sb|act|chapter|virginia|ordinance|bill|\d{3,4})\b', clean_base, re.I))
    
    if not matched_text and not is_legislative_query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{safe_filename}' not found"
        )

    if not matched_text:
        matched_text = f"COMMONWEALTH OF VIRGINIA GENERAL ASSEMBLY ACT\n\nTitle: {clean_base}\n\nOfficial statutory record approved by the General Assembly of Virginia."

    # 2. Try online LIS fetch if URL available
    downloaded = False
    if online_url:
        try:
            with httpx.Client(timeout=8.0, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True, verify=False) as client:
                resp = client.get(online_url)
                if resp.status_code == 200:
                    if resp.content.startswith(b"%PDF"):
                        file_path.write_bytes(resp.content)
                        downloaded = True
                    elif len(resp.text) > 100:
                        scraped = re.sub(r'<[^>]+>', ' ', resp.text)
                        scraped = re.sub(r'\s+', ' ', scraped).strip()
                        if len(scraped) > 100:
                            matched_text = f"COMMONWEALTH OF VIRGINIA OFFICIAL LEGISLATIVE RECORD (LIS)\nSource: {online_url}\n\n{scraped[:4500]}"
        except Exception as e:
            print(f"Notice: Online LIS fetch for {online_url}: {e}")

    # 3. If remote binary wasn't direct PDF, construct standard PyMuPDF canvas
    if not downloaded:
        with pymupdf.open() as doc_pdf:
            page = doc_pdf.new_page(width=612, height=792)

            page.draw_rect(pymupdf.Rect(40, 40, 572, 70), color=(0.2, 0.3, 0.4), fill=(0.93, 0.95, 0.98))
            page.insert_textbox(
                pymupdf.Rect(50, 46, 560, 66),
                f"COMMONWEALTH OF VIRGINIA • LEGISLATIVE INFORMATION SYSTEM",
                fontsize=9,
                fontname="helv",
                color=(0.3, 0.4, 0.5)
            )
            
            page.insert_textbox(
                pymupdf.Rect(50, 80, 562, 740),
                matched_text,
                fontsize=10,
                fontname="helv",
                color=(0.1, 0.1, 0.1)
            )
            doc_pdf.save(str(file_path))

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=safe_filename
    )

@app.post("/api/ingest/batch", response_model=BatchIngestResponse)
def batch_ingest(request: BatchIngestRequest) -> BatchIngestResponse:
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
) -> LegislativeSearchResponse:
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
