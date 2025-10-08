from __future__ import annotations
from pathlib import Path


def read_text_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Paper not found: {path}")
    return p.read_text(encoding="utf-8", errors="ignore")