# utils/text_utils.py
import re
from typing import Dict

FILLER_OPENERS = {"so", "thus", "therefore", "hence", "but", "and"}

def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def phrase_from_question(qtext: str, limit_words: int = 12) -> str:
    s = re.sub(r"^Q\d+\.\s*", "", qtext).strip()
    s = re.split(r"\bWhich\s+of\s+the\s+following\b", s, flags=re.I)[0]
    s = _clean(s)
    words = s.split()
    if len(words) > limit_words:
        s = " ".join(words[:limit_words])
    s = s.rstrip(".,;: ") + "."
    return s if s else "Concise topic phrase unavailable."

def fix_explain(expl: str, qtext: str) -> str:
    e = (expl or "").strip()
    # strip filler
    e = re.sub(r"^\s*(so|thus|therefore|hence|but|and)[,:\s]+", "", e, flags=re.I).strip()
    # normalize whitespace and cap length
    e = re.sub(r"\s+", " ", e)
    words = e.split()
    if len(words) < 5 or len(words) > 18:
        # fallback to topic phrase
        topic = re.sub(r"^Q\d+\.\s*", "", qtext)
        topic = re.split(r"Which of the following", topic, flags=re.I)[0]
        topic = re.sub(r"\s+", " ", topic).strip()
        topic = " ".join(topic.split()[:10]) or "Concise justification"
        e = f"Chooses this option because {topic.lower()}."
    else:
        if not e.endswith("."):
            e += "."
    return e
