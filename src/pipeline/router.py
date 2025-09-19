# router/llm_router.py
"""
One-word math router: LLM FIRST (local 7B on GPU), regex as corrective BACKUP.

Labels (single words):
algebra, integration, differentiation, limits, trig,
geometry, vectors, probability, sets, lpp, complex, stats, diffeq

Rules:
- "linear algebra" → "vectors"
- All integrals (definite/indefinite/area) → "integration"
- If LLM and regex disagree, prefer regex (correction).
- If LLM missing, use regex; else default to "algebra".

Backends:
  - Local HF transformers (Qwen 7B) via models.local_qwen.chat (preferred)
  - If local import fails, fall back to remote HF client models.qwen_client.call_model
"""

from __future__ import annotations
import os, re
from typing import Dict, Optional

# --- One-word labels (keep this list tight)
LABELS = [
    "algebra", "integration", "differentiation", "limits", "trig",
    "geometry", "vectors", "probability", "sets", "lpp",
    "complex", "stats", "diffeq"
]

# --- Regex rules ---
ROUTE_TABLE: Dict[str, str] = {
    "vectors": r"\b(matrix|matrices|det(?:erminant)?|adj(?:oint)?|inverse|transpose|rank|eigen|minor|cofactor|A\^|\[\[|3×3|3x3|order\s+\d+\s*×\s*\d+|direction\s+ratios?|direction\s+cosines?)\b|=\s*\(x[-+].*?=|yz-?plane",
    "integration": r"\b∫|integral\b|dx\b|area\s+bounded|area\s+of\s+region|evaluate\s+the\s+integral",
    "differentiation": r"\bdy/dx|derivative|differentiat|increasing\b|\bdecreasing\b|log\(?x\)?",
    "limits": r"\blim\s*[_({]|\b(?:x|t|h)\s*→|->\s*0|\bas\s*(?:x|t|h)\s*→",
    "trig": r"\b(?:sin|cos|tan|cot|sec|cosec)\b|°|π",
    "geometry": r"\b(diagonals?|octagon|polygon|latus\s*rectum|locus|distance\s+from|coordinate\s+geometry)\b",
    "probability": r"\bprobabilit|P\(|mutually\s+exclusive|independent\s+events|conditional\s+prob|Bayes|binomial\s+distribution|random\s+variable|die\b|dice\b|temple\b",
    "sets": r"\bset\b|A\s*∪\s*B|A\s*∩\s*B|domain\b|codomain\b|range\b|greatest\s+integer|floor\b|ceiling\b|⌊|⌈",
    "lpp": r"\b(LPP|linear\s*programming|objective\s+function|constraints?|maximize|minimize)\b",
    "complex": r"\bcomplex\b|[|]Z1|Z2[|]|[|]Z[|]|\barg\s*\(|\bre\(|\bim\(",
    "stats": r"\bmean\s+deviation|variance|standard\s+deviation|sd\b|median\b|mode\b|quartiles?\b|percentiles?\b",
    "algebra": r"\b(binomial|expansion\b|GP\b|AP\b|geometric\s+progression|inequalit|equation\b|equations\b|roots?\b|factor(?:isation)?|common\s+set\s+of\s+solution)\b",
    "diffeq": r"\bdifferential\s+equation|order\s+and\s+degree\b|dy/dx\s*=.*y|y'\s*=|y''\s*=",
}

# Compile once (fast & case-insensitive)
COMPILED_PATTERNS: Dict[str, re.Pattern] = {
    label: re.compile(pat, flags=re.I)
    for label, pat in ROUTE_TABLE.items()
}

def _rule_route(text: str) -> Optional[str]:
    t = text.strip()
    for label, rx in COMPILED_PATTERNS.items():
        if rx.search(t):
            return label
    return None

ROUTER_MODEL_DEFAULT = "Qwen/Qwen2.5-Math-7B-Instruct"

def _local_router_label(text: str) -> Optional[str]:
    """
    Run the 7B router locally on GPU if models.local_qwen is available.
    Falls back to remote HF client if local import fails.
    """
    system_template = (
        "You are a classifier. Return exactly one label from this list:\n"
        f"{', '.join(LABELS)}\n"
        "- Map 'linear algebra' to 'vectors'.\n"
        "- Use 'integration' for any integral problems.\n"
        "Output ONLY the label."
    )
    user = f"Question:\n{text}\n\nLabel:"
    router_model = os.getenv("ROUTER_MODEL_ID", ROUTER_MODEL_DEFAULT)

    # Try local first (GPU)
    try:
        from models.router_llm import chat as local_chat
        out = local_chat(
            model_id=router_model,
            system=system_template,
            user=user,
            max_new_tokens=8,
            temperature=0.0,
        ).strip().lower()
        out = re.sub(r"[^a-z]", "", out)
        return out or None
    except Exception:
        pass

    # Fallback: remote HF client (no GPU download)
    try:
        from models.solver_llm import call_model  # must support model_id=...
        out = call_model(
            system_template,
            user,
            model_id=router_model,
            max_tokens=8,
            temperature=0.0,
        ).strip().lower()
        out = re.sub(r"[^a-z]", "", out)
        return out or None
    except Exception:
        return None

def _normalize_label(lbl: Optional[str]) -> str:
    if not lbl:
        return "algebra"
    s = re.sub(r"[^a-z]", "", lbl.lower())
    synonyms = {
        "linearanalgebra": "vectors",
        "matrix": "vectors", "matrices": "vectors", "determinant": "vectors",
        "integrationdefinite": "integration", "integrationindefinite": "integration",
        "differentialequations": "diffeq",
        "prob": "probability",
        "statistics": "stats", "stat": "stats",
        "trigonometry": "trig",
        "limit": "limits",
        "vector": "vectors",
        "settheory": "sets",
        "complexnumbers": "complex",
    }
    s = synonyms.get(s, s)
    return s if s in LABELS else "algebra"

def route_question(
    text: str,
    use_langchain_router: bool = False,      # we ignore LangChain/OpenAI path
    prefer_regex_on_conflict: bool = True,
    debug: bool = False,
) -> str:
    """
    LLM-first routing with regex correction.
    Uses local 7B (GPU) if available; otherwise remote HF client.
    """
    llm_raw = _local_router_label(text)
    llm_label = _normalize_label(llm_raw)

    rule_raw = _rule_route(text)
    rule_label = _normalize_label(rule_raw)

    if llm_raw:
        chosen = rule_label if (prefer_regex_on_conflict and rule_raw and rule_label != llm_label) else llm_label
    else:
        chosen = rule_label if rule_raw else "algebra"

    if debug:
        print(f"[ROUTE] LLM={llm_label or None} | REGEX={rule_label or None} | CHOSEN={chosen}")
    return chosen

def route_questions_bulk(qtexts: Dict[str, str], **kwargs) -> Dict[str, str]:
    return {k: route_question(v, **kwargs) for k, v in qtexts.items()}