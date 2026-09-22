import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add workspace to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agenda_parser import AgendaParser
from backend.geo_service import GeoService
from backend.topic_classifier import TopicClassifier
from backend.vector_store import VectorStoreManager
from backend.schemas import TopicCategory

def run_evaluation():
    print("==================================================")
    print("  TownWatch Evaluation & Precision Benchmark")
    print("==================================================")

    agenda_path = Path("TEMPPDF/sample_agendas/Virginia_Beach_City_Council_Agenda_2026.pdf")
    if not agenda_path.exists():
        print(f"Error: Evaluation file not found at {agenda_path}")
        sys.exit(1)

    parser = AgendaParser()
    geo_service = GeoService()
    classifier = TopicClassifier()

    start_time = time.time()
    items = parser.parse_pdf_agenda(agenda_path)
    parse_time = time.time() - start_time

    # 1. Segmentation Evaluation
    expected_count = 7
    segmentation_recall = len(items) / expected_count if expected_count else 1.0
    print(f"\n[1] SEGMENTATION RECALL")
    print(f"    Expected items: {expected_count} | Detected items: {len(items)}")
    print(f"    Recall: {segmentation_recall * 100:.1f}% | Parse latency: {parse_time * 1000:.1f}ms")

    # 2. Topic Classification Evaluation
    # Ground truth mapping for the 7 items in Virginia Beach agenda
    ground_truth_categories = [
        TopicCategory.GENERAL_ADMIN,
        TopicCategory.ZONING_LAND_USE,
        TopicCategory.TAXES_BUDGET,
        TopicCategory.ZONING_LAND_USE,
        TopicCategory.EDUCATION_SCHOOLS,
        TopicCategory.PUBLIC_SAFETY,
        TopicCategory.PARKS_REC_ENVIRONMENT,
    ]

    correct_classifications = 0
    print(f"\n[2] TOPIC CLASSIFICATION ACCURACY")
    for idx, (item, expected_cat) in enumerate(zip(items, ground_truth_categories), 1):
        is_match = item.category == expected_cat
        if is_match:
            correct_classifications += 1
        print(f"    Item {idx}: '{item.title[:45]}...'")
        print(f"       Expected: {expected_cat.value}")
        print(f"       Detected: {item.category.value} [{'PASS' if is_match else 'FAIL'}]")

    accuracy = correct_classifications / len(ground_truth_categories) if ground_truth_categories else 0
    print(f"    Classification Accuracy: {accuracy * 100:.1f}% ({correct_classifications}/{len(ground_truth_categories)})")

    # 3. Geographic Parcel / Address Recall
    expected_parcels_or_streets = [
        "450 North Elm Street",
        "104-55-A",
        "1250 Pacific Avenue",
        "820 Atlantic Avenue",
        "782 South Oak Street",
        "500 Commerce Avenue"
    ]

    detected_locations_all = []
    for item in items:
        for loc in item.locations:
            detected_locations_all.append(loc.address or loc.parcel_id or loc.raw_match)

    matched_parcels = 0
    for exp in expected_parcels_or_streets:
        found = any(exp.lower() in d.lower() for d in detected_locations_all)
        if found:
            matched_parcels += 1

    geo_recall = matched_parcels / len(expected_parcels_or_streets)
    print(f"\n[3] GEOGRAPHIC PARCEL & ADDRESS EXTRACTION")
    print(f"    Expected addresses/parcels: {len(expected_parcels_or_streets)}")
    print(f"    Matched: {matched_parcels}")
    print(f"    Recall: {geo_recall * 100:.1f}%")

    # 4. Qdrant Retrieval Relevance
    print(f"\n[4] QDRANT SEMANTIC RETRIEVAL GROUNDEDNESS")
    vsm = VectorStoreManager(db_path="./qdrant_db")
    test_queries = [
        ("residential setback variance on Elm Street", "2026-102"),
        ("school board STEM laboratory modernization", "Atlantic"),
        ("property tax levy and assessed valuation rate", "0.99"),
    ]

    retrieval_hits = 0
    for q, exp_keyword in test_queries:
        results = vsm.search(query=q, limit=3)
        hit = any(exp_keyword.lower() in (r["payload"].get("text_chunk", "").lower()) for r in results)
        if hit:
            retrieval_hits += 1
        print(f"    Query: '{q}' -> Top-3 hit matched keyword '{exp_keyword}': {'YES' if hit else 'NO'}")

    retrieval_acc = retrieval_hits / len(test_queries)
    print(f"    Top-3 Retrieval Accuracy: {retrieval_acc * 100:.1f}%")

    # Overall Summary
    print("\n==================================================")
    print("  EVALUATION SUMMARY & QUALITY GATE")
    print("==================================================")
    print(f"  Segmentation Recall:       {segmentation_recall * 100:.1f}%")
    print(f"  Topic Accuracy:            {accuracy * 100:.1f}%")
    print(f"  Geo Parcel Recall:         {geo_recall * 100:.1f}%")
    print(f"  Qdrant Retrieval Acc:      {retrieval_acc * 100:.1f}%")
    
    passed = segmentation_recall >= 0.85 and accuracy >= 0.85 and geo_recall >= 0.80 and retrieval_acc >= 0.66
    print(f"  OVERALL RESULT:            {'PASS' if passed else 'FAIL'}")
    print("==================================================\n")

    if not passed:
        sys.exit(1)

if __name__ == "__main__":
    run_evaluation()
