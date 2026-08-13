# Google Colab PDF Processing & Virginia Legislative Law Search Pipeline

## TL;DR
Build a high-performance Google Colab cloud processing pipeline (`notebooks/colab_ingest_pipeline.ipynb`) leveraging free GPU/TPU/CPU resources to fetch, parse, embed, and index Virginia legislative PDFs (laws, bills, acts of assembly enacted in Virginia from 2016–2026), coupled with a Virginia-specific legislative search service (`backend/legislative_search.py`) and batch ingestion endpoint (`/api/ingest/batch`) to search and ingest Virginia state laws into CongApp's vector database.

## Objective
Enable users to:
1. Search and discover brand new and historic Virginia legislative laws, bills, and enactments spanning the past 10 years (2016–2026).
2. Run batch PDF processing on Google Colab free compute runtimes for heavy extraction and embedding.
3. Automatically sync the resulting Qdrant vectors and metadata back into the local `congApp` backend (`qdrant_db`) with full search and citation support filtered by Virginia jurisdiction and date range.

## Non-goals
- Scraping non-Virginia state legislatures during this test phase.
- Replacing Qdrant as the vector database engine.
- Requiring paid cloud infrastructure (must run on free-tier Colab and local backend).

## Discovery
- `backend/parser.py`: PDF parser using `PyMuPDF` with page and paragraph metadata extraction.
- `backend/vector_store.py`: Qdrant client using `fastembed` (`BAAI/bge-small-en-v1.5`, 384 dim).
- `backend/main.py`: FastAPI server serving search queries (`/api/search`) supporting `state_filter` and `date_range`.
- `backend/schemas.py`: Search request/response models supporting `state_filter`, `date_range`, and document metadata.

## Decisions
- **Target Jurisdiction**: Virginia (LIS / Virginia General Assembly laws & bills, 2016–2026).
- **Colab Notebook Format**: Store a stand-alone Jupyter Notebook `notebooks/colab_ingest_pipeline.ipynb` that users can upload to Google Colab or open directly via GitHub link.
- **Batch Export Format**: Colab script exports processed vectors and payloads as a portable JSON payload package (`ingested_chunks.json`) or direct HTTP push to `/api/ingest/batch`.
- **Virginia Legislative Search Module**: Implement `backend/legislative_search.py` configured with default filters for `state="Virginia"` and `start_year=2016`.
- **State & Legislative Metadata**: Standardize metadata fields (`doc_type: legislative_law`, `state: Virginia`, `bill_id`, `enactment_year`, `source_url`).

## TODOs

- [x] Task 1: Virginia Legislative Law Search & PDF Fetcher Module (2016–2026)
- [x] Task 2: Backend Batch Ingestion Endpoint & Virginia Metadata Schema Extension
- [x] Task 3: Google Colab Processing Notebook & Script Pipeline for Virginia Laws
- [x] Task 4: Frontend UI Virginia Legislative Search & Ingestion Integration
- [x] Final Verification Wave

Next: `start-work google-colab-pdf-ingest-and-legislative-search`
