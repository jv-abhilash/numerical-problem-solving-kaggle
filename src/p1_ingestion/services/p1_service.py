# src/p1_ingestion/services/p1_service.py
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.p1_ingestion.api import parse_document
from src.storage.interfaces import RunRepository
from src.shared.schema import Question

def _default_run_id(paper_path: str) -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{Path(paper_path).stem}-{ts}"

class P1IngestionService:
    def __init__(self, repo: RunRepository | None) -> None:
        self.repo = repo

    def ingest(self,
               paper_path: str,
               run_id: Optional[str] = None,
               persist: bool = True,
               debug_json_path: Optional[str] = None) -> Dict[str, Any]:
        run_id = run_id or _default_run_id(paper_path)

        questions: List[Question] = parse_document(paper_path)

        if persist and self.repo is not None:
            self.repo.init()
            self.repo.upsert_run(run_id, paper_path)
            self.repo.save_questions(run_id, questions)

        if debug_json_path:
            p = Path(debug_json_path); p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "run_id": run_id,
            "total_questions": len(questions),
            "with_options": sum(1 for q in questions if q["has_options"]),
            "questions": questions,
        }
