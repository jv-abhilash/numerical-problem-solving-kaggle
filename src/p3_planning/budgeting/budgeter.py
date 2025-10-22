from __future__ import annotations
from typing import Tuple
from src.storage.interfaces import RouteRecord, Difficulty, Topic

# Priority: lower number = higher priority
TOPIC_PRIORITY = {
    "calculus": 0,
    "algebra": 1,
    "geometry": 2,
    "discrete": 3,
}

def _base_tokens(diff: Difficulty) -> int:
    return {"E": 256, "M": 512, "H": 1024}.get(diff, 512)

def _base_calls(diff: Difficulty) -> int:
    return {"E": 1, "M": 2, "H": 3}.get(diff, 2)

def compute_budget(route: RouteRecord) -> Tuple[int, int, int]:
    """
    Returns (budget_tokens, max_calls, priority).
    Increases cost for tool needs; uses topic to rank priority.
    """
    diff: Difficulty = route["difficulty"]
    topic: Topic = route["topic"]
    needs_tools = route.get("needs_tools", [])

    tokens = _base_tokens(diff)
    calls = _base_calls(diff)

    # If tools requested (e.g., sympy), give more headroom
    if needs_tools:
        tokens = int(tokens * 1.25)
        calls += 1

    priority = TOPIC_PRIORITY.get(topic, 5)
    return tokens, calls, priority