from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional
import re
import pymupdf



@dataclass
class DocumentChunk:
    doc_title: str
    page: int
    paragraph: int
    text_chunk: str
    token_count: int
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TextCleaner:
    STANDALONE_NOISE_RE = re.compile(r"^(?:[I|V|X|L|C|D|M]+|\d+)$", re.IGNORECASE)
    BOILERPLATE_PATTERNS = [
        re.compile(r"^119TH CONGRESS.*$", re.IGNORECASE),
        re.compile(r"^\d+D SESSION.*$", re.IGNORECASE),
        re.compile(r"^[A-Z0-9\-\s]{5,}—+$"),
    ]

    @classmethod
    def clean_text(cls, raw_text: str) -> Optional[str]:
        if not raw_text:
            return None

        cleaned = re.sub(r"\s+", " ", raw_text).strip()

        if len(cleaned) <= 4 and cls.STANDALONE_NOISE_RE.match(cleaned):
            return None

        for pattern in cls.BOILERPLATE_PATTERNS:
            if pattern.match(cleaned):
                return None

        return cleaned


class PDFParser:
    def __init__(self, chunk_size_tokens: int = 500, overlap_tokens: int = 50, min_chunk_words: int = 3) -> None:
        self.chunk_size_tokens = chunk_size_tokens
        self.overlap_tokens = overlap_tokens
        self.min_chunk_words = min_chunk_words
        self.cleaner = TextCleaner()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return max(1, len(text) // 4)

    def _build_chunk(self, segments: List[Dict], doc_title: str, paragraph_counter: int, sub_index: Optional[int] = None) -> DocumentChunk:
        text = " ".join(s["text"] for s in segments)
        token_count = self.estimate_tokens(text)
        first_seg = segments[0]
        meta = {
            "source_path": doc_title,
            "bbox": first_seg["bbox"]
        }
        if sub_index is not None:
            meta["sub_paragraph_index"] = sub_index
            
        return DocumentChunk(
            doc_title=doc_title,
            page=first_seg["page"],
            paragraph=paragraph_counter,
            text_chunk=text,
            token_count=token_count,
            metadata=meta
        )

    def parse_pdf(self, pdf_path: str | Path, max_chunks: Optional[int] = None) -> List[DocumentChunk]:
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")

        raw_segments = []
        with pymupdf.open(path) as doc:
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Detect strikethrough / strikeout vector lines and annotations
                strike_lines = []
                try:
                    for d in page.get_drawings():
                        for item in d.get("items", []):
                            if item[0] == "l":  # Line
                                p1, p2 = item[1], item[2]
                                if abs(p1.y - p2.y) < 3.0 and abs(p1.x - p2.x) > 4.0:
                                    min_x, max_x = min(p1.x, p2.x), max(p1.x, p2.x)
                                    strike_lines.append((min_x, max_x, (p1.y + p2.y) / 2.0))
                            elif item[0] == "re":  # Thin rectangle line
                                r = item[1]
                                if r.height < 3.5 and r.width > 4.0:
                                    strike_lines.append((r.x0, r.x1, (r.y0 + r.y1) / 2.0))

                    for annot in page.annots():
                        if annot.type[0] == pymupdf.PDF_ANNOT_STRIKE_OUT:
                            r = annot.rect
                            strike_lines.append((r.x0, r.x1, (r.y0 + r.y1) / 2.0))
                except Exception:
                    strike_lines = []

                # If strikethrough lines exist on page, filter word-by-word
                if strike_lines:
                    words = page.get_text("words")
                    active_words_by_block = {}
                    block_bboxes = {}

                    for w in words:
                        wx0, wy0, wx1, wy1, wtext, block_no, line_no, word_no = w[:8]
                        # Check if word intersects any strike line
                        is_struck = False
                        for lx0, lx1, ly in strike_lines:
                            if (wy0 - 3.0 <= ly <= wy1 + 3.0) and (lx0 <= wx1 and lx1 >= wx0):
                                is_struck = True
                                break

                        if not is_struck and wtext.strip():
                            if block_no not in active_words_by_block:
                                active_words_by_block[block_no] = [wtext]
                                block_bboxes[block_no] = [wx0, wy0, wx1, wy1]
                            else:
                                active_words_by_block[block_no].append(wtext)
                                bb = block_bboxes[block_no]
                                bb[0] = min(bb[0], wx0)
                                bb[1] = min(bb[1], wy0)
                                bb[2] = max(bb[2], wx1)
                                bb[3] = max(bb[3], wy1)

                    for block_no, wlist in active_words_by_block.items():
                        block_text = " ".join(wlist).strip()
                        cleaned = self.cleaner.clean_text(block_text)
                        if cleaned and len(cleaned.split()) >= self.min_chunk_words:
                            bb = block_bboxes[block_no]
                            raw_segments.append({
                                "text": cleaned,
                                "page": page_num + 1,
                                "bbox": (bb[0], bb[1], bb[2], bb[3])
                            })
                else:
                    # Fast path for pages without strikethroughs
                    blocks = page.get_text("blocks")
                    for block in blocks:
                        text = block[4].strip()
                        if not text or block[6] != 0:
                            continue
                        cleaned = self.cleaner.clean_text(text)
                        if not cleaned or len(cleaned.split()) < self.min_chunk_words:
                            continue
                        raw_segments.append({
                            "text": cleaned,
                            "page": page_num + 1,
                            "bbox": (block[0], block[1], block[2], block[3])
                        })


        merged_segments = []
        current_text = ""
        current_page = None
        current_bbox = None
        
        for seg in raw_segments:
            if not current_text:
                current_text = seg["text"]
                current_page = seg["page"]
                current_bbox = seg["bbox"]
            else:
                if not re.search(r'[.!?]["\']?\s*$', current_text):
                    current_text += " " + seg["text"]
                else:
                    merged_segments.append({
                        "text": current_text,
                        "page": current_page,
                        "bbox": current_bbox
                    })
                    current_text = seg["text"]
                    current_page = seg["page"]
                    current_bbox = seg["bbox"]
        
        if current_text:
            merged_segments.append({
                "text": current_text,
                "page": current_page,
                "bbox": current_bbox
            })

        chunks: List[DocumentChunk] = []
        paragraph_counter = 1
        current_chunk_segs = []
        current_tokens = 0
        added_new_since_flush = False
        
        min_tokens = 200
        max_tokens = self.chunk_size_tokens
        
        for seg in merged_segments:
            if max_chunks is not None and len(chunks) >= max_chunks:
                break
                
            seg_tokens = self.estimate_tokens(seg["text"])
            
            if seg_tokens > max_tokens:
                if current_chunk_segs and added_new_since_flush:
                    chunks.append(self._build_chunk(current_chunk_segs, path.name, paragraph_counter))
                    paragraph_counter += 1
                    current_chunk_segs = []
                    current_tokens = 0
                    added_new_since_flush = False
                
                sub_texts = self._split_paragraph(seg["text"])
                for idx, sub_text in enumerate(sub_texts):
                    if max_chunks is not None and len(chunks) >= max_chunks:
                        break
                    sub_seg = {"text": sub_text, "page": seg["page"], "bbox": seg["bbox"]}
                    chunks.append(self._build_chunk([sub_seg], path.name, paragraph_counter, sub_index=idx + 1))
                paragraph_counter += 1
                continue
                
            current_chunk_segs.append(seg)
            current_tokens += seg_tokens
            added_new_since_flush = True
            
            if current_tokens >= min_tokens:
                chunks.append(self._build_chunk(current_chunk_segs, path.name, paragraph_counter))
                paragraph_counter += 1
                added_new_since_flush = False
                
                overlap_segs = []
                overlap_tokens_count = 0
                for s in reversed(current_chunk_segs):
                    t_count = self.estimate_tokens(s["text"])
                    if overlap_tokens_count + t_count <= self.overlap_tokens or not overlap_segs:
                        overlap_segs.insert(0, s)
                        overlap_tokens_count += t_count
                    else:
                        break
                        
                if len(current_chunk_segs) == 1:
                    current_chunk_segs = []
                    current_tokens = 0
                else:
                    current_chunk_segs = overlap_segs
                    current_tokens = sum(self.estimate_tokens(s["text"]) for s in current_chunk_segs)

        if current_chunk_segs and added_new_since_flush and (max_chunks is None or len(chunks) < max_chunks):
            chunks.append(self._build_chunk(current_chunk_segs, path.name, paragraph_counter))

        return chunks

    def _split_paragraph(self, text: str) -> List[str]:
        words = text.split(" ")
        chunks: List[str] = []
        current_words: List[str] = []

        for word in words:
            current_words.append(word)
            sub_text = " ".join(current_words)
            if self.estimate_tokens(sub_text) >= self.chunk_size_tokens:
                chunks.append(sub_text)
                overlap_word_count = max(1, self.overlap_tokens // 2)
                current_words = current_words[-overlap_word_count:]

        if current_words:
            chunks.append(" ".join(current_words))

        return chunks


if __name__ == "__main__":
    import json

    sample_pdf = Path(__file__).resolve().parent.parent / "TEMPPDF" / "S5087_Clean_Air_Act_Renewable_Biomass_Amendment.pdf"
    if sample_pdf.exists():
        parser = PDFParser()
        result = parser.parse_pdf(sample_pdf, max_chunks=3)
        print(f"Loaded exactly {len(result)} chunks from {sample_pdf.name}:\n")
        print(json.dumps([c.to_dict() for c in result], indent=2))
        
