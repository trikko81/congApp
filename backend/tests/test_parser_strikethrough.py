import pytest
import pymupdf
from pathlib import Path
import tempfile

from backend.parser import PDFParser

def test_strikethrough_text_filtered_out():
    # Create a temporary PDF with normal text and strikethrough text
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        doc = pymupdf.open()
        page = doc.new_page(width=612, height=792)
        
        # Line 1: Normal active legal text
        page.insert_text(pymupdf.Point(50, 100), "Active provision for environmental regulation.", fontsize=11)
        
        # Line 2: Repealed / struck-out text (drawn with a strikethrough line through it)
        text_pt = pymupdf.Point(50, 140)
        page.insert_text(text_pt, "Repealed clause regarding mandatory coal emissions.", fontsize=11)
        # Draw horizontal strikethrough line across the text
        page.draw_line(pymupdf.Point(48, 136), pymupdf.Point(340, 136), color=(0, 0, 0), width=1.0)
        
        # Line 3: More active text
        page.insert_text(pymupdf.Point(50, 180), "Enacted renewable energy incentives shall take effect.", fontsize=11)
        
        doc.save(str(tmp_path))
        doc.close()

        parser = PDFParser()
        chunks = parser.parse_pdf(tmp_path)
        
        assert len(chunks) > 0
        all_chunk_text = " ".join(c.text_chunk for c in chunks)
        
        # Active text must be present
        assert "Active provision for environmental regulation" in all_chunk_text
        assert "Enacted renewable energy incentives" in all_chunk_text
        
        # Struck-through / repealed text must NOT be present
        assert "Repealed clause regarding mandatory coal emissions" not in all_chunk_text

    finally:
        if tmp_path.exists():
            tmp_path.unlink()
