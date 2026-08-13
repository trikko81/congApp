import pytest
from pathlib import Path
from notebooks.virginia_crawler import VirginiaLISCrawler, VirginiaChapteredBill

def test_virginia_crawler_init() -> None:
    crawler = VirginiaLISCrawler(start_year=2016, end_year=2026)
    assert crawler.start_year == 2016
    assert crawler.end_year == 2026
    assert "2024" in crawler.session_codes

def test_virginia_session_code_mapping() -> None:
    crawler = VirginiaLISCrawler(start_year=2016, end_year=2026)
    code = crawler.get_session_code(2020, session_type="regular")
    assert code == "201"
    code_2024 = crawler.get_session_code(2024, session_type="regular")
    assert code_2024 == "241"

def test_crawler_fetch_chaptered_bills_sample() -> None:
    crawler = VirginiaLISCrawler(start_year=2016, end_year=2026)
    bills = crawler.get_curated_or_scraped_bills(year=2020, limit=2)
    assert len(bills) > 0
    bill = bills[0]
    assert isinstance(bill, VirginiaChapteredBill)
    assert bill.state == "Virginia"
    assert bill.year == 2020
    assert bill.title != ""
    assert len(bill.text_content) > 50
