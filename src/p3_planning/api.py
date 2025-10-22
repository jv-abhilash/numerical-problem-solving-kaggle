from __future__ import annotations
from typing import Dict, Any, List
from src.storage.interfaces import RunRepositoryP1P2P3, PlanRecord, RouteRecord
from src.p3_planning.budgeting.planner import build_steps
from src.p3_planning.budgeting.budgeter import compute_budget

def run_planning(
    repo: RunRepositoryP1P2P3,
    run_id: str,
    *,
    persist: bool = True,
    preview_n: int = 5,
) -> Dict[str, Any]:
    # 1) Load routes; require P2 to be done
    routes: List[RouteRecord] = repo.load_routes(run_id)
    if not routes:
        return {"status": "error", "run_id": run_id, "error": "No routes found for this run_id. Run P2 first."}

    # 2) (Optional) load questions if you want richer notes later
    # questions = {q["qid"]: q for q in repo.load_questions(run_id)}

    # 3) Build plans
    plans: List[PlanRecord] = []
    for r in routes:
        budget_tokens, max_calls, priority = compute_budget(r)
        # steps = build_steps(questions.get(r["qid"], {"stem": ""}), r)  # if you loaded questions
        # Minimal (no question context needed for generic steps):
        steps = build_steps({"qid": r["qid"], "stem": "", "raw": "", "latex": "", "opts": [], "has_options": False}, r)

        plans.append({
            "run_id": run_id,
            "qid": r["qid"],
            "topic": r["topic"],
            "difficulty": r["difficulty"],
            "bucket": r["bucket"],
            "steps": steps,
            "tools": r.get("needs_tools", []),
            "budget_tokens": budget_tokens,
            "max_calls": max_calls,
            "priority": priority,
            "notes": None,
        })

    # 4) Persist
    if persist:
        repo.save_plans(run_id, plans)

    # 5) Summaries
    by_topic: Dict[str,int] = {}
    by_diff: Dict[str,int] = {}
    for p in plans:
        by_topic[p["topic"]] = by_topic.get(p["topic"], 0) + 1
        by_diff[p["difficulty"]] = by_diff.get(p["difficulty"], 0) + 1

    return {
        "status": "ok",
        "run_id": run_id,
        "total": len(plans),
        "topic_counts": by_topic,
        "difficulty_counts": by_diff,
        "preview": plans[:preview_n],
    }