# src/pipeline/ingest.py
"""
P1: Ingestion & Normalization - Integrated with existing pipeline
Adapted to work with existing router/solver architecture
"""

import re
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Union, Tuple
import pymupdf 
import pdfplumber

from ..utils.io import _to_int, normalize_record
from ..utils.schema import extract_between_markers, brace_scan_candidates, try_json_loads
from .normalize import _clean, phrase_from_question


class DocumentParser:
    """
    Handles PDF and TXT parsing for KCET papers
    Integrates with existing question parsing from pipeline
    """
    
    def __init__(self):
        # Question patterns adapted from your existing code
        self.question_patterns = [
            r'Q(?P<n>\d+)\s*\.?\s*:?',  # Matches your existing Q1. Q2: format
        ]
        
        # Option patterns - matches (1), (2), (3), (4) format from your code
        self.option_patterns = [
            r'\(\s*(?P<num>[1-4])\s*\)',  # (1), (2), etc.
            r'(?P<num>[1-4])[\.\)]\s*',   # 1. or 1) format
        ]
    
    def parse_document(self, file_path: Union[str, Path]) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
        """
        Parse document and return qtexts, options in format compatible with existing pipeline
        
        Returns:
            Tuple of (qtexts, options) where:
            - qtexts: {'q1': 'question_text', 'q2': 'question_text', ...}
            - options: {'q1': ['opt1', 'opt2', 'opt3', 'opt4'], ...}
        """
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == '.pdf':
            text_content = self._parse_pdf(file_path)
        elif file_path.suffix.lower() in ['.txt', '.text']:
            text_content = self._parse_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        return self._extract_questions_and_options(text_content)
    
    def _parse_pdf(self, file_path: Path) -> str:
        """Parse PDF using both PyMuPDF and pdfplumber for robustness"""
        text_content = ""
        
        try:
            # Try PyMuPDF first (faster)
            with pymupdf.open(file_path) as doc:
                for page in doc:
                    text_content += page.get_text() + "\n"
        except Exception as e:
            print(f"PyMuPDF failed, trying pdfplumber: {e}")
            
            # Fallback to pdfplumber
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_content += page_text + "\n"
            except Exception as e:
                raise Exception(f"Both PDF parsers failed: {e}")
        
        return self._clean_text(text_content)
    
    def _parse_txt(self, file_path: Path) -> str:
        """Parse plain text file with encoding handling"""
        encodings_to_try = ['utf-8', 'latin-1', 'cp1252']
        
        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                return self._clean_text(content)
            except UnicodeDecodeError:
                continue
        
        raise ValueError(f"Could not read {file_path} with any encoding")
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content - uses existing _clean function"""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = _clean(text)  # Use existing utility
        
        # Normalize common Unicode issues
        replacements = {
            '"': '"', '"': '"',  # Smart quotes
            ''': "'", ''': "'",  # Smart apostrophes
            '–': '-', '—': '-',  # Em/en dashes
            '…': '...',          # Ellipsis
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text.strip()
    
    def _extract_questions_and_options(self, text: str) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
        """
        Extract questions and options in format compatible with existing pipeline
        Adapted from your existing question parsing logic
        """
        # Find all question anchors using existing pattern
        anchors = list(re.finditer(r"(Q(?P<n>\d+)\s*\.?\s*:?)", text, flags=re.I))
        
        qtexts = {}
        options = {}
        
        for i, anchor in enumerate(anchors):
            q_num = int(anchor.group("n"))
            q_key = f"q{q_num}"
            
            # Extract question chunk
            start = anchor.start()
            end = anchors[i + 1].start() if i + 1 < len(anchors) else len(text)
            chunk = text[start:end].strip()
            
            # Split question text from options at first "(1)"
            parts = re.split(r"\(\s*1\s*\)", chunk, maxsplit=1)
            if len(parts) == 2:
                question_part = parts[0].strip()
                options_part = "(1)" + parts[1]  # Re-add the (1) marker
            else:
                # Fallback: try to find question end by looking for option patterns
                question_part = chunk
                options_part = ""
                
                # Look for first option pattern
                for pattern in self.option_patterns:
                    match = re.search(pattern, chunk)
                    if match:
                        split_pos = match.start()
                        question_part = chunk[:split_pos].strip()
                        options_part = chunk[split_pos:].strip()
                        break
            
            # Clean question text
            question_text = re.sub(r"Q\d+\s*\.?\s*:?\s*", "", question_part).strip()
            question_text = _clean(question_text)
            
            # Extract 4 options
            question_options = self._extract_four_options(options_part)
            
            qtexts[q_key] = question_text
            options[q_key] = question_options
        
        return qtexts, options
    
    def _extract_four_options(self, options_text: str) -> List[str]:
        """Extract exactly 4 options from the options text"""
        option_list = []
        
        # Find all option matches
        option_matches = []
        for pattern in self.option_patterns:
            matches = list(re.finditer(pattern, options_text))
            if matches:
                option_matches = matches
                break
        
        if not option_matches:
            # Fallback: try to split by common patterns
            lines = options_text.split('\n')
            for line in lines[:4]:  # Take first 4 non-empty lines
                line = line.strip()
                if line and not re.match(r'^\s*$', line):
                    # Remove option numbering
                    line = re.sub(r'^\(\s*[1-4]\s*\)\s*', '', line)
                    line = re.sub(r'^[1-4][\.\)]\s*', '', line)
                    option_list.append(line.strip())
        else:
            # Extract options based on matches
            for i, match in enumerate(option_matches[:4]):  # Limit to 4 options
                start_pos = match.end()
                
                # Find end position (start of next option or end of text)
                if i + 1 < len(option_matches):
                    end_pos = option_matches[i + 1].start()
                else:
                    end_pos = len(options_text)
                
                option_text = options_text[start_pos:end_pos].strip()
                # Clean up the option text
                option_text = re.sub(r'\n+', ' ', option_text)
                option_text = _clean(option_text)
                option_list.append(option_text)
        
        # Ensure we have exactly 4 options
        while len(option_list) < 4:
            option_list.append(f"Option {len(option_list) + 1} (missing)")
        
        return option_list[:4]  # Return exactly 4 options
    
    def detect_figures(self, text: str) -> Dict[str, bool]:
        """Detect which questions have figures/diagrams"""
        figure_indicators = [
            'figure', 'diagram', 'graph', 'chart', 'image',
            'shown', 'given below', 'above figure', 'in the figure',
            'refer to', 'see the', 'as shown', 'illustrated'
        ]
        
        anchors = list(re.finditer(r"(Q(?P<n>\d+)\s*\.?\s*:?)", text, flags=re.I))
        figure_detection = {}
        
        for i, anchor in enumerate(anchors):
            q_num = int(anchor.group("n"))
            q_key = f"q{q_num}"
            
            # Extract question chunk
            start = anchor.start()
            end = anchors[i + 1].start() if i + 1 < len(anchors) else len(text)
            chunk = text[start:end].lower()
            
            has_figure = any(indicator in chunk for indicator in figure_indicators)
            figure_detection[q_key] = has_figure
        
        return figure_detection


def parse_questions_enhanced(text: str) -> Tuple[Dict[str, str], Dict[str, List[str]], Dict[str, bool]]:
    """
    Enhanced version of existing parse_questions function
    Returns qtexts, options, and figure detection
    
    Compatible with existing pipeline - can be drop-in replacement
    """
    parser = DocumentParser()
    qtexts, options = parser._extract_questions_and_options(text)
    figures = parser.detect_figures(text)
    
    return qtexts, options, figures


def ingest_document_to_pipeline_format(file_path: Union[str, Path]) -> Tuple[Dict[str, str], Dict[str, List[str]], Dict[str, bool]]:
    """
    Main P1 function that ingests document and returns data in pipeline format
    
    Args:
        file_path: Path to PDF or TXT file
        
    Returns:
        Tuple of (qtexts, options, figures) compatible with existing pipeline
    """
    parser = DocumentParser()
    qtexts, options = parser.parse_document(file_path)
    
    # Generate figure detection
    if Path(file_path).suffix.lower() in ['.txt', '.text']:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        figures = parser.detect_figures(text)
    else:
        # For PDF, we'd need to re-parse or store the text
        figures = {q: False for q in qtexts.keys()}  # Default to no figures for PDFs
    
    print(f"P1 Ingestion: Parsed {len(qtexts)} questions from {file_path}")
    
    return qtexts, options, figures


# Utility functions for integration with existing pipeline

def generate_question_hashes(qtexts: Dict[str, str], options: Dict[str, List[str]]) -> Dict[str, str]:
    """Generate content hashes for idempotency"""
    hashes = {}
    
    for qkey, qtext in qtexts.items():
        if qkey in options:
            content = qtext + ''.join(options[qkey])
            hash_value = hashlib.sha256(content.encode()).hexdigest()[:16]
            hashes[qkey] = f"sha256:{hash_value}"
        else:
            hashes[qkey] = "sha256:unknown"
    
    return hashes


def convert_to_structured_format(qtexts: Dict[str, str], options: Dict[str, List[str]], 
                                figures: Optional[Dict[str, bool]] = None,
                                source: str = "") -> List[Dict]:
    """
    Convert pipeline format to structured question format for storage/export
    
    Returns list of question dictionaries compatible with existing answer processing
    """
    questions = []
    figures = figures or {}
    
    for qkey, qtext in qtexts.items():
        # Extract question number
        q_match = re.match(r'q(\d+)', qkey)
        qid = int(q_match.group(1)) if q_match else None
        
        question_dict = {
            "qid": qid,
            "qkey": qkey,
            "question": qtext,
            "options": options.get(qkey, []),
            "has_figure": figures.get(qkey, False),
            "source": source,
            "question_hash": generate_question_hashes({qkey: qtext}, {qkey: options.get(qkey, [])})[qkey]
        }
        
        questions.append(question_dict)
    
    return questions


if __name__ == "__main__":
    # Test P1 with existing pipeline integration
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        
        print("=== P1: INGESTION TEST ===")
        
        # Test ingestion
        qtexts, options, figures = ingest_document_to_pipeline_format(file_path)
        
        print(f"Extracted {len(qtexts)} questions")
        
        # Show sample results
        for i, (qkey, qtext) in enumerate(list(qtexts.items())[:3]):
            print(f"\n{qkey.upper()}:")
            print(f"Text: {qtext[:100]}...")
            print(f"Options: {len(options.get(qkey, []))}")
            print(f"Has Figure: {figures.get(qkey, False)}")
            if qkey in options:
                for j, opt in enumerate(options[qkey]):
                    print(f"  ({j+1}) {opt[:50]}...")
        
        # Convert to structured format
        structured = convert_to_structured_format(qtexts, options, figures, str(file_path))
        print(f"\nConverted to {len(structured)} structured questions")
        
        # Generate hashes
        hashes = generate_question_hashes(qtexts, options)
        print(f"Generated content hashes for {len(hashes)} questions")
        
        print("\n=== P1 INTEGRATION COMPLETE ===")
        print("Ready for P2: Router integration")
    else:
        print("Usage: python -m src.pipeline.ingest <file_path>")