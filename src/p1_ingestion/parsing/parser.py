"""
P1: Ingestion & Normalization
Parses TXT/PDF and returns List[Question] (src.shared.schema.Question)
Strict KCET format: questions start with 'Qn' and options use numbered markers (1)(2)(3)(4).
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import List, Union, Optional

# Optional PDF libs
try:
    import fitz as pymupdf  # PyMuPDF
except Exception:  # pragma: no cover
    pymupdf = None  # type: ignore

try:
    import pdfplumber  # type: ignore
except Exception:  # pragma: no cover
    pdfplumber = None  # type: ignore

from src.shared.schema import Question
from .cleaners import _clean, normalize_question_text, normalize_option_text

# ---------- Patterns (strict to your KCET format) ----------
# Q-anchors at line start: "Q1", "Q2", optionally followed by '.', ')', ':' or '-'
_QANCHOR = re.compile(r"(?m)^\s*Q\s*(\d{1,3})\s*[\.\):\-]?\s*")
# Numbered options: (1) ( 2 ) etc.
_NUM_OPT = re.compile(r"\(\s*([1-4])\s*\)")

class DocumentParser:
    """Parse KCET-like papers from TXT or PDF into unified Question dicts."""

    def __init__(self) -> None:
        pass

    # ----------- Public API -----------
    def parse_document(self, path: Union[str, Path], prefix: str = "Q") -> List[Question]:
        """Main entry: returns a list[Question]."""
        p = Path(path)
        if p.suffix.lower() == ".pdf":
            text = self._read_pdf(p)
        else:
            text = self._read_txt(p)
        return self._extract_questions(text, prefix=prefix)

    # ----------- Readers -----------
    def _read_txt(self, path: Path) -> str:
        encodings = ("utf-8", "utf-16", "latin-1", "cp1252")
        for enc in encodings:
            try:
                raw = path.read_text(encoding=enc, errors="strict")
                return self._clean_text(raw)
            except UnicodeError:
                continue
        # last resort
        return self._clean_text(path.read_text(encoding="utf-8", errors="ignore"))

    def _read_pdf(self, path: Path) -> str:
    # Try PyMuPDF first
        if pymupdf is not None:
            try:
                out: List[str] = []
                with pymupdf.open(path) as doc:  # type: ignore[attr-defined]
                    for page in doc:
                        txt = ""
                        # Prefer modern API
                        try:
                            txt = page.get_text("text")  # PyMuPDF >= 1.18
                        except Exception:
                            # Fallback: some builds accept get_text() without arg
                            try:
                                txt = page.get_text()  # type: ignore[call-arg]
                            except Exception:
                                # Very old API
                                try:
                                    txt = page.getText("text")  # PyMuPDF <= 1.17
                                except Exception:
                                    txt = ""
                        out.append(txt or "")
                return self._clean_text("\n".join(out))
            except Exception:
                pass  # fall through to pdfplumber

        # Fallback to pdfplumber
        if pdfplumber is not None:
            try:
                out: List[str] = []
                with pdfplumber.open(path) as pdf:  # type: ignore[attr-defined]
                    for page in pdf.pages:
                        s = page.extract_text() or ""
                        out.append(s)
                return self._clean_text("\n".join(out))
            except Exception:
                pass

        raise RuntimeError("No PDF backend available (install PyMuPDF or pdfplumber).")

    # ----------- Cleaning -----------
    def _clean_text(self, text: str) -> str:
        t = text or ""
        # unify line breaks and collapse long blank areas
        t = re.sub(r"\r\n?", "\n", t)
        t = re.sub(r"\n\s*\n", "\n\n", t)
        # common unicode normalizations
        t = (t.replace("’", "'").replace("‘", "'")
               .replace("“", '"').replace("”", '"')
               .replace("‐", "-").replace("–", "-").replace("—", "-")
               .replace("…", "...").replace("∗", "*"))
        # trim trailing spaces per line
        t = re.sub(r"[ \t]+$", "", t, flags=re.M)
        return t.strip()

    # ----------- Extraction -----------
    def _extract_questions(self, text: str, *, prefix: str = "Q") -> List[Question]:
        """Split by question anchors; parse stem and numbered options."""
        anchors = list(_QANCHOR.finditer(text))
        out: List[Question] = []

        for i, m in enumerate(anchors):
            qnum = int(m.group(1))
            start = m.end()
            end = anchors[i + 1].start() if i + 1 < len(anchors) else len(text)
            block = text[start:end].strip()

            # Split stem/options at the first "(1)" marker (robust for inline or multiline)
            m1 = _NUM_OPT.search(block)
            if not m1:
                stem_block = block
                options_block = ""
            else:
                stem_block = block[: m1.start()].strip()
                options_block = block[m1.start():].strip()

            stem = normalize_question_text(re.sub(r"^\s*(?:Q\s*)?\d+.*?$", "", stem_block, flags=re.M))
            opts = self._extract_numbered_options(options_block)

            qid = f"{prefix}{qnum}"
            out.append({
                "qid": qid,
                "raw": block,
                "stem": stem,
                "latex": "",
                "opts": opts,
                "has_options": len(opts) > 0,
            })

        return out

    def _extract_numbered_options(self, options_block: str) -> List[str]:
        """
        Slice options using numbered markers (1)(2)(3)(4),
        whether options are on separate lines or inline.
        """
        if not options_block:
            return []

        marks = list(_NUM_OPT.finditer(options_block))

        # Record the FIRST occurrence of each marker 1..4, in order
        first_by_num: dict[str, re.Match[str]] = {}
        for m in marks:
            num = m.group(1)
            if num in ("1", "2", "3", "4") and num not in first_by_num:
                first_by_num[num] = m

        if "1" not in first_by_num:
            # Can't reliably slice without the first marker
            return []

        ordered = [first_by_num.get(n) for n in ("1", "2", "3", "4")]
        spans: List[tuple[int, int]] = []
        for i, m in enumerate(ordered):
            if m is None:
                break  # stop at the last present marker
            start = m.end()
            next_m = next((x for x in ordered[i + 1:] if x is not None), None)
            end = next_m.start() if next_m else len(options_block)
            spans.append((start, end))

        opts: List[str] = []
        for start, end in spans:
            chunk = options_block[start:end]
            # collapse whitespace and normalize
            chunk = re.sub(r"\s+", " ", chunk).strip()
            chunk = normalize_option_text(chunk)
            if chunk:
                opts.append(chunk)

        return opts[:4]


# # src/p1_ingestion/parsing/parser.py
# """
# P1: Ingestion & Normalization - Integrated with existing pipeline
# Adapted to work with existing router/solver architecture
# """

