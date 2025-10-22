# src/shared/config.py
from __future__ import annotations
import os
from typing import Optional, overload

# (optional) auto-load .env
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

@overload
def _env_str(name: str) -> Optional[str]: ...
@overload
def _env_str(name: str, default: str) -> str: ...

def _env_str(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    return v

def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    try:
        return int(v) if v not in (None, "") else default
    except Exception:
        return default

# -------- P2 LLM Router (OpenAI-compatible over HTTP) --------
ROUTER_BASE_URL: str = _env_str("ROUTER_BASE_URL", "http://192.168.68.59:7000")
ROUTER_API_KEY: Optional[str] = _env_str("ROUTER_API_KEY")  # may be None
ROUTER_MODEL_ID: str = _env_str("ROUTER_MODEL_ID", "Qwen/Qwen2.5-Math-7B")
ROUTER_TIMEOUT: int = _env_int("ROUTER_TIMEOUT", 30)
ROUTER_BATCH: int = _env_int("ROUTER_BATCH", 32)
ROUTER_STRATEGY: str = _env_str("ROUTER_STRATEGY", "llm_http")  # "llm_http" | "heuristic"