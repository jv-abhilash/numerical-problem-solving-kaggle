# src/utils/io.py
"""
Enhanced I/O utilities - integrated with existing answers_io.py patterns
Maintains compatibility with existing pipeline
"""

import os
import json
import re
import pandas as pd
from typing import Any, Dict, Optional, List, Union
from pathlib import Path

# Keep existing functions from your utils/answers_io.py
def _to_int(x) -> Optional[int]:
    """Convert value to integer, handling various input types"""
    try:
        if x is None: 
            return None
        if isinstance(x, bool): 
            return int(x)
        return int(float(str(x).strip()))
    except Exception:
        return None


def _pick_prob(v: Dict[str, Any], chosen_idx: Optional[int]) -> Optional[float]:
    """Extract probability/confidence from various possible keys"""
    for key in ["prob", "probability", "confidence", "score"]:
        if key in v and isinstance(v[key], (int, float)):
            return float(v[key])
    
    for key in ["probs", "probabilities", "scores", "logits_softmax"]:
        if key in v:
            val = v[key]
            if isinstance(val, dict) and chosen_idx is not None:
                if str(chosen_idx) in val: 
                    return float(val[str(chosen_idx)])
            if isinstance(val, list) and chosen_idx is not None:
                i = chosen_idx - 1
                if 0 <= i < len(val) and isinstance(val[i], (int, float)):
                    return float(val[i])
    return None


def normalize_record(qkey: str, v: Dict[str, Any], qtext: str) -> Dict[str, Any]:
    """
    Normalize a single answer record - enhanced version of existing function
    """
    # Extract question ID
    m = re.match(r"[Qq](\d+)", qkey)
    qid = int(m.group(1)) if m else None

    # Extract option index
    opt_idx = None
    for k in ["option", "option_index", "choice", "selected", "answer_idx", "ans_idx"]:
        if k in v:
            opt_idx = _to_int(v[k])
            break

    # Extract question type/topic
    qtype = v.get("type") or v.get("qtype") or v.get("topic") or ""
    
    # Extract probability/confidence
    prob = _pick_prob(v, opt_idx)
    
    # Extract explanation/reasoning
    explain = v.get("explain") or v.get("reasoning") or v.get("rationale") or ""

    # Handle probability arrays/objects
    probs_json = None
    for k in ["probs", "probabilities", "scores", "logits_softmax"]:
        if k in v:
            try: 
                probs_json = json.dumps(v[k], ensure_ascii=False)
            except Exception: 
                probs_json = str(v[k])
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


def answers_to_csv(answers: Dict[str, Any], qtexts: Dict[str, str], 
                  out_path: Optional[str] = None) -> str:
    """
    Convert answers dictionary to CSV - enhanced version maintaining compatibility
    """
    # Normalize all records
    rows = []
    for k, v in answers.items():
        if isinstance(v, dict):
            record = normalize_record(k, v, qtexts.get(k, ""))
        else:
            record = normalize_record(k, {"value": v}, qtexts.get(k, ""))
        rows.append(record)
    
    # Create DataFrame and sort by question ID
    df = pd.DataFrame(rows).sort_values("qid").reset_index(drop=True)
    
    # Determine output path
    if out_path is None:
        if os.path.exists("/kaggle/working"):
            out_path = "/kaggle/working/answers_parsed.csv"
        else:
            out_path = "./answers_parsed.csv"
    
    # Save to CSV
    df.to_csv(out_path, index=False)
    return out_path


# Enhanced I/O functions for P1 integration

