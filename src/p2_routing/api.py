# src/p2_routing/api.py
from __future__ import annotations
from typing import Dict, Any, List
from src.storage.interfaces import RunRepositoryP1P2, RouteRecord
from src.p2_routing.engines import get_router_engine
from src.p2_routing.interfaces import RouterEngine
from src.shared.config import ROUTER_STRATEGY, ROUTER_BATCH

def run_routing(
    repo: RunRepositoryP1P2,
    run_id: str,
    *,
    persist: bool = True,
    batch_size: int | None = None,
    router: str | None = None,           # "llm_http" | "heuristic"
    mcp_endpoint: str | None = None,     # ignored in HTTP-LLM path
    mcp_api_key: str | None = None,      # ignored in HTTP-LLM path
    mcp_tool: str = "route_questions",   # ignored in HTTP-LLM path
) -> Dict[str, Any]:

    # 1) load questions
    questions = repo.load_questions(run_id)

    # 2) pick engine (env default if not provided)
    kind = router or ROUTER_STRATEGY
    engine: RouterEngine = get_router_engine(kind=kind)

    # 3) batch (simple slab batching even though HTTP client loops internally)
    batch = batch_size or ROUTER_BATCH
    routes: List[RouteRecord] = []
    for i in range(0, len(questions), max(1, batch)):
        slab = questions[i:i+batch]
        routes.extend(engine.route_batch(slab))

    # 4) compute counts and attach run_id
    counts: Dict[str, int] = {}
    for r in routes:
        r["run_id"] = run_id
        counts[r["bucket"]] = counts.get(r["bucket"], 0) + 1

    # 5) persist
    if persist:
        repo.save_routes(run_id, routes)
        repo.upsert_bucket_counts(run_id, counts)

    return {
        "status": "ok",
        "engine": kind,
        "run_id": run_id,
        "total": len(routes),
        "buckets": counts,
        "preview": routes[:5],
    }