from __future__ import annotations
from typing import TypedDict, List, Dict, Literal


# ---------- Core, stable contracts (used by all phases) ----------

class Question(TypedDict):
    qid: str                 # "Q1", "KCET-2019-Q12", etc. (string avoids int/str mismatches)
    raw: str                 # original text block (stem + options)
    stem: str                # extracted question text (options removed)
    latex: str               # LaTeX-normalized ("" if N/A)
    opts: List[str]          # 0..4 options; empty if no options
    has_options: bool        # derived convenience flag


class RoutedQuestion(TypedDict):
    qid: str
    topic: Literal[
        "algebra","calc","geometry","trig","prob","stats",
        "sets","vectors","lpp","complex","limits","integration","differentiation"
    ]
    difficulty: Literal["EASY","MEDIUM","HARD"]
    route: Literal["LLM_SOLVER","SYMPY_TOOL","HYBRID"]


class Plan(TypedDict):
    qid: str
    steps: List[str]
    budget: Dict[str, int]          # {"tokens": 512, "calls": 2}
    tool_hints: List[str]


class RawAnswer(TypedDict):
    qid: str
    work: str
    answer_text: str
    option_index: int               # 0..3 or -1 if N/A
    used_tools: List[str]
    latency_ms: int


class VerifiedAnswer(TypedDict):
    qid: str
    is_consistent: bool
    confidence: float
    final_option_index: int
    notes: str


class EvalReport(TypedDict):
    accuracy: float
    per_topic: Dict[str, float]
    per_difficulty: Dict[str, float]
    confusion: Dict[str, Dict[str, int]]






# # src/utils/schema.py
# """
# JSON parsing utilities - enhanced version of existing json_tools.py
# Maintains compatibility while adding P1 schema support
# """

# import re
# import json
# from typing import Any, Dict, List, Optional

# # Keep existing functions from your utils/json_tools.py

# def strip_think(text: str) -> str:
#     """Remove thinking blocks from LLM output"""
#     return re.sub(r"<think>.*?</think>", "", text, flags=re.S|re.I)


# def extract_between_markers(text: str, start="<BEGIN_JSON>", end="<END_JSON>") -> Optional[str]:
#     """
#     Extract JSON between markers - works with or without end marker
#     (since we use stop tokens)
#     """
#     t = strip_think(text)
    
#     # Try with both markers
#     m = re.search(re.escape(start) + r"\s*(\{.*?\})\s*" + re.escape(end), t, flags=re.S)
#     if m:
#         return m.group(1)
    
#     # Try with just start marker
#     m2 = re.search(re.escape(start) + r"\s*(\{.*)", t, flags=re.S)
#     if m2:
#         block = m2.group(1)
#         depth = 0
#         last_close = -1
        
#         for i, ch in enumerate(block):
#             if ch == "{": 
#                 depth += 1
#             elif ch == "}":
#                 depth -= 1
#                 if depth == 0: 
#                     last_close = i
        
#         if last_close != -1:
#             return block[:last_close + 1].strip()
    
#     return None


# def brace_scan_candidates(text: str) -> List[str]:
#     """
#     Scan text for JSON-like brace blocks
#     """
#     t = strip_think(text)
#     blocks = []
#     depth = 0
#     start = None
    
#     for i, ch in enumerate(t):
#         if ch == "{":
#             if depth == 0: 
#                 start = i
#             depth += 1
#         elif ch == "}":
#             if depth > 0:
#                 depth -= 1
#                 if depth == 0 and start is not None:
#                     blocks.append(t[start:i+1])
#                     start = None
    
#     return blocks


# def try_json_loads(s: str) -> Optional[Dict[str, Any]]:
#     """
#     Try to parse JSON string, return dict if successful
#     """
#     try:
#         obj = json.loads(s)
#         return obj if isinstance(obj, dict) else None
#     except Exception:
#         return None


# def best_json_candidate(text: str, expected_keys: List[str]) -> Optional[Dict[str, Any]]:
#     """
#     Find the best JSON candidate based on expected keys overlap
#     """
#     best = None
#     best_overlap = -1
    
#     for cand in brace_scan_candidates(text):
#         obj = try_json_loads(cand)
#         if not obj: 
#             continue
        
#         # Check if all keys match question pattern (q1, q2, etc.)
#         if not all(re.fullmatch(r"q\d+", k) for k in obj.keys()):
#             continue
        
#         # Calculate overlap with expected keys
#         overlap = len(set(obj.keys()) & set(expected_keys))
#         if overlap > best_overlap:
#             best = obj
#             best_overlap = overlap
    
#     return best


# # Enhanced schema utilities for P1 integration

# def validate_question_dict(question_dict: Dict[str, Any]) -> List[str]:
#     """
#     Validate a question dictionary structure
#     Returns list of validation errors
#     """
#     errors = []
    
#     required_fields = ["qid", "question", "options"]
#     for field in required_fields:
#         if field not in question_dict:
#             errors.append(f"Missing required field: {field}")
    
