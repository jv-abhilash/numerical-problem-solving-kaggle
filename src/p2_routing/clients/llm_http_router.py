# src/p2_routing/clients/llm_http_router.py
from __future__ import annotations
from typing import List, Dict, Optional, Literal, cast
import requests

from src.shared.schema import Question
from src.storage.interfaces import RouteRecord, Topic, Difficulty
from src.p2_routing.interfaces import RouterEngine

# ---- Four-topic taxonomy (must match interfaces.py) ----
_ALLOWED_TOPICS: set[str] = {"algebra", "calculus", "discrete", "geometry"}
TopicLiteral = Literal["algebra", "calculus", "discrete", "geometry"]
DifficultyLiteral = Literal["E", "M", "H"]

def _coerce_topic(raw: Optional[str]) -> Topic:
    s = (raw or "").strip().lower()

    # synonyms -> 4 buckets
    if s in {"integration", "differentiation", "limits", "calc", "diffeq"}:
        s = "calculus"
    elif s in {"prob", "probability", "stats", "stat", "statistics", "sets", "set", "lpp", "graph", "graphs", "combinatorics", "permutation", "combination"}:
        s = "discrete"
    elif s in {"geom", "coordinate geometry", "analytic geometry", "conic", "circle", "triangle", "polygon", "locus"}:
        s = "geometry"
    elif s in {"vectors", "complex"}:
        s = "algebra"

    if s not in _ALLOWED_TOPICS:
        s = "algebra"
    return cast(Topic, s)

def _coerce_difficulty(raw: Optional[str]) -> Difficulty:
    s = (raw or "").strip().upper()
    if s not in {"E", "M", "H"}:
        s = "M"
    return cast(Difficulty, s)

class LLMHttpRouterEngine(RouterEngine):
    """
    Calls an OpenAI-compatible /v1/chat/completions endpoint (e.g., vLLM) to classify each question.
    One HTTP call per question for simplicity/reliability.
    """

    def __init__(
        self,
        base_url: str,
        model_id: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        system_prompt: Optional[str] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.api_key = api_key
        self.timeout = timeout
        self.system_prompt = system_prompt or (
            "You are a strict JSON classifier. "
            "Classify the math question into one of these topics: "
            "algebra, calculus, discrete, geometry. "
            "Also return difficulty as one of: E, M, H. "
            "Optionally include subtopic, needs_tools (array of short tool names), "
            "confidence (0..1), and notes. "
            "Return ONLY a single JSON object with keys: "
            '{"topic": "...", "difficulty": "...", "subtopic": null | "...", '
            '"needs_tools": [], "confidence": 0.0, "notes": null}.'
        )

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _endpoint(self) -> str:
        return f"{self.base_url}/route"

    def route_batch(self, questions: List[Question]) -> List[RouteRecord]:
        """
        Send all questions in a single batch to the /route endpoint.
        The server expects: {"inputs": [{"qid": "...", "stem": "...", "options": [...]}]}
        And returns: [{"qid": "...", "topic": "...", "difficulty": "...", ...}]
        """
        if not questions:
            return []

        # Build the payload matching the server's RouteRequest schema
        inputs = []
        for q in questions:
            inputs.append({
                "qid": q["qid"],
                "stem": q["stem"],
                "options": q.get("opts", [])
            })

        payload = {"inputs": inputs}

        try:
            r = requests.post(self._endpoint(), headers=self._headers(), json=payload, timeout=self.timeout)
            r.raise_for_status()
            routes_data = r.json()

            # Server returns a list of route objects
            if not isinstance(routes_data, list):
                raise RuntimeError(f"Expected list response from /route, got: {type(routes_data)}")

            # Convert server response to RouteRecord format
            out: List[RouteRecord] = []
            for obj in routes_data:
                topic = _coerce_topic(obj.get("topic"))
                diff = _coerce_difficulty(obj.get("difficulty"))
                needs_tools = obj.get("needs_tools", [])
                if not isinstance(needs_tools, list):
                    needs_tools = []
                needs_tools = [str(t) for t in needs_tools]

                rec: RouteRecord = {
                    "run_id": "",
                    "qid": obj.get("qid", ""),
                    "topic": topic,
                    "subtopic": (str(obj["subtopic"]) if obj.get("subtopic") is not None else None),
                    "difficulty": diff,
                    "needs_tools": needs_tools,
                    "confidence": float(obj.get("confidence", 0.0)),
                    "notes": (str(obj["notes"]) if obj.get("notes") is not None else None),
                    "bucket": f"{topic}:{diff}",
                }
                out.append(rec)

            return out

        except requests.exceptions.RequestException as e:
            # Network/HTTP error - return fallback routes
            import logging
            logging.getLogger(__name__).error(f"Router HTTP error: {e}")
            return [
                {
                    "run_id": "",
                    "qid": q["qid"],
                    "topic": "algebra",
                    "subtopic": None,
                    "difficulty": "M",
                    "needs_tools": [],
                    "confidence": 0.5,
                    "notes": f"http-error: {str(e)}",
                    "bucket": "algebra:M",
                }
                for q in questions
            ]
        except Exception as e:
            # Other errors - return fallback routes
            import logging
            logging.getLogger(__name__).error(f"Router processing error: {e}")
            return [
                {
                    "run_id": "",
                    "qid": q["qid"],
                    "topic": "algebra",
                    "subtopic": None,
                    "difficulty": "M",
                    "needs_tools": [],
                    "confidence": 0.5,
                    "notes": f"processing-error: {str(e)}",
                    "bucket": "algebra:M",
                }
                for q in questions
            ]