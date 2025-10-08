"""
Text normalization utilities - P1 normalization support
(compatible with your earlier text_utils-style helpers)
"""
from __future__ import annotations
import re
from typing import List

FILLER_OPENERS = {"so", "thus", "therefore", "hence", "but", "and"}

def _clean(s: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", s or "").strip()

def phrase_from_question(qtext: str, limit_words: int = 12) -> str:
    """Extract a concise phrase from the question text."""
    s = re.sub(r"^Q\d+\.\s*", "", qtext or "").strip()
    s = re.split(r"\bWhich\s+of\s+the\s+following\b", s, flags=re.I)[0]
    s = _clean(s)
    words = s.split()
    if len(words) > limit_words:
        s = " ".join(words[:limit_words])
    s = s.rstrip(".,;: ")
    return (s + ".") if s else "Concise topic phrase unavailable."

def fix_explain(expl: str, qtext: str) -> str:
    """Normalize short justification text."""
    e = (expl or "").strip()
    e = re.sub(r"^\s*(so|thus|therefore|hence|but|and)[,:\s]+", "", e, flags=re.I).strip()
    e = _clean(e)
    words = e.split()
    if len(words) < 5 or len(words) > 18:
        topic = re.sub(r"^Q\d+\.\s*", "", qtext or "")
        topic = re.split(r"Which of the following", topic, flags=re.I)[0]
        topic = _clean(topic)
        topic = " ".join(topic.split()[:10]) or "the given conditions"
        e = f"Chooses this option because {topic.lower()}."
    elif not e.endswith("."):
        e += "."
    return e

def normalize_question_text(text: str) -> str:
    """Normalize question stem for consistent processing."""
    if not text:
        return ""
    text = re.sub(r"^Q?\d+[\.\:\)\s-]*", "", text, flags=re.I).strip()  # strip leading numbers
    text = _clean(text)
    text = re.sub(r"\s*[\.\:\;\,]\s*$", "", text).strip()
    if text and not text.endswith(('.', '?', '!')):
        text += "."
    return text

def normalize_option_text(option: str) -> str:
    """Normalize option text; strip A/B/C/D or 1/2/3/4 markers."""
    if not option:
        return ""
    option = re.sub(r"^\s*[\(\[]?\s*([1-4ABCDabcd])[\.\)\]]\s*", "", option)  # "A) ", "(3) ", "b. "
    option = _clean(option)
    return option

def detect_question_topics(text: str) -> List[str]:
    """Heuristic topic hints (used later for routing hints or summaries)."""
    topics: List[str] = []
    t = (text or "").lower()
    topic_patterns = {
        "algebra": [r"\b(equation|solve|variable|polynomial|linear|quadratic)\b",
                    r"\b(factor|coefficient|expression|inequality)\b"],
        "calculus": [r"\b(derivative|integral|limit|differential|gradient)\b",
                     r"\b(maxima|minima|optimization|rate|slope)\b"],
        "geometry": [r"\b(triangle|circle|angle|area|perimeter|volume)\b",
                     r"\b(parallel|perpendicular|congruent|similar)\b"],
        "trigonometry": [r"\b(sin|cos|tan|sine|cosine|tangent)\b",
                         r"\b(angle|radian|degree|identity)\b"],
        "statistics": [r"\b(mean|median|mode|variance)\b",
                       r"\b(distribution|sample|population|correlation)\b"],
        "discrete": [r"\b(permutation|combination|graph|set|logic)\b",
                     r"\b(sequence|series|matrix|binary)\b"],
    }
    for topic, patterns in topic_patterns.items():
        if any(re.search(p, t) for p in patterns):
            topics.append(topic)
    return topics or ["unknown"]

def extract_mathematical_expressions(text: str) -> List[str]:
    """Very lightweight math token extractor."""
    expressions: List[str] = []
    patterns = [
        r"[a-zA-Z]\s*[+\-*/=<>]\s*[a-zA-Z0-9]+",
        r"\b\d+\s*[+\-*/]\s*\d+\b",
        r"[a-zA-Z]\^\d+",
        r"√\d+",
        r"\b\d+\.\d+\b",
        r"\b\d+/\d+\b",
    ]
    for pat in patterns:
        expressions.extend(re.findall(pat, text or ""))
    # dedupe
    seen, out = set(), []
    for e in expressions:
        if e not in seen:
            out.append(e)
            seen.add(e)
    return out

def assess_question_difficulty(text: str, options: List[str]) -> str:
    """Quick difficulty heuristic: E/M/H."""
    score = 0
    t = (text or "").lower()
    nwords = len((text or "").split())
    if nwords > 20: score += 1
    if nwords > 35: score += 1
    hard = ["complex", "advanced", "prove", "derive", "optimize",
            "integration", "differentiation", "theorem", "lemma"]
    med  = ["calculate", "determine", "find", "solve", "evaluate",
            "analyze", "compare", "interpret"]
    if any(w in t for w in hard): score += 2
    if any(w in t for w in med):  score += 1
    exprs = extract_mathematical_expressions(text or "")
    if len(exprs) > 3: score += 1
    if any(('^' in e or '√' in e) for e in exprs): score += 1
    avg_opt = (sum(len(o.split()) for o in (options or [])) / max(1, len(options or [])))
    if avg_opt > 5: score += 1
    return "H" if score >= 5 else "M" if score >= 2 else "E"

def generate_question_summary(text: str, options: List[str], max_length: int = 100) -> str:
    """Short summary with optional topic hint."""
    phrase = phrase_from_question(text or "", limit_words=15)
    topics = detect_question_topics(text or "")
    if topics and topics[0] != "unknown":
        hint = f" ({topics[0]})"
        if len(phrase) + len(hint) <= max_length:
            phrase += hint
    return phrase[:max_length]



# # src/p1_ingestion/parsing/cleaners.py
# """
# Text normalization utilities - enhanced version of existing text_utils.py
# Maintains compatibility while adding P1 normalization support
# """

# import re
# from typing import Dict, List, Tuple

# # Keep existing functions from your utils/text_utils.py

# FILLER_OPENERS = {"so", "thus", "therefore", "hence", "but", "and"}


# def _clean(s: str) -> str:
#     """Clean whitespace and normalize text"""
#     return re.sub(r"\s+", " ", s).strip()


# def phrase_from_question(qtext: str, limit_words: int = 12) -> str:
#     """
#     Extract a concise phrase from question text
#     """
#     s = re.sub(r"^Q\d+\.\s*", "", qtext).strip()
#     s = re.split(r"\bWhich\s+of\s+the\s+following\b", s, flags=re.I)[0]
#     s = _clean(s)
    
#     words = s.split()
#     if len(words) > limit_words:
#         s = " ".join(words[:limit_words])
    
#     s = s.rstrip(".,;: ") + "."
#     return s if s else "Concise topic phrase unavailable."


# def fix_explain(expl: str, qtext: str) -> str:
#     """
#     Fix and normalize explanation text
#     """
#     e = (expl or "").strip()
    
#     # Strip filler words
#     e = re.sub(r"^\s*(so|thus|therefore|hence|but|and)[,:\s]+", "", e, flags=re.I).strip()
    
#     # Normalize whitespace and check length
#     e = re.sub(r"\s+", " ", e)
#     words = e.split()
    
#     if len(words) < 5 or len(words) > 18:
#         # Fallback to topic phrase
#         topic = re.sub(r"^Q\d+\.\s*", "", qtext)
#         topic = re.split(r"Which of the following", topic, flags=re.I)[0]
#         topic = re.sub(r"\s+", " ", topic).strip()
#         topic = " ".join(topic.split()[:10]) or "Concise justification"
#         e = f"Chooses this option because {topic.lower()}."
#     else:
#         if not e.endswith("."):
#             e += "."
    
#     return e


# # Enhanced normalization functions for P1

# def normalize_question_text(text: str) -> str:
#     """
#     Normalize question text for consistent processing
#     Enhanced for P1 ingestion
#     """
#     if not text:
#         return ""
    
#     # Remove question numbering patterns
#     text = re.sub(r"^Q\d+[\.\:\s]*", "", text, flags=re.I).strip()
#     text = re.sub(r"^\d+[\.\)\s]+", "", text).strip()
    
#     # Normalize whitespace
#     text = _clean(text)
    
#     # Remove trailing punctuation artifacts
#     text = re.sub(r"\s*[\.\:\;\,]\s*$", "", text).strip()
    
#     # Ensure proper sentence ending
#     if text and not text.endswith(('.', '?', '!')):
#         text += "."
    
#     return text


# def normalize_option_text(option: str) -> str:
#     """
#     Normalize option text for consistent processing
#     """
#     if not option:
#         return ""
    
#     # Remove option numbering
#     option = re.sub(r"^\s*[\(\[]?\s*[1-4A-D][\.\)\]]\s*", "", option, flags=re.I)
    
#     # Clean whitespace
#     option = _clean(option)
    
#     return option


# def detect_question_topics(text: str) -> List[str]:
#     """
#     Detect mathematical topics in question text
#     Enhanced topic detection for routing
#     """
#     topics = []
#     text_lower = text.lower()
    
#     # Topic keyword patterns
#     topic_patterns = {
#         "algebra": [r"\b(equation|solve|variable|polynomial|linear|quadratic)\b",
#                    r"\b(factor|coefficient|expression|inequality)\b"],
#         "calculus": [r"\b(derivative|integral|limit|differential|gradient)\b",
#                     r"\b(maxima|minima|optimization|rate|slope)\b"],
#         "geometry": [r"\b(triangle|circle|angle|area|perimeter|volume)\b",
#                     r"\b(parallel|perpendicular|congruent|similar)\b"],
#         "trigonometry": [r"\b(sin|cos|tan|sine|cosine|tangent)\b",
#                         r"\b(angle|radian|degree|identity)\b"],
#         "statistics": [r"\b(mean|median|mode|probability|variance)\b",
#                       r"\b(distribution|sample|population|correlation)\b"],
#         "discrete": [r"\b(permutation|combination|graph|set|logic)\b",
#                     r"\b(sequence|series|matrix|binary)\b"]
#     }
    
#     for topic, patterns in topic_patterns.items():
#         for pattern in patterns:
#             if re.search(pattern, text_lower):
#                 if topic not in topics:
#                     topics.append(topic)
#                 break
    
#     return topics if topics else ["unknown"]


# def extract_mathematical_expressions(text: str) -> List[str]:
#     """
#     Extract mathematical expressions from question text
#     """
#     expressions = []
    
#     # Common math expression patterns
#     patterns = [
#         r"[a-zA-Z]\s*[+\-*/=<>]\s*[a-zA-Z0-9]+",  # Variable expressions
#         r"\d+\s*[+\-*/]\s*\d+",                     # Numeric expressions
#         r"[a-zA-Z]\^\d+",                           # Powers
#         r"√\d+",                                    # Square roots
#         r"\b\d+\.\d+\b",                           # Decimals
#         r"\b\d+/\d+\b",                            # Fractions
#     ]
    
#     for pattern in patterns:
#         matches = re.findall(pattern, text)
#         expressions.extend(matches)
    
#     return list(set(expressions))  # Remove duplicates


# def assess_question_difficulty(text: str, options: List[str]) -> str:
#     """
#     Assess question difficulty based on text complexity
#     Returns: "E" (Easy), "M" (Medium), "H" (Hard)
#     """
#     # Simple heuristic scoring
#     score = 0
#     text_lower = text.lower()
    
#     # Length factors
#     if len(text.split()) > 20:
#         score += 1
#     if len(text.split()) > 35:
#         score += 1
    
#     # Complexity indicators
#     hard_indicators = [
#         "complex", "advanced", "prove", "derive", "optimize",
#         "integration", "differentiation", "theorem", "lemma"
#     ]
    
#     medium_indicators = [
#         "calculate", "determine", "find", "solve", "evaluate",
#         "analyze", "compare", "interpret"
#     ]
    
#     for indicator in hard_indicators:
#         if indicator in text_lower:
#             score += 2
    
#     for indicator in medium_indicators:
#         if indicator in text_lower:
#             score += 1
    
#     # Mathematical expression complexity
#     expressions = extract_mathematical_expressions(text)
#     if len(expressions) > 3:
#         score += 1
#     if any('^' in expr or '√' in expr for expr in expressions):
#         score += 1
    
#     # Option complexity
#     avg_option_len = sum(len(opt.split()) for opt in options) / len(options) if options else 0
#     if avg_option_len > 5:
#         score += 1
    
#     # Final assessment
#     if score >= 5:
#         return "H"
#     elif score >= 2:
#         return "M"
#     else:
#         return "E"


# def generate_question_summary(text: str, options: List[str], max_length: int = 100) -> str:
#     """
#     Generate a concise summary of the question
#     """
#     # Use the existing phrase extraction as base
#     phrase = phrase_from_question(text, limit_words=15)
    
#     # Add topic hints if possible
#     topics = detect_question_topics(text)
#     if topics and topics[0] != "unknown":
#         topic_hint = f" ({topics[0]})"
#         if len(phrase) + len(topic_hint) <= max_length:
#             phrase += topic_hint
    
#     return phrase[:max_length]