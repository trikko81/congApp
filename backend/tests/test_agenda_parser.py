import pytest
from backend.agenda_parser import AgendaParser
from backend.schemas import TopicCategory

def test_segment_agenda_items_from_text():
    parser = AgendaParser()
    sample_text = """
    TOWNSHIP COUNCIL REGULAR MEETING AGENDA - JULY 15, 2026
    
    ITEM 1: CALL TO ORDER & ROLL CALL
    The meeting was called to order at 7:00 PM.
    
    ITEM 2: CONSENT AGENDA
    Resolution 2026-45: Approval of prior meeting minutes and routine vendor payments.
    
    PUBLIC HEARING: ORDINANCE NO. 2026-102
    An Ordinance amending Chapter 140 (Zoning) regarding setback requirements on parcel 104-55-A at 450 North Elm St.
    
    ITEM 4: BOARD OF EDUCATION BUDGET AMENDMENT
    Discussion and vote on the 2026-2027 school district capital improvement tax millage rate.
    """
    items = parser.segment_text(sample_text, doc_title="Township_Meeting_July2026.pdf")
    
    assert len(items) >= 3
    titles = [item.title for item in items]
    assert any("ORDINANCE NO. 2026-102" in t or "Zoning" in t or "ITEM 2" in t for t in titles)
    
    # Check that ordinance/resolution IDs are parsed
    ord_items = [item for item in items if item.ordinance_id]
    assert len(ord_items) >= 1
    assert any("2026-102" in str(item.ordinance_id) or "2026-45" in str(item.ordinance_id) for item in ord_items)

def test_agenda_item_locations_integration():
    parser = AgendaParser()
    sample_text = """
    ITEM 5: PUBLIC HEARING - ZONING VARIANCE
    Motion to approve residential variance for 782 South Oak Street, Tax Map Parcel 88-12-004.
    """
    items = parser.segment_text(sample_text, doc_title="Zoning_Board_Meeting.pdf")
    assert len(items) == 1
    assert len(items[0].locations) >= 1
    assert any("782 South Oak" in str(loc.address) for loc in items[0].locations if loc.address)

def test_detect_municipality():
    parser = AgendaParser()
    assert parser.detect_municipality("City Council of Richmond Regular Session", "Richmond_Agenda.pdf") == "Richmond"
    assert parser.detect_municipality("Township meeting notes", "Fairfax_Board.pdf") == "Fairfax"
    assert parser.detect_municipality("Norfolk city hall session", "notes.pdf") == "Norfolk"

def test_detect_meeting_date():
    parser = AgendaParser()
    assert parser.detect_meeting_date("CITY COUNCIL MEETING - MAY 12, 2026") == "MAY 12, 2026"
    assert parser.detect_meeting_date("Minutes from 2026-07-15 regular session") == "2026-07-15"
    assert parser.detect_meeting_date("Meeting without date") is None

