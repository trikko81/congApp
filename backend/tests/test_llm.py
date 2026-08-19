import pytest
from unittest.mock import patch, MagicMock
from backend.llm_synthesis import LLMSynthesisService

def test_extract_query_filters_virginia_and_recency():
    service = LLMSynthesisService()
    filters = service.extract_query_filters("Find ordinances passed in Virginia in the past week")
    assert filters.get("state_filter") == "Virginia"
    assert filters.get("date_range") == "past_week"

def test_extract_query_filters_none():
    service = LLMSynthesisService()
    filters = service.extract_query_filters("What are the zoning regulations?")
    assert filters.get("state_filter") is None
    assert filters.get("date_range") is None

def test_build_citations():
    service = LLMSynthesisService()
    chunks = [
        {
            "doc_title": "Virginia_Clean_Air_Act.pdf",
            "page": 2,
            "paragraph": 5,
            "snippet": "Emission reduction standards for industrial facilities."
        }
    ]
    citations = service.build_citations(chunks)
    assert len(citations) == 1
    assert citations[0]["doc_title"] == "Virginia_Clean_Air_Act.pdf"
    assert "Virginia_Clean_Air_Act.pdf" in citations[0]["citation_label"]
    assert "p. 2" in citations[0]["citation_label"]

def test_fallback_synthesis():
    service = LLMSynthesisService(provider="fallback")
    chunks = [
        {
            "doc_title": "S5087_Clean_Air_Act.pdf",
            "page": 1,
            "paragraph": 2,
            "snippet": "This section requires clean energy biomass."
        }
    ]
    result = service.synthesize("What does the act say about biomass?", chunks)
    assert "synthesized_answer" in result
    assert "citations" in result
    assert result["llm_provider"] == "fallback"
    assert len(result["citations"]) == 1
    assert "Based on the analysis of legislative documents for" not in result["synthesized_answer"]
    assert "Click any citation badge below" not in result["synthesized_answer"]
    assert "• According to [S5087_Clean_Air_Act" in result["synthesized_answer"]

def test_deepseek_synthesis_mock():
    service = LLMSynthesisService(provider="deepseek", api_key="sk-test-deepseek")
    chunks = [
        {
            "doc_title": "Virginia_Air_Act.pdf",
            "page": 3,
            "paragraph": 1,
            "snippet": "Virginia clean air rules."
        }
    ]
    with patch("backend.llm_synthesis.LLMSynthesisService._call_deepseek") as mock_call:
        mock_call.return_value = "According to Virginia_Air_Act.pdf [p. 3, par. 1], clean air rules apply."
        result = service.synthesize("What are Virginia rules?", chunks)
        assert "clean air rules apply" in result["synthesized_answer"]
        assert result["llm_provider"] == "deepseek"

def test_gemini_synthesis_mock():
    service = LLMSynthesisService(provider="gemini", api_key="AIzaSyTestKey")
    chunks = [
        {
            "doc_title": "Water_Pollution_Act.pdf",
            "page": 5,
            "paragraph": 2,
            "snippet": "Discharge standards for municipal waterways."
        }
    ]
    with patch("backend.llm_synthesis.LLMSynthesisService._call_gemini") as mock_call:
        mock_call.return_value = "Based on Water_Pollution_Act.pdf [p. 5, par. 2], discharge standards apply."
        result = service.synthesize("What are discharge standards?", chunks)
        assert "discharge standards apply" in result["synthesized_answer"]
        assert result["llm_provider"] == "gemini"

