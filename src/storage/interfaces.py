# src/storage/interfaces.py
from __future__ import annotations

# Prefer stdlib typing on 3.11+, but fall back for editors/linters that lag
try:
    from typing import (
        Protocol,
        List,
        Dict,
        Optional,
        runtime_checkable,
        TypedDict,
        Required,       # PEP 655 (3.11+)
        NotRequired,    # PEP 655 (3.11+)
        Literal,
    )
except ImportError:  # pragma: no cover
    from typing import Protocol, List, Dict, Optional, runtime_checkable, TypedDict, Literal
    from typing_extensions import Required, NotRequired  # type: ignore

from src.shared.schema import Question  # P1 type only

# ---- Canonical routing types (single source of truth) ----
Topic = Literal["algebra", "calculus", "discrete", "geometry"]
Difficulty = Literal["E", "M", "H"]

# ---------- P1 ----------
@runtime_checkable
class RunRepositoryP1(Protocol):
    # lifecycle
    def init(self) -> None: ...
    def upsert_run(self, run_id: str, paper_path: str) -> None: ...
    # P1 data
    def save_questions(self, run_id: str, questions: List[Question]) -> None: ...
    def load_questions(self, run_id: str) -> List[Question]: ...

# ---------- P2 ----------
class RouteRecord(TypedDict):
    run_id: Required[str]
    qid: Required[str]
    topic: Required[Topic]
    difficulty: Required[Difficulty]
    bucket: Required[str]  # convention: "<topic>:<difficulty>"

    subtopic: NotRequired[Optional[str]]
    needs_tools: NotRequired[List[str]]  # e.g. ["sympy"]
    confidence: NotRequired[float]       # 0..1
    notes: NotRequired[Optional[str]]

@runtime_checkable
class RunRepositoryP2(Protocol):
    def save_routes(self, run_id: str, routes: List[RouteRecord]) -> None: ...
    def load_routes(self, run_id: str) -> List[RouteRecord]: ...
    def upsert_bucket_counts(self, run_id: str, counts: Dict[str, int]) -> None: ...
    def load_bucket_counts(self, run_id: str) -> Dict[str, int]: ...

# ---------- P3 ----------
class PlanRecord(TypedDict):
    run_id: Required[str]
    qid: Required[str]
    topic: Required[Topic]
    difficulty: Required[Difficulty]
    bucket: Required[str]
    steps: Required[List[str]]
    tools: Required[List[str]]
    budget_tokens: Required[int]
    max_calls: Required[int]
    priority: Required[int]
    notes: NotRequired[Optional[str]]

@runtime_checkable
class RunRepositoryP3(Protocol):
    def save_plans(self, run_id: str, plans: List[PlanRecord]) -> None: ...
    def load_plans(self, run_id: str) -> List[PlanRecord]: ...

# ---------- Combined protocols ----------
# Put Protocol LAST to avoid MRO issues in some type checkers.
@runtime_checkable
class RunRepositoryP1P2(RunRepositoryP1, RunRepositoryP2, Protocol):
    pass

@runtime_checkable
class RunRepositoryP1P2P3(RunRepositoryP1, RunRepositoryP2, RunRepositoryP3, Protocol):
    pass