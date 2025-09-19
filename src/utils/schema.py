# utils/json_tools.py
import re, json
from typing import Any, Dict, List, Optional

def strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S|re.I)

def extract_between_markers(text: str, start="<BEGIN_JSON>", end="<END_JSON>") -> Optional[str]:
    """Works with or without the end marker (since we use stop tokens)."""
    t = strip_think(text)
    m = re.search(re.escape(start) + r"\s*(\{.*?\})\s*" + re.escape(end), t, flags=re.S)
    if m:
        return m.group(1)
    m2 = re.search(re.escape(start) + r"\s*(\{.*)", t, flags=re.S)
    if m2:
        block = m2.group(1)
        depth = 0
        last_close = -1
        for i, ch in enumerate(block):
            if ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0: last_close = i
        if last_close != -1:
            return block[: last_close + 1].strip()
    return None

def brace_scan_candidates(text: str) -> List[str]:
    t, blocks, depth, start = strip_think(text), [], 0, None
    for i, ch in enumerate(t):
        if ch == "{":
            if depth == 0: start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    blocks.append(t[start:i+1]); start = None
    return blocks

def try_json_loads(s: str) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None

def best_json_candidate(text: str, expected_keys: List[str]) -> Optional[Dict[str, Any]]:
    best, best_overlap = None, -1
    for cand in brace_scan_candidates(text):
        obj = try_json_loads(cand)
        if not obj: continue
        if not all(re.fullmatch(r"q\d+", k) for k in obj.keys()):
            continue
        overlap = len(set(obj.keys()) & set(expected_keys))
        if overlap > best_overlap:
            best, best_overlap = obj, overlap
    return best