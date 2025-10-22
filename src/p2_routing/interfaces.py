# src/p2_routing/interfaces.py
from __future__ import annotations
from typing import Protocol, List
from src.shared.schema import Question
from src.storage.interfaces import RouteRecord

class RouterEngine(Protocol):
    def route_batch(self, questions: List[Question]) -> List[RouteRecord]: ...
