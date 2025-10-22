# src/p2_routing/engines/__init__.py
from __future__ import annotations
from typing import Optional

from src.p2_routing.interfaces import RouterEngine
from src.shared.config import (
    ROUTER_BASE_URL, ROUTER_MODEL_ID, ROUTER_API_KEY, ROUTER_TIMEOUT
)

# Import the HTTP LLM engine
from src.p2_routing.clients.llm_http_router import LLMHttpRouterEngine

def get_router_engine(
    kind: str = "llm_http",
    *,
    base_url: Optional[str] = None,
    model_id: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: Optional[float] = None,
) -> RouterEngine:
    """
    Get router engine instance.

    Currently only supports 'llm_http' (LLM over HTTP).
    Heuristic and MCP routers have been removed.
    """
    if kind != "llm_http":
        raise ValueError(f"Unsupported router kind: {kind}. Only 'llm_http' is supported.")

    return LLMHttpRouterEngine(
        base_url=base_url or ROUTER_BASE_URL,
        model_id=model_id or ROUTER_MODEL_ID,
        api_key=api_key if api_key is not None else ROUTER_API_KEY,
        timeout=float(timeout if timeout is not None else ROUTER_TIMEOUT),
    )
