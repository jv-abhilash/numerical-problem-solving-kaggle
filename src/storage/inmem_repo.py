# src/storage/inmem_repo.py
from __future__ import annotations
from typing import List, Dict, DefaultDict
from collections import defaultdict

from src.storage.interfaces import (
    RunRepositoryP1P2P3,  # <-- use combined protocol
    RouteRecord,
    PlanRecord,
)
from src.shared.schema import Question

class InMemoryRunRepository(RunRepositoryP1P2P3):
    def __init__(self) -> None:
        # P1
        self.runs: Dict[str, str] = {}
        self.qs: DefaultDict[str, List[Question]] = defaultdict(list)

        # P2
        self.routes: DefaultDict[str, List[RouteRecord]] = defaultdict(list)
        self.bucket_counts: DefaultDict[str, Dict[str, int]] = defaultdict(dict)

        # P3
        self.plans: DefaultDict[str, List[PlanRecord]] = defaultdict(list)

    def init(self) -> None:
        ...

    # ----- P1 -----
    def upsert_run(self, run_id: str, paper_path: str) -> None:
        self.runs[run_id] = paper_path

    def save_questions(self, run_id: str, questions: List[Question]) -> None:
        self.qs[run_id] = list(questions)

    def load_questions(self, run_id: str) -> List[Question]:
        return list(self.qs.get(run_id, []))

    # ----- P2 -----
    def save_routes(self, run_id: str, routes: List[RouteRecord]) -> None:
        self.routes[run_id] = list(routes)

    def load_routes(self, run_id: str) -> List[RouteRecord]:
        return list(self.routes.get(run_id, []))

    def upsert_bucket_counts(self, run_id: str, counts: Dict[str, int]) -> None:
        self.bucket_counts[run_id] = dict(counts)

    def load_bucket_counts(self, run_id: str) -> Dict[str, int]:
        return dict(self.bucket_counts.get(run_id, {}))

    # ----- P3 -----
    def save_plans(self, run_id: str, plans: List[PlanRecord]) -> None:
        self.plans[run_id] = list(plans)

    def load_plans(self, run_id: str) -> List[PlanRecord]:
        return list(self.plans.get(run_id, []))