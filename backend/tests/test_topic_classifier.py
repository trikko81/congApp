import pytest
from backend.schemas import TopicCategory
from backend.topic_classifier import TopicClassifier, ClassificationResult

def test_classify_zoning_land_use():
    classifier = TopicClassifier()
    text = """
    ORDINANCE NO. 2026-102
    AN ORDINANCE TO AMEND THE COMPREHENSIVE ZONING CODE
    The City Council hereby approves the application for a residential variance for parcel 104-55-A
    located at 450 North Elm Street to reduce the rear yard setback from 25 feet to 15 feet.
    Special use permit granted subject to standard stormwater runoff retention conditions.
    """
    result = classifier.classify_and_summarize(text)
    assert result.category == TopicCategory.ZONING_LAND_USE
    assert result.confidence >= 0.7
    assert len(result.summary_bullets) >= 1
    assert any("setback" in b.lower() or "variance" in b.lower() or "elm" in b.lower() for b in result.summary_bullets)

def test_classify_taxes_and_budget():
    classifier = TopicClassifier()
    text = """
    RESOLUTION NO. 2026-44: ANNUAL TAX LEVY AND GENERAL FUND APPROPRIATION
    A resolution adopting the fiscal year 2026-2027 municipal budget. The real property tax rate
    is set at $0.99 per $100 of assessed valuation. Total appropriations equal $45,200,000 for city operations.
    """
    result = classifier.classify_and_summarize(text)
    assert result.category == TopicCategory.TAXES_BUDGET
    assert result.confidence >= 0.7
    assert len(result.summary_bullets) >= 1
    assert any("tax" in b.lower() or "budget" in b.lower() or "0.99" in b for b in result.summary_bullets)

def test_classify_education_schools():
    classifier = TopicClassifier()
    text = """
    SCHOOL BOARD ACTION ITEM 4.2: CAPITAL IMPROVEMENT PLAN FOR HIGH SCHOOL
    Motion to approve allocation of $3,500,000 in local bond proceeds to modernize STEM laboratory facilities
    at Central High School. Superintendent recommended approval based on enrollment projections.
    """
    result = classifier.classify_and_summarize(text)
    assert result.category == TopicCategory.EDUCATION_SCHOOLS
    assert result.confidence >= 0.7
    assert len(result.summary_bullets) >= 1

def test_classify_public_safety():
    classifier = TopicClassifier()
    text = """
    ITEM 7: POLICE DEPARTMENT RADIO COMMUNICATIONS UPGRADE
    Authorization for the City Manager to execute a purchase agreement with Motorola Solutions
    for tactical emergency radio repeaters for the Police Department and Fire Rescue operations.
    """
    result = classifier.classify_and_summarize(text)
    assert result.category == TopicCategory.PUBLIC_SAFETY
    assert result.confidence >= 0.7

def test_classify_parks_environment():
    classifier = TopicClassifier()
    text = """
    RESOLUTION 2026-19: URBAN CANOPY AND MUNICIPAL PARK RESTORATION
    Approval of grant funding for tree planting along the riverwalk and trail expansion in Riverside Park.
    Environmental sustainability task force presented recommendations.
    """
    result = classifier.classify_and_summarize(text)
    assert result.category == TopicCategory.PARKS_REC_ENVIRONMENT
    assert result.confidence >= 0.7

def test_neutral_bullets_filtering():
    classifier = TopicClassifier()
    text = """
    WHEREAS, the City of Hopewell has determined a need for street lighting; and
    WHEREAS, public notices were duly published according to law;
    NOW, THEREFORE, BE IT ORDAINED by the Council of the City of Hopewell that $50,000 is authorized
    for installation of LED luminaires along Commerce Avenue.
    """
    result = classifier.classify_and_summarize(text)
    # Ensure "WHEREAS" and "NOW, THEREFORE" legalese is stripped out of summary bullets
    for bullet in result.summary_bullets:
        assert not bullet.strip().startswith("WHEREAS")
        assert not bullet.strip().startswith("NOW, THEREFORE")