def load_text_file_robust(file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
    """
    Load text file with robust encoding handling
    Enhanced version for P1 ingestion
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Try multiple encodings
    encodings_to_try = [encoding, 'utf-8', 'latin-1', 'cp1252']
    
    for enc in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                content = f.read()
            return content
        except UnicodeDecodeError:
            continue
    
    raise ValueError(f"Could not read {file_path} with any encoding: {encodings_to_try}")


def save_questions_jsonl(qtexts: Dict[str, str], options: Dict[str, List[str]], 
                        figures: Dict[str, bool], out_path: str) -> None:
    """
    Save questions in JSONL format for P1 output
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, 'w', encoding='utf-8') as f:
        for qkey in sorted(qtexts.keys(), key=lambda x: int(x[1:]) if x[1:].isdigit() else 0):
            record = {
                "qkey": qkey,
                "qid": int(qkey[1:]) if qkey[1:].isdigit() else None,
                "question": qtexts[qkey],
                "options": options.get(qkey, []),
                "has_figure": figures.get(qkey, False),
                "source": str(out_path)
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')


def load_answer_key_flexible(file_path: Union[str, Path]) -> Dict[str, int]:
    """
    Load answer key with flexible column detection
    Enhanced version for P1 evaluation
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Answer key not found: {file_path}")
    
    df = pd.read_csv(file_path)
    
    # Flexible column name detection
    qid_col = None
    answer_col = None
    
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower in ['qid', 'question_id', 'id', 'question']:
            qid_col = col
        elif col_lower in ['answer', 'correct_answer', 'correct_option', 'option', 'solution', 'option_index']:
            answer_col = col
    
    if qid_col is None:
        raise ValueError(f"Could not find question ID column in {file_path}. Available: {list(df.columns)}")
    
    if answer_col is None:
        raise ValueError(f"Could not find answer column in {file_path}. Available: {list(df.columns)}")
    
    # Convert to dictionary
    answer_key = {}
    for _, row in df.iterrows():
        qid = str(row[qid_col]).strip()
        answer = row[answer_col]
        
        # Convert answer to integer (1-4 for A-D)
        if isinstance(answer, str):
            answer = answer.strip().upper()
            if answer in ['A', 'B', 'C', 'D']:
                answer = ord(answer) - ord('A') + 1  # A=1, B=2, C=3, D=4
            else:
                try:
                    answer = int(answer)
                except ValueError:
                    continue
        
        if isinstance(answer, int) and 1 <= answer <= 4:
            answer_key[qid] = answer
    
    return answer_key


def save_predictions_enhanced(answers: Dict[str, Any], qtexts: Dict[str, str],
                            question_hashes: Dict[str, str], 
                            out_path: str) -> str:
    """
    Enhanced version of answers_to_csv with additional P1 metadata
    """
    rows = []
    
    for k, v in answers.items():
        if isinstance(v, dict):
            record = normalize_record(k, v, qtexts.get(k, ""))
        else:
            record = normalize_record(k, {"value": v}, qtexts.get(k, ""))
        
        # Add P1 metadata
        record["question_text"] = qtexts.get(k, "")
        record["question_hash"] = question_hashes.get(k, "")
        
        rows.append(record)
    
    df = pd.DataFrame(rows).sort_values("qid").reset_index(drop=True)
    df.to_csv(out_path, index=False)
    return out_path


# Validation utilities for P1

def validate_question_structure(qtexts: Dict[str, str], options: Dict[str, List[str]]) -> List[str]:
    """
    Validate question structure and return list of issues
    """
    issues = []
    
    for qkey, qtext in qtexts.items():
        if not qtext.strip():
            issues.append(f"{qkey}: Empty question text")
        
        if qkey not in options:
            issues.append(f"{qkey}: Missing options")
            continue
            
        opts = options[qkey]
        if len(opts) != 4:
            issues.append(f"{qkey}: Has {len(opts)} options instead of 4")
        
        if any(not opt.strip() for opt in opts):
            issues.append(f"{qkey}: Has empty options")
        
        # Check for very short questions (might be parsing errors)
        if len(qtext.split()) < 3:
            issues.append(f"{qkey}: Very short question text (possible parsing error)")
    
    return issues


def generate_parsing_stats(qtexts: Dict[str, str], options: Dict[str, List[str]], 
                          figures: Dict[str, bool]) -> Dict[str, Any]:
    """
    Generate statistics about parsing results
    """
    stats = {
        "total_questions": len(qtexts),
        "questions_with_4_options": sum(1 for opts in options.values() if len(opts) == 4),
        "questions_with_figures": sum(figures.values()),
        "average_question_length": sum(len(q.split()) for q in qtexts.values()) / len(qtexts) if qtexts else 0,
        "average_option_length": 0
    }
    
    # Calculate average option length
    all_options = []
    for opts in options.values():
        all_options.extend(opts)
    
    if all_options:
        stats["average_option_length"] = sum(len(opt.split()) for opt in all_options) / len(all_options)
    
    return stats


# Cache utilities

def get_cache_path(base_dir: Union[str, Path], cache_key: str, extension: str = 'json') -> Path:
    """Generate cache file path from key"""
    base_dir = Path(base_dir)
    cache_dir = base_dir / '.cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Create safe filename
    safe_key = "".join(c if c.isalnum() or c in '-_' else '_' for c in cache_key)
    return cache_dir / f"{safe_key}.{extension}"


def load_cached_data(cache_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Load data from cache if valid"""
    cache_path = Path(cache_path)
    
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def save_cached_data(data: Dict[str, Any], cache_path: Union[str, Path]) -> None:
    """Save data to cache"""
    try:
        cache_path = Path(cache_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # Fail silently for cache operations