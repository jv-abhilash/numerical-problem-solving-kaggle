from __future__ import annotations
from typing import List
from src.shared.schema import Question


def validate_questions(questions: List[Question]) -> List[Question]:
    """
    Basic sanity checks and filtering. In KCET style, we at least require a stem.
    """
    cleaned: List[Question] = []
    for q in questions:
        stem_ok = bool(q["stem"].strip())
        if not stem_ok:
            # keep but mark as no-stem? For now, filter it out:
            continue

        # Option count bounds
        if len(q["opts"]) > 4:
            q["opts"] = q["opts"][:4]

        cleaned.append(q)
    return cleaned
