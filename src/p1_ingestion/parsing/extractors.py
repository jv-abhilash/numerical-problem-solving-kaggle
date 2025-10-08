from __future__ import annotations
import re
from typing import List, Dict
from src.shared.schema import Question


# Recognize question starts like:
#   "1) ", "1. ", "12) ", "12. "
_QSTART = re.compile(r"(?m)^\s*(\d{1,3})\s*[\.\)]\s+")

# Recognize options in multiple common formats:
#   (A) text
#   A) text
#   A. text
#   (a) text
_OPT_LINE = re.compile(r"(?im)^\s*[\(\[]?\s*([ABCD])\s*[\)\].-]?\s+(.*\S)\s*$")


def _split_question_blocks(text: str) -> List[tuple[int, str]]:
    """
    Split the entire paper into (qnum, block_text) pairs by regex markers.
    """
    blocks: List[tuple[int, str]] = []
    starts = list(_QSTART.finditer(text))

    for i, m in enumerate(starts):
        qnum = int(m.group(1))
        start = m.end()
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        block = text[start:end].strip()
        blocks.append((qnum, block))
    return blocks


def _extract_options(block: str) -> List[str]:
    """
    Extract up to 4 option lines in typical KCET formats.
    If none found, return [].
    """
    opts: List[str] = []
    # Get contiguous option lines; if scattered, we'll still capture them
    for m in _OPT_LINE.finditer(block):
        opts.append(m.group(2).strip())

    # If > 4, keep first 4
    if len(opts) > 4:
        opts = opts[:4]
    return opts


def _strip_options_from_block(block: str) -> str:
    """
    Remove option lines from the block to yield a clean stem.
    """
    lines = block.splitlines()
    stem_lines: List[str] = []
    for ln in lines:
        if _OPT_LINE.match(ln):
            continue
        stem_lines.append(ln)
    stem = "\n".join(stem_lines).strip()
    # Remove trailing extra newlines/spaces
    stem = re.sub(r"\n{3,}", "\n\n", stem).strip()
    return stem


def extract_questions(text: str, *, prefix: str = "Q") -> List[Question]:
    """
    High-level extractor:
      - detect question blocks
      - parse options
      - produce Question dicts
    """
    out: List[Question] = []
    for qnum, block in _split_question_blocks(text):
        opts = _extract_options(block)
        stem = _strip_options_from_block(block)

        qid = f"{prefix}{qnum}"
        q: Question = {
            "qid": qid,
            "raw": block,
            "stem": stem,
            "latex": "",           # placeholder; fill later in a LaTeX normalization pass
            "opts": opts,
            "has_options": len(opts) > 0,
        }
        out.append(q)
    return out