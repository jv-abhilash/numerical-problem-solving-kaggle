# from __future__ import annotations
# from typing import List
# from .parser import parse_document as _parse
# from .config import P1Config
# from src.shared.schema import Question


# def parse_document(path: str, cfg: P1Config | None = None) -> List[Question]:
#     """
#     Public façade for P1. Keeping this narrow lets main.py stay stable even if internals change.
#     """
#     return _parse(path, cfg)


# src/p1_ingestion/api.py
from __future__ import annotations
from typing import List
from .parsing.parser import DocumentParser
from src.shared.schema import Question

def parse_document(path: str) -> List[Question]:
    return DocumentParser().parse_document(path)