# import re
# import hashlib
# from pathlib import Path
# from typing import List, Dict, Optional, Union, Tuple
# import pymupdf 
# import pdfplumber

# from ..utils.io import _to_int, normalize_record
# from ..utils.schema import extract_between_markers, brace_scan_candidates, try_json_loads
# from .cleaners import _clean, phrase_from_question


# class DocumentParser:
#     """
#     Handles PDF and TXT parsing for KCET papers
#     Integrates with existing question parsing from pipeline
#     """
    
#     def __init__(self):
#         # Question patterns adapted from your existing code
#         self.question_patterns = [
#             r'Q(?P<n>\d+)\s*\.?\s*:?',  # Matches your existing Q1. Q2: format
#         ]
        
#         # Option patterns - matches (1), (2), (3), (4) format from your code
#         self.option_patterns = [
#             r'\(\s*(?P<num>[1-4])\s*\)',  # (1), (2), etc.
#             r'(?P<num>[1-4])[\.\)]\s*',   # 1. or 1) format
#         ]
    
#     def parse_document(self, file_path: Union[str, Path]) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
#         """
#         Parse document and return qtexts, options in format compatible with existing pipeline
        
#         Returns:
#             Tuple of (qtexts, options) where:
#             - qtexts: {'q1': 'question_text', 'q2': 'question_text', ...}
#             - options: {'q1': ['opt1', 'opt2', 'opt3', 'opt4'], ...}
#         """
#         file_path = Path(file_path)
        
