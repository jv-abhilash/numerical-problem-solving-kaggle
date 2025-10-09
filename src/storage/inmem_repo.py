# src/storage/inmem_repo.py
from __future__ import annotations
from typing import List, Dict, DefaultDict
from collections import defaultdict
from src.storage.interfaces import RunRepositoryP1
from src.shared.schema import Question, RoutedQuestion, Plan, RawAnswer, VerifiedAnswer

class InMemoryRunRepository(RunRepositoryP1):
    def __init__(self) -> None:
        self.runs: Dict[str, str] = {}
        self.qs: DefaultDict[str, List[Question]] = defaultdict(list)
        self.routes: DefaultDict[str, List[RoutedQuestion]] = defaultdict(list)
        self.plans: DefaultDict[str, List[Plan]] = defaultdict(list)
        self.raw: DefaultDict[str, List[RawAnswer]] = defaultdict(list)
        self.verified: DefaultDict[str, List[VerifiedAnswer]] = defaultdict(list)

    def init(self) -> None: ...
    def upsert_run(self, run_id: str, paper_path: str) -> None:
        self.runs[run_id] = paper_path

    def save_questions(self, run_id: str, questions: List[Question]) -> None:
        self.qs[run_id] = questions
    def load_questions(self, run_id: str) -> List[Question]:
        return list(self.qs.get(run_id, []))

    def save_routes(self, run_id: str, routes: List[RoutedQuestion]) -> None:
        self.routes[run_id] = routes
    def load_routes(self, run_id: str) -> List[RoutedQuestion]:
        return list(self.routes.get(run_id, []))

    def save_plans(self, run_id: str, plans: List[Plan]) -> None:
        self.plans[run_id] = plans
    def load_plans(self, run_id: str) -> List[Plan]:
        return list(self.plans.get(run_id, []))

    def save_raw_answers(self, run_id: str, answers: List[RawAnswer]) -> None:
        self.raw[run_id] = answers
    def load_raw_answers(self, run_id: str) -> List[RawAnswer]:
        return list(self.raw.get(run_id, []))

    def save_verified(self, run_id: str, verified: List[VerifiedAnswer]) -> None:
        self.verified[run_id] = verified
    def load_verified(self, run_id: str) -> List[VerifiedAnswer]:
        return list(self.verified.get(run_id, []))