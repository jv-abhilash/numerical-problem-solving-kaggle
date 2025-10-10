# src/storage/interfaces.py
from __future__ import annotations
from typing import (
    Protocol,
    List,
    Dict,
    Optional,
    runtime_checkable,
    TypedDict,
    Required,        
    NotRequired,     
    Literal,         
)
from src.shared.schema import Question  # P1 type only

# ---------- P1 ----------
@runtime_checkable
class RunRepositoryP1(Protocol):
    # lifecycle
    def init(self) -> None: ...
    def upsert_run(self, run_id: str, paper_path: str) -> None: ...
    # P1
    def save_questions(self, run_id: str, questions: List[Question]) -> None: ...
    def load_questions(self, run_id: str) -> List[Question]: ...

# ---------- P2 ----------
class RouteRecord(TypedDict):
    run_id: Required[str]
    qid: Required[str]
    topic: Required[Literal["algebra","calculus","geometry","trigonometry","statistics","discrete","mixed"]]
    difficulty: Required[Literal["E","M","H"]]
    bucket: Required[str]  # "<topic>:<difficulty>"

    subtopic: NotRequired[Optional[str]]
    needs_tools: NotRequired[List[str]]
    confidence: NotRequired[float]      # 0..1
    notes: NotRequired[Optional[str]]

@runtime_checkable
class RunRepositoryP2(Protocol):
    def save_routes(self, run_id: str, routes: List[RouteRecord]) -> None: ...
    def load_routes(self, run_id: str) -> List[RouteRecord]: ...
    def upsert_bucket_counts(self, run_id: str, counts: Dict[str, int]) -> None: ...
    def load_bucket_counts(self, run_id: str) -> Dict[str, int]: ...