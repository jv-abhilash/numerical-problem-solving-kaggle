from __future__ import annotations
from dataclasses import dataclass


@dataclass
class P1Config:
    # If your TXT contains “weird” OCR artifacts, you can control a few toggles here
    collapse_blank_lines: bool = True
    normalize_quotes: bool = True
    strip_figures: bool = True      # remove lines like "[Figure 1]" or "Fig." tags
    max_question_number: int = 400  # safety bound for KCET-style sets