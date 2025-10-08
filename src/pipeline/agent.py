# router/solver.py
from typing import Dict, Any, List, Tuple, Optional
import os, json
from .planner import expected_qkeys_from_prompt, parse_questions, render_batch_block
from src.utils.schema import extract_between_markers, best_json_candidate
from .normalize import fix_explain
from .router import route_question
from src.models.solver_llm import call_model  # must support model_id=... kw or your flexible (*args) version

DEFAULT_MODEL_ID = os.getenv("FALLBACK_MODEL_ID", os.getenv("DEFAULT_MODEL_ID", "")) or \
                   "Qwen/Qwen3-235B-A22B-Thinking-2507"

SYSTEM = (
    "You are a strict function that answers MCQs.\n"
    "Return ONE JSON object whose keys are exactly the q-keys shown in the user message.\n"
    "For each key return: {\"option\": <0|1|2|3|4>, \"explain\": \"<short justification, 8–16 words>\"}.\n"
    "- 'option' is the OPTION NUMBER (1..4). Use 0 if unsure or none match.\n"
    "- 'explain' must be one concise, grammatical sentence in plain English.\n"
    "- Avoid filler (So/Thus/Therefore/Hence). Avoid symbols and LaTeX; use words.\n"
    "- Do NOT echo questions or options. Output ONLY JSON between <BEGIN_JSON> and <END_JSON>.\n"
)

def _sanitize_merge(sub_keys: List[str],
                    raw_text: str,
                    qtexts: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """Parse model output -> dict, then sanitize option/explain using imported helpers."""
    obj: Dict[str, Any] = {}
    js = extract_between_markers(raw_text)
    if js:
        try:
            parsed = json.loads(js)
            if isinstance(parsed, dict):
                obj = parsed
        except Exception:
            obj = {}

    if not obj:
        obj = best_json_candidate(raw_text, sub_keys) or {}

    merged: Dict[str, Dict[str, Any]] = {}
    for k in sub_keys:
        v = obj.get(k, {}) or {}
        opt = v.get("option", 0)
        try:
            opt = int(opt)
        except Exception:
            opt = 0
        if not (0 <= opt <= 4):
            opt = 0

        expl_in = (v.get("explain") if isinstance(v, dict) else "") or ""
        # fix_explain is a 2-arg function: (expl, qtext)
        expl = fix_explain(expl_in, qtexts.get(k, ""))

        # carry any useful meta if present
        carried = {}
        for src in ("type","qtype","topic","prob","probability","confidence",
                    "probs","probabilities","scores","logits_softmax","reasoning","rationale"):
            if isinstance(v, dict) and src in v:
                carried[src] = v[src]

        merged[k] = {"option": opt, "explain": expl, **carried}
    return merged

def solve_with_router(
    USER_PROMPT: str,
    batch_size: int = 20,
    model_map: Optional[Dict[str, str]] = None,  # reserved for future multi-LLM
    use_langchain_router: bool = True,
    prefer_regex_on_conflict: bool = True,
    temperature: float = 0.0,
    max_tokens: int = 20000,
    verbose: bool = True,
) -> Tuple[Dict[str, Dict[str, object]], Dict[str, str]]:
    """
    Single-LLM flow:
      1) Parse the paper (qtexts/options + expected q-keys).
      2) Route each question to a one-word label (LLM-first with regex correction).
      3) Solve per label in batches using the SAME fallback LLM for all buckets.
      4) Sanitize & merge answers.
    """
    qtexts, opts = parse_questions(USER_PROMPT)
    expected = expected_qkeys_from_prompt(USER_PROMPT)
    if not expected:
        raise ValueError("No questions detected. Ensure Qn headings with options (1)..(4).")

    # Router
    routes: Dict[str, str] = {}
    for qk in expected:
        routes[qk] = route_question(
            qtexts[qk],
            use_langchain_router=use_langchain_router,
            prefer_regex_on_conflict=prefer_regex_on_conflict
        )

    # Single-LLM for all buckets
    fallback_model = os.getenv("FALLBACK_MODEL_ID", DEFAULT_MODEL_ID)

    # Group by label (kept for analysis)
    buckets: Dict[str, List[str]] = {}
    for qk, label in routes.items():
        buckets.setdefault(label, []).append(qk)

    merged: Dict[str, Dict[str, Any]] = {}

    # Solve per bucket, batched
    for label, keys in buckets.items():
        model_id = fallback_model
        for i in range(0, len(keys), batch_size):
            sub = keys[i:i+batch_size]
            user_batch = render_batch_block(qtexts, opts, sub)

            raw = call_model(
                SYSTEM,
                user_batch,
                model_id=model_id,       # your call_model must accept this kw (or use your flexible version)
                max_tokens=max_tokens,
                temperature=temperature,
            )

            merged.update(_sanitize_merge(sub, raw, qtexts))

            if verbose:
                answered = sum(1 for k in sub if merged.get(k, {}).get("option", 0) != 0)
                print(f"[{label} → {model_id}] batch {i//batch_size+1}: answered {answered}/{len(sub)}.")

    # Ensure every expected key exists
    for k in expected:
        if k not in merged:
            merged[k] = {"option": 0, "explain": fix_explain("", qtexts.get(k, ""))}

    return merged, qtexts

def solve_batches(USER_PROMPT: str, batch_size: int = 20) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    """Simple single-model baseline (ignores routing)."""
    qtexts, opts = parse_questions(USER_PROMPT)
    expected = expected_qkeys_from_prompt(USER_PROMPT)
    if not expected:
        raise ValueError("No questions detected. Ensure Qn headings with options (1)..(4).")

    merged: Dict[str, Dict[str, Any]] = {}
    fallback_model = os.getenv("FALLBACK_MODEL_ID", DEFAULT_MODEL_ID)

    for i in range(0, len(expected), batch_size):
        sub = expected[i:i+batch_size]
        user_batch = render_batch_block(qtexts, opts, sub)

        raw = call_model(
            SYSTEM,
            user_batch,
            model_id=fallback_model,
            max_tokens=20000,
            temperature=0.0,
        )

        merged.update(_sanitize_merge(sub, raw, qtexts))
        answered = sum(1 for k in sub if merged[k]["option"] != 0)
        print(f"Batch {i//batch_size+1}/{(len(expected)+batch_size-1)//batch_size} — answered {answered}/{len(sub)}.")

    return merged, qtexts