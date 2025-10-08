"""
JSON parsing utilities: extract JSON blocks from LLM text and normalize
Compatible with earlier utils/json_tools.py, with small cleanups.
"""

from __future__ import annotations
import re
import json
from typing import Any, Dict, List, Optional


# -------------------- Low-level helpers --------------------

def strip_think(text: str) -> str:
    """Remove <think>...</think> blocks from LLM output."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)


def extract_between_markers(text: str, start: str = "<BEGIN_JSON>", end: str = "<END_JSON>") -> Optional[str]:
    """
    Extract JSON between markers. Works if the end marker is missing by scanning braces.
    """
    t = strip_think(text)

    # Try explicit start/end first
    m = re.search(re.escape(start) + r"\s*(\{.*?\})\s*" + re.escape(end), t, flags=re.S)
    if m:
        return m.group(1)

    # Fallback: start only, then balanced-brace scan
    m2 = re.search(re.escape(start) + r"\s*(\{.*)", t, flags=re.S)
    if m2:
        block = m2.group(1)
        depth = 0
        last_close = -1
        for i, ch in enumerate(block):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    last_close = i
        if last_close != -1:
            return block[: last_close + 1].strip()

    return None


def brace_scan_candidates(text: str) -> List[str]:
    """Scan the text and return a list of balanced-brace JSON-like blocks."""
    t = strip_think(text)
    blocks: List[str] = []
    depth = 0
    start: Optional[int] = None

    for i, ch in enumerate(t):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    blocks.append(t[start : i + 1])
                    start = None
    return blocks


def try_json_loads(s: str) -> Optional[Dict[str, Any]]:
    """Try json.loads; return dict if successful, else None."""
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def best_json_candidate(text: str, expected_keys: List[str]) -> Optional[Dict[str, Any]]:
    """
    Choose the best JSON candidate among brace blocks by maximizing overlap with expected keys.
    Expected keys typically look like ["q1", "q2", ...].
    """
    best = None
    best_overlap = -1

    for cand in brace_scan_candidates(text):
        obj = try_json_loads(cand)
        if not obj:
            continue

        # Candidate must look like {"q1": {...}, "q2": {...}, ...}
        if not all(re.fullmatch(r"q\d+", k) for k in obj.keys()):
            continue

        overlap = len(set(obj.keys()) & set(expected_keys))
        if overlap > best_overlap:
            best = obj
            best_overlap = overlap

    return best


# -------------------- P1-oriented helpers --------------------

def validate_question_dict(question_dict: Dict[str, Any]) -> List[str]:
    """
    Validate structure of a *single* question dict.
    Less strict than before: allow 0..4 options during ingestion.
    Enforce "exactly 4" later (pre-evaluation) if needed.
    """
    errors: List[str] = []

    required_fields = ["qid", "question", "options"]
    for field in required_fields:
        if field not in question_dict:
            errors.append(f"Missing required field: {field}")

    # options
    if "options" in question_dict:
        options = question_dict["options"]
        if not isinstance(options, list):
            errors.append("Options must be a list")
        elif len(options) > 4:
            errors.append(f"Expected up to 4 options, got {len(options)}")
        elif any(not isinstance(opt, str) or not opt.strip() for opt in options):
            errors.append("All options must be non-empty strings")

    # qid: allow string (Q12) or int here; normalize later
    if "qid" in question_dict:
        qid = question_dict["qid"]
        if not isinstance(qid, (int, str)):
            errors.append("qid must be int or str")

    return errors


def normalize_question_dict(raw_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a raw question dict produced by various extractors/LLMs to a common shape.
    Output keys: qid (str), question (str), options (List[str]), has_figure (bool), metadata (dict?)
    """
    normalized: Dict[str, Any] = {}

    # qid
    for key in ["qid", "question_id", "id", "q_id"]:
        if key in raw_dict:
            val = raw_dict[key]
            if isinstance(val, int):
                normalized["qid"] = f"Q{val}"
                break
            else:
                s = str(val).strip()
                # Accept "Q12", "q12", "12"
                m = re.match(r"^(?:[Qq])?(\d+)$", s)
                if m:
                    normalized["qid"] = f"Q{int(m.group(1))}"
                    break

    # question text
    for key in ["question", "question_text", "text", "problem"]:
        if key in raw_dict and raw_dict[key]:
            normalized["question"] = str(raw_dict[key]).strip()
            break

    # options
    for key in ["options", "choices", "answers", "alternatives"]:
        if key in raw_dict:
            opts = raw_dict[key]
            if isinstance(opts, list):
                normalized["options"] = [str(opt).strip() for opt in opts[:4]]
                break

    normalized["has_figure"] = bool(raw_dict.get("has_figure", False))

    if "metadata" in raw_dict and isinstance(raw_dict["metadata"], dict):
        normalized["metadata"] = raw_dict["metadata"]

    return normalized


def extract_questions_from_llm_response(text: str, expected_questions: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Extract a JSON object like {"q1": {...}, "q2": {...}} from an LLM response.
    First try explicit markers; then fall back to best brace block.
    """
    block = extract_between_markers(text)
    if block:
        parsed = try_json_loads(block)
        if parsed and all(re.fullmatch(r"q\d+", k) for k in parsed.keys()):
            return parsed

    best = best_json_candidate(text, expected_questions)
    return best or {}


# -------------------- Small compat helpers --------------------

class QuestionFormat:
    """Key/ID helpers for q1/Q1 formats and option normalization."""

    @staticmethod
    def validate_qkey(qkey: str) -> bool:
        return bool(re.match(r"^[qQ]\d+$", qkey))

    @staticmethod
    def qkey_to_qid(qkey: str) -> Optional[str]:
        m = re.match(r"^[qQ](\d+)$", qkey)
        return f"Q{m.group(1)}" if m else None

    @staticmethod
    def qid_to_qkey(qid: str) -> str:
        m = re.match(r"^[Qq]?(\d+)$", qid)
        return f"q{m.group(1)}" if m else f"q{qid}"

    @staticmethod
    def normalize_option_index(option: Any) -> Optional[int]:
        """Return 1..4 for A/B/C/D or 1/2/3/4; None if not valid."""
        if isinstance(option, int) and 1 <= option <= 4:
            return option
        if isinstance(option, str):
            s = option.strip().upper()
            if s in ["A", "B", "C", "D"]:
                return ord(s) - ord("A") + 1
            try:
                v = int(s)
                return v if 1 <= v <= 4 else None
            except ValueError:
                pass
        return None