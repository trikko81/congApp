import pytest
from datetime import datetime, timedelta
from backend.legislative_search import VirginiaLegislativeSearcher
from notebooks.virginia_crawler import VirginiaLISCrawler

def test_va_recent_bills_date_filtering():
    crawler = VirginiaLISCrawler(start_year=2024, end_year=2026)
    assert hasattr(crawler, "fetch_recent_passed_bills")
    
    bills = crawler.fetch_recent_passed_bills(days=90)
    assert isinstance(bills, list)
    assert len(bills) > 0
    for bill in bills:
        assert "bill_id" in bill
        assert "chapter" in bill
        assert "text" in bill
        assert "enacted_date" in bill
        # Verify date is within past 90 days or current session window
        bill_date = datetime.strptime(bill["enacted_date"], "%Y-%m-%d")
        cutoff = datetime.now() - timedelta(days=95)
        assert bill_date >= cutoff
