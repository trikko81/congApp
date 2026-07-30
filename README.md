# OrdinanceRAG

OrdinanceRAG turns static, unsearchable public governance files into an interactive, grounded intelligence engine using Retrieval-Augmented Generation (RAG).

##  System Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│ City Council    │ ──> │ Document Parsing │ ──> │ Vector Embedding  │
│ Dense PDFs      │     │ & Metadata Split │     │ Generation        │
└─────────────────┘     └──────────────────┘     └─────────┬─────────┘
                                                           │
                                                           ▼
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│ Grounded LLM    │ <── │ Similarity Search│ <── │ Vector Database   │
│ Citation Output │     │ (Cosine / HNSW)  │     │ Storage           │
└─────────────────┘     └──────────────────┘     └───────────────────┘
```

##  Proposed Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend Framework** | Next.js (React, TypeScript) | Fast, server-rendered web UI for responsive search and streaming responses. |
| **Styling & UI** | Tailwind CSS + Shadcn UI | Clean, accessible design tailored for civic tech readability. |
| **PDF Rendering** | `react-pdf` / `PDF.js` | Native browser viewer allowing split-screen viewing and PDF text highlighting. |
| **Document Processing** | PyMuPDF (`fitz`) / Unstructured | Layout-aware extraction of text, tables, and page metadata from dense PDFs. |
| **Vector Database** | Qdrant (Local / Dockerized) | High-performance vector store with rich metadata payload filtering. |
| **Embedding Model** | `text-embedding-3-small` / `bge-m3` | Fast, high-dimensional vector representations optimized for retrieval. |
| **LLM Inference** | GPT-4o-mini / Claude 3.5 Sonnet | Cost-effective, instruction-aligned LLMs for factual summarization and citation. |
| **Orchestration** | LangChain / LlamaIndex | Managing retrieval chains, prompt templates, and streaming context pipelines. |

## 🎨 Miro Board Architecture Zones

1. **Zone 1: Problem Definition & User Journey** – Civic pain points & resident Q&A flow.
2. **Zone 2: System Architecture & Data Flow** – Raw PDF ingestion pipe & real-time query retrieval pipe.
3. **Zone 3: Vector Metadata & Schema Layout** – JSON payload schema (`text_chunk`, `source_doc`, `page_number`, `section`).
4. **Zone 4: Low-Fidelity UI Wireframe Mockups** – Split-screen interface (Search & streamed AI answer + embedded PDF viewer sync).
5. **Zone 5: Agile Sprint Roadmap** – Phase 1 to Phase 4 setup.
