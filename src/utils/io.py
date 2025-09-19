# utils/answers_io.py
import os, json, re
from typing import Any, Dict, Optional, List
import pandas as pd

def _to_int(x) -> Optional[int]:
    try:
        if x is None: return None
        if isinstance(x, bool): return int(x)
        return int(float(str(x).strip()))
    except Exception:
        return None

def _pick_prob(v: Dict[str, Any], chosen_idx: Optional[int]) -> Optional[float]:
    for key in ["prob", "probability", "confidence", "score"]:
        if key in v and isinstance(v[key], (int, float)):
            return float(v[key])
    for key in ["probs", "probabilities", "scores", "logits_softmax"]:
        if key in v:
            val = v[key]
            if isinstance(val, dict) and chosen_idx is not None:
                if str(chosen_idx) in val: return float(val[str(chosen_idx)])
            if isinstance(val, list) and chosen_idx is not None:
                i = chosen_idx - 1
                if 0 <= i < len(val) and isinstance(val[i], (int, float)):
                    return float(val[i])
    return None

def normalize_record(qkey: str, v: Dict[str, Any], qtext: str) -> Dict[str, Any]:
    m = re.match(r"[Qq](\d+)", qkey)
    qid = int(m.group(1)) if m else None

    opt_idx = None
    for k in ["option", "option_index", "choice", "selected", "answer_idx", "ans_idx"]:
        if k in v:
            opt_idx = _to_int(v[k]); break

    qtype = v.get("type") or v.get("qtype") or v.get("topic") or ""
    prob  = _pick_prob(v, opt_idx)
    explain = v.get("explain") or v.get("reasoning") or v.get("rationale") or ""

    probs_json = None
    for k in ["probs", "probabilities", "scores", "logits_softmax"]:
        if k in v:
            try: probs_json = json.dumps(v[k], ensure_ascii=False)
            except Exception: probs_json = str(v[k])
            break

    return {
        "qid": qid,
        "option_index": opt_idx,
        "qtype": qtype,
        "probability": prob,
        "explanation": explain,
        "probs_json": probs_json,
        "raw": json.dumps(v, ensure_ascii=False)
    }

def answers_to_csv(answers: Dict[str, Any], qtexts: Dict[str, str], out_path: Optional[str]=None) -> str:
    rows = [normalize_record(k, v if isinstance(v, dict) else {"value": v}, qtexts.get(k, "")) for k, v in answers.items()]
    df = pd.DataFrame(rows).sort_values("qid").reset_index(drop=True)
    if out_path is None:
        out_path = "/kaggle/working/answers_parsed.csv" if os.path.exists("/kaggle/working") else "./answers_parsed.csv"
    df.to_csv(out_path, index=False)
    return out_path