#         if file_path.suffix.lower() == '.pdf':
#             text_content = self._parse_pdf(file_path)
#         elif file_path.suffix.lower() in ['.txt', '.text']:
#             text_content = self._parse_txt(file_path)
#         else:
#             raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
#         return self._extract_questions_and_options(text_content)
    
#     def _parse_pdf(self, file_path: Path) -> str:
#         """Parse PDF using both PyMuPDF and pdfplumber for robustness"""
#         text_content = ""
        
#         try:
#             # Try PyMuPDF first (faster)
#             with pymupdf.open(file_path) as doc:
#                 for page in doc:
#                     text_content += page.get_text() + "\n"
#         except Exception as e:
#             print(f"PyMuPDF failed, trying pdfplumber: {e}")
            
#             # Fallback to pdfplumber
#             try:
#                 with pdfplumber.open(file_path) as pdf:
#                     for page in pdf.pages:
#                         page_text = page.extract_text()
#                         if page_text:
#                             text_content += page_text + "\n"
#             except Exception as e:
#                 raise Exception(f"Both PDF parsers failed: {e}")
        
#         return self._clean_text(text_content)
    
#     def _parse_txt(self, file_path: Path) -> str:
#         """Parse plain text file with encoding handling"""
#         encodings_to_try = ['utf-8', 'latin-1', 'cp1252']
        
#         for encoding in encodings_to_try:
#             try:
#                 with open(file_path, 'r', encoding=encoding) as f:
#                     content = f.read()
#                 return self._clean_text(content)
#             except UnicodeDecodeError:
#                 continue
        
#         raise ValueError(f"Could not read {file_path} with any encoding")
    
#     def _clean_text(self, text: str) -> str:
#         """Clean and normalize text content - uses existing _clean function"""
#         # Remove excessive whitespace
#         text = re.sub(r'\n\s*\n', '\n\n', text)
#         text = _clean(text)  # Use existing utility
        
#         # Normalize common Unicode issues
#         replacements = {
#             '"': '"', '"': '"',  # Smart quotes
#             ''': "'", ''': "'",  # Smart apostrophes
#             '–': '-', '—': '-',  # Em/en dashes
#             '…': '...',          # Ellipsis
#         }
        
#         for old, new in replacements.items():
#             text = text.replace(old, new)
        
#         return text.strip()
    
#     def _extract_questions_and_options(self, text: str) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
#         """
#         Extract questions and options in format compatible with existing pipeline
#         Adapted from your existing question parsing logic
#         """
#         # Find all question anchors using existing pattern
#         anchors = list(re.finditer(r"(Q(?P<n>\d+)\s*\.?\s*:?)", text, flags=re.I))
        
#         qtexts = {}
#         options = {}
        
#         for i, anchor in enumerate(anchors):
#             q_num = int(anchor.group("n"))
#             q_key = f"q{q_num}"
            
#             # Extract question chunk
#             start = anchor.start()
#             end = anchors[i + 1].start() if i + 1 < len(anchors) else len(text)
#             chunk = text[start:end].strip()
            
#             # Split question text from options at first "(1)"
#             parts = re.split(r"\(\s*1\s*\)", chunk, maxsplit=1)
#             if len(parts) == 2:
#                 question_part = parts[0].strip()
#                 options_part = "(1)" + parts[1]  # Re-add the (1) marker
#             else:
#                 # Fallback: try to find question end by looking for option patterns
#                 question_part = chunk
#                 options_part = ""
                