#     # Validate options structure
#     if "options" in question_dict:
#         options = question_dict["options"]
#         if not isinstance(options, list):
#             errors.append("Options must be a list")
#         elif len(options) != 4:
#             errors.append(f"Expected 4 options, got {len(options)}")
#         elif any(not isinstance(opt, str) or not opt.strip() for opt in options):
#             errors.append("All options must be non-empty strings")
    
#     # Validate qid
#     if "qid" in question_dict:
#         qid = question_dict["qid"]
#         if not isinstance(qid, int) or qid <= 0:
#             errors.append("qid must be a positive integer")
    
#     return errors


# def normalize_question_dict(raw_dict: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Normalize a question dictionary to standard format
#     """
#     normalized = {}
    
#     # Handle qid variations
#     for key in ["qid", "question_id", "id", "q_id"]:
#         if key in raw_dict:
#             try:
#                 normalized["qid"] = int(raw_dict[key])
#                 break
#             except (ValueError, TypeError):
#                 continue
    
#     # Handle question text variations
#     for key in ["question", "question_text", "text", "problem"]:
#         if key in raw_dict and raw_dict[key]:
#             normalized["question"] = str(raw_dict[key]).strip()
#             break
    
#     # Handle options variations
#     for key in ["options", "choices", "answers", "alternatives"]:
#         if key in raw_dict:
#             opts = raw_dict[key]
#             if isinstance(opts, list):
#                 normalized["options"] = [str(opt).strip() for opt in opts]
#                 break
    
#     # Handle boolean fields
#     normalized["has_figure"] = bool(raw_dict.get("has_figure", False))
    
#     # Handle metadata
#     if "metadata" in raw_dict and isinstance(raw_dict["metadata"], dict):
#         normalized["metadata"] = raw_dict["metadata"]
    
#     return normalized


# def extract_questions_from_llm_response(text: str, expected_questions: List[str]) -> Dict[str, Dict[str, Any]]:
#     """
#     Extract question answers from LLM response text
#     Enhanced version for P1 integration
#     """
#     # Try JSON extraction first
#     json_block = extract_between_markers(text)
#     if json_block:
#         parsed = try_json_loads(json_block)
#         if parsed and all(re.fullmatch(r"q\d+", k) for k in parsed.keys()):
#             return parsed
    
#     # Fallback to best candidate search
#     best_candidate = best_json_candidate(text, expected_questions)
#     if best_candidate:
#         return best_candidate
    
#     return {}


# # Data structures for P1 pipeline

# class QuestionFormat:
#     """Standard question format definitions"""
    
#     @staticmethod
#     def validate_qkey(qkey: str) -> bool:
#         """Validate question key format (q1, q2, etc.)"""
#         return bool(re.match(r"^q\d+$", qkey))
    
#     @staticmethod
#     def qkey_to_qid(qkey: str) -> Optional[int]:
#         """Convert qkey (q1) to qid (1)"""
#         match = re.match(r"^q(\d+)$", qkey)
#         return int(match.group(1)) if match else None
    
#     @staticmethod
#     def qid_to_qkey(qid: int) -> str:
#         """Convert qid (1) to qkey (q1)"""
#         return f"q{qid}"
    
#     @staticmethod
#     def normalize_option_index(option: Any) -> Optional[int]:
#         """Normalize option to 1-4 index"""
#         if isinstance(option, int) and 1 <= option <= 4:
#             return option
        
#         if isinstance(option, str):
#             option = option.strip().upper()
#             if option in ['A', 'B', 'C', 'D']:
#                 return ord(option) - ord('A') + 1
#             try:
#                 opt_int = int(option)
#                 return opt_int if 1 <= opt_int <= 4 else None
#             except ValueError:
#                 pass
        
#         return None


# # Configuration schemas for pipeline

# class PipelineConfig:
#     """Pipeline configuration management"""
    
#     def __init__(self, config_dict: Dict[str, Any]):
#         self.config = config_dict
    
#     def get(self, key: str, default: Any = None) -> Any:
#         """Get configuration value with dot notation support"""
#         keys = key.split('.')
#         value = self.config
        
#         for k in keys:
#             if isinstance(value, dict) and k in value:
#                 value = value[k]
#             else:
#                 return default
        
#         return value
    
#     def set(self, key: str, value: Any) -> None:
#         """Set configuration value with dot notation support"""
#         keys = key.split('.')
#         config = self.config
        
#         for k in keys[:-1]:
#             if k not in config:
#                 config[k] = {}
#             config = config[k]
        
#         config[keys[-1]] = value
    
#     @classmethod
#     def default_config(cls) -> 'PipelineConfig':
#         """Create default pipeline configuration"""
#         return cls({
#             "ingestion": {
#                 "use_enhanced_parser": True,
#                 "cache_enabled": True,
#                 "validate_questions": True
#             },
#             "router": {
#                 "use_langchain": False,
#                 "prefer_regex_on_conflict": True,
#                 "batch_size": 20
#             },
#             "solver": {
#                 "temperature": 0.0,
#                 "max_tokens": 20000,
#                 "timeout_seconds": 60,
#                 "max_attempts": 3
#             },
#             "output": {
#                 "predictions_file": "data/model_preds.csv",
#                 "output_dir": "data",
#                 "save_intermediate": True
#             }
#         })