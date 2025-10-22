# src/p2_routing/services/routing_service.py
from __future__ import annotations
from typing import Dict, Any
from src.storage.interfaces import RunRepositoryP1P2
from src.p2_routing.api import run_routing
from src.shared.config import ROUTER_STRATEGY, ROUTER_BATCH

class P2RoutingService:
    def __init__(self, repo: RunRepositoryP1P2) -> None:
        self.repo = repo

    def route(
        self,
        run_id: str,
        *,
        persist: bool = True,
        batch_size: int | None = None,
        router: str | None = None,
        mcp_endpoint: str | None = None,
        mcp_api_key: str | None = None,
        mcp_tool: str = "route_questions",
    ) -> Dict[str, Any]:
        return run_routing(
            self.repo,
            run_id,
            persist=persist,
            batch_size=batch_size or ROUTER_BATCH,
            router=router or ROUTER_STRATEGY,
            mcp_endpoint=mcp_endpoint,
            mcp_api_key=mcp_api_key,
            mcp_tool=mcp_tool,
        )