#                 # Look for first option pattern
#                 for pattern in self.option_patterns:
#                     match = re.search(pattern, chunk)
#                     if match:
#                         split_pos = match.start()
#                         question_part = chunk[:split_pos].strip()
#                         options_part = chunk[split_pos:].strip()
#                         break
            
#             # Clean question text
#             question_text = re.sub(r"Q\d+\s*\.?\s*:?\s*", "", question_part).strip()
#             question_text = _clean(question_text)
            
#             # Extract 4 options
#             question_options = self._extract_four_options(options_part)
            
#             qtexts[q_key] = question_text
#             options[q_key] = question_options
        
#         return qtexts, options
    
#     def _extract_four_options(self, options_text: str) -> List[str]:
#         """Extract exactly 4 options from the options text"""
#         option_list = []
        
#         # Find all option matches
#         option_matches = []
#         for pattern in self.option_patterns:
#             matches = list(re.finditer(pattern, options_text))
#             if matches:
#                 option_matches = matches
#                 break
        
#         if not option_matches:
#             # Fallback: try to split by common patterns
#             lines = options_text.split('\n')
#             for line in lines[:4]:  # Take first 4 non-empty lines
#                 line = line.strip()
#                 if line and not re.match(r'^\s*$', line):
#                     # Remove option numbering
#                     line = re.sub(r'^\(\s*[1-4]\s*\)\s*', '', line)
#                     line = re.sub(r'^[1-4][\.\)]\s*', '', line)
#                     option_list.append(line.strip())
#         else:
#             # Extract options based on matches
#             for i, match in enumerate(option_matches[:4]):  # Limit to 4 options
#                 start_pos = match.end()
                
#                 # Find end position (start of next option or end of text)
#                 if i + 1 < len(option_matches):
#                     end_pos = option_matches[i + 1].start()
#                 else:
#                     end_pos = len(options_text)
                
#                 option_text = options_text[start_pos:end_pos].strip()
#                 # Clean up the option text
#                 option_text = re.sub(r'\n+', ' ', option_text)
#                 option_text = _clean(option_text)
#                 option_list.append(option_text)
        
#         # Ensure we have exactly 4 options
#         while len(option_list) < 4:
#             option_list.append(f"Option {len(option_list) + 1} (missing)")
        
#         return option_list[:4]  # Return exactly 4 options
    
#     def detect_figures(self, text: str) -> Dict[str, bool]:
#         """Detect which questions have figures/diagrams"""
#         figure_indicators = [
#             'figure', 'diagram', 'graph', 'chart', 'image',
#             'shown', 'given below', 'above figure', 'in the figure',
#             'refer to', 'see the', 'as shown', 'illustrated'
#         ]
        
#         anchors = list(re.finditer(r"(Q(?P<n>\d+)\s*\.?\s*:?)", text, flags=re.I))
#         figure_detection = {}
        
#         for i, anchor in enumerate(anchors):
#             q_num = int(anchor.group("n"))
#             q_key = f"q{q_num}"
            
#             # Extract question chunk
#             start = anchor.start()
#             end = anchors[i + 1].start() if i + 1 < len(anchors) else len(text)
#             chunk = text[start:end].lower()
            
#             has_figure = any(indicator in chunk for indicator in figure_indicators)
#             figure_detection[q_key] = has_figure
        
#         return figure_detection


# def parse_questions_enhanced(text: str) -> Tuple[Dict[str, str], Dict[str, List[str]], Dict[str, bool]]:
#     """
#     Enhanced version of existing parse_questions function
#     Returns qtexts, options, and figure detection
    
#     Compatible with existing pipeline - can be drop-in replacement
#     """
#     parser = DocumentParser()
#     qtexts, options = parser._extract_questions_and_options(text)
#     figures = parser.detect_figures(text)
    
#     return qtexts, options, figures


# def ingest_document_to_pipeline_format(file_path: Union[str, Path]) -> Tuple[Dict[str, str], Dict[str, List[str]], Dict[str, bool]]:
#     """
#     Main P1 function that ingests document and returns data in pipeline format
    
#     Args:
#         file_path: Path to PDF or TXT file
        
#     Returns:
#         Tuple of (qtexts, options, figures) compatible with existing pipeline
#     """
#     parser = DocumentParser()
#     qtexts, options = parser.parse_document(file_path)
    
#     # Generate figure detection
#     if Path(file_path).suffix.lower() in ['.txt', '.text']:
#         with open(file_path, 'r', encoding='utf-8') as f:
#             text = f.read()
#         figures = parser.detect_figures(text)
#     else:
#         # For PDF, we'd need to re-parse or store the text
#         figures = {q: False for q in qtexts.keys()}  # Default to no figures for PDFs
    
#     print(f"P1 Ingestion: Parsed {len(qtexts)} questions from {file_path}")
    
#     return qtexts, options, figures


# # Utility functions for integration with existing pipeline

# def generate_question_hashes(qtexts: Dict[str, str], options: Dict[str, List[str]]) -> Dict[str, str]:
#     """Generate content hashes for idempotency"""
#     hashes = {}
    
#     for qkey, qtext in qtexts.items():
#         if qkey in options:
#             content = qtext + ''.join(options[qkey])
#             hash_value = hashlib.sha256(content.encode()).hexdigest()[:16]
#             hashes[qkey] = f"sha256:{hash_value}"
#         else:
#             hashes[qkey] = "sha256:unknown"
    
#     return hashes


# def convert_to_structured_format(qtexts: Dict[str, str], options: Dict[str, List[str]], 
#                                 figures: Optional[Dict[str, bool]] = None,
#                                 source: str = "") -> List[Dict]:
#     """
#     Convert pipeline format to structured question format for storage/export
    
#     Returns list of question dictionaries compatible with existing answer processing
#     """
#     questions = []
#     figures = figures or {}
    
#     for qkey, qtext in qtexts.items():
#         # Extract question number
#         q_match = re.match(r'q(\d+)', qkey)
#         qid = int(q_match.group(1)) if q_match else None
        
#         question_dict = {
#             "qid": qid,
#             "qkey": qkey,
#             "question": qtext,
#             "options": options.get(qkey, []),
#             "has_figure": figures.get(qkey, False),
#             "source": source,
#             "question_hash": generate_question_hashes({qkey: qtext}, {qkey: options.get(qkey, [])})[qkey]
#         }
        
#         questions.append(question_dict)
    
#     return questions


# if __name__ == "__main__":
#     # Test P1 with existing pipeline integration
#     import sys
    
#     if len(sys.argv) > 1:
#         file_path = sys.argv[1]
        
#         print("=== P1: INGESTION TEST ===")
        
#         # Test ingestion
#         qtexts, options, figures = ingest_document_to_pipeline_format(file_path)
        
#         print(f"Extracted {len(qtexts)} questions")
        
#         # Show sample results
#         for i, (qkey, qtext) in enumerate(list(qtexts.items())[:3]):
#             print(f"\n{qkey.upper()}:")
#             print(f"Text: {qtext[:100]}...")
#             print(f"Options: {len(options.get(qkey, []))}")
#             print(f"Has Figure: {figures.get(qkey, False)}")
#             if qkey in options:
#                 for j, opt in enumerate(options[qkey]):
#                     print(f"  ({j+1}) {opt[:50]}...")
        
#         # Convert to structured format
#         structured = convert_to_structured_format(qtexts, options, figures, str(file_path))
#         print(f"\nConverted to {len(structured)} structured questions")
        
#         # Generate hashes
#         hashes = generate_question_hashes(qtexts, options)
#         print(f"Generated content hashes for {len(hashes)} questions")
        
#         print("\n=== P1 INTEGRATION COMPLETE ===")
#         print("Ready for P2: Router integration")
#     else:
#         print("Usage: python -m src.pipeline.ingest <file_path>")