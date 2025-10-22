# src/p2_routing/classification/rules.py
from __future__ import annotations
import re
from typing import Optional, Dict, Pattern
from src.storage.interfaces import Topic

# Fine-grained cues → umbrella topics (must be one of: algebra|calculus|discrete|geometry)
_FINE_TO_UMBRELLA: Dict[str, Topic] = {
    # calculus bucket
    "trigonometry": "calculus", "trig": "calculus",
    "integration": "calculus", "differentiation": "calculus", "limits": "calculus",

    # algebra bucket
    "vectors": "algebra", "complex": "algebra",

    # discrete bucket
    "probability": "discrete", "prob": "discrete",
    "stats": "discrete", "stat": "discrete", "statistics": "discrete",
    "sets": "discrete", "lpp": "discrete",
}

# Primary regex patterns per 4-topic taxonomy
TOPIC_REGEX: Dict[Topic, Pattern[str]] = {
    "calculus": re.compile(r"\b(∫|integral|differentiat|derivative|dy/dx|limit|lim\s*[_({])\b", re.I),
    "geometry": re.compile(r"\b(triangle|circle|polygon|octagon|locus|coordinate\s+geometry|distance\s+from)\b", re.I),
    "discrete": re.compile(r"\b(probabilit|combination|permutation|binomial|set\b|∪|∩|graph\s+theory|LP|LPP)\b", re.I),
    "algebra":  re.compile(r"\b(equation|inequalit|polynomial|roots?\b|factor|AP\b|GP\b|expansion)\b", re.I),
}

def normalize_topic(raw: Optional[str]) -> Topic:
    """
    Normalize any raw/fine-grained label to one of the 4 Topics.
    Default to 'algebra' if unknown.
    """
    s = (raw or "").strip().lower()
    if s in _FINE_TO_UMBRELLA:
        return _FINE_TO_UMBRELLA[s]
    # s is guaranteed to be one of the valid Topic literals here
    if s in ("algebra", "calculus", "geometry", "discrete"):
        return s  # type: ignore[return-value]
    return "algebra"       # safe default since 'mixed' is not in the schema

def rule_route(text: str) -> Topic:
    """
    Regex-first routing to one of the 4 Topics.
    Falls back to 'algebra' if no pattern matches.
    """
    t = (text or "")
    for topic, rx in TOPIC_REGEX.items():
        if rx.search(t):
            return topic
    return "algebra"