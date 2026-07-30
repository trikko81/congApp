# OrdinanceRAG Architectural Overview

## 1. Document Chunk Payload Schema

Each text chunk ingested into Qdrant follows this payload structure to guarantee 100% citation traceability:

```json
{
  "vector": [0.012, -0.043, 0.812, "..."],
  "payload": {
    "text_chunk": "Motion to approve residential zoning variance for Main St...",
    "source_doc": "Council_Meeting_July2026.pdf",
    "page_number": 42,
    "section": "Zoning & Planning Committee",
    "paragraph": 3,
    "ordinance_id": "ORD-2026-88",
    "date": "2026-05-12"
  }
}
```

## 2. Cosine Similarity Formula

Similarity measurement used for vector retrieval against embedded queries:

$$\text{Similarity}(\mathbf{q}, \mathbf{d}) = \frac{\mathbf{q} \cdot \mathbf{d}}{\Vert{}\mathbf{q}\Vert{} \Vert{}\mathbf{d}\Vert{}}$$

## 3. Sprint Roadmap

- **Phase 1 (Data Prep)**: Setup PDF parser (`PyMuPDF`) & test metadata chunking strategies.
- **Phase 2 (Core Vector Engine)**: Local `Qdrant` instance setup + embedding pipeline (`text-embedding-3-small` / `bge-m3`).
- **Phase 3 (Frontend & Viewer)**: Next.js interface with `react-pdf` context highlighting.
- **Phase 4 (Evaluation)**: Benchmark retrieval accuracy on sample city council docs.
