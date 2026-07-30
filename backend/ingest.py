"""
Ingestion Pipeline for OrdinanceRAG.
Finds all PDFs in TEMPPDF directory, parses them into chunks, and indexes them in Qdrant.
"""

import os
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["HF_HUB_DISABLE_SSL_VERIFICATION"] = "1"

from pathlib import Path
from backend.parser import PDFParser
from backend.vector_store import VectorStoreManager
import time

def main():
    project_root = Path(__file__).resolve().parent.parent
    pdf_dir = project_root / "TEMPPDF"
    
    if not pdf_dir.exists():
        print(f"Directory not found: {pdf_dir}")
        return

    # Initialize parser and vector store
    # Note: For persistence, we use the local qdrant_db folder
    db_path = project_root / "qdrant_db"
    print(f"Using Qdrant DB at: {db_path}")
    vsm = VectorStoreManager(db_path=str(db_path))
    parser = PDFParser(chunk_size_tokens=500, overlap_tokens=50)

    total_chunks_indexed = 0
    start_time = time.time()

    # Process all PDFs in the directory
    for pdf_file in pdf_dir.glob("*.pdf"):
        print(f"\n--- Processing {pdf_file.name} ---")
        try:
            # Parse the PDF into DocumentChunks
            chunks = parser.parse_pdf(pdf_file)
            print(f"Extracted {len(chunks)} chunks.")
            
            if chunks:
                # Index into Qdrant
                vsm.index_chunks(chunks)
                total_chunks_indexed += len(chunks)
                
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")

    elapsed = time.time() - start_time
    print(f"\n=========================================")
    print(f"Ingestion Complete! Indexed {total_chunks_indexed} total chunks in {elapsed:.2f} seconds.")
    print(f"=========================================")

    # Test a semantic search query
    test_query = "clean air act renewable biomass"
    print(f"\nTesting Semantic Search for: '{test_query}'")
    results = vsm.search(test_query, limit=3)
    
    for i, res in enumerate(results):
        print(f"\nResult {i+1} (Score: {res['score']:.4f})")
        print(f"Source: {res['payload'].get('doc_title')} - Page {res['payload'].get('page')}, ¶{res['payload'].get('paragraph')}")
        text = res['payload'].get('text_chunk', '')
        print(f"Snippet: {text[:150]}...")

if __name__ == "__main__":
    main()
