# router/prompt_router.py
import re
from typing import Dict, List

def _clean(s: str) -> str:
    import re
    return re.sub(r"\s+", " ", s).strip()

def expected_qkeys_from_prompt(prompt: str) -> List[str]:
    nums = sorted({int(m.group(1)) for m in re.finditer(r"\bQ\s*([0-9]+)\s*[\.:]", prompt, flags=re.I)})
    return [f"q{n}" for n in nums]

def parse_questions(prompt: str):
    """Return (question_texts, options_by_q)."""
    question_texts: Dict[str, str] = {}
    options_by_q: Dict[str, List[str]] = {}

    anchors = list(re.finditer(r"(Q(?P<n>\d+)\s*\.?\s*:?)", prompt, flags=re.I))
    for i, m in enumerate(anchors):
        n = int(m.group("n"))
        start = m.start()
        end = anchors[i+1].start() if i+1 < len(anchors) else len(prompt)
        chunk = prompt[start:end].strip()

        q_text = re.split(r"\(\s*1\s*\)", chunk, maxsplit=1)[0]
        q_text = _clean(q_text)

        opts = []
        for k in range(1, 5):
            pat = rf"\(\s*{k}\s*\)\s*(.*?)(?=\(\s*{k+1}\s*\)|\Z)"
            mm = re.search(pat, chunk, flags=re.S)
            if mm:
                opts.append(_clean(mm.group(1)))
        while len(opts) < 4:
            opts.append("")

        qk = f"q{n}"
        question_texts[qk] = q_text
        options_by_q[qk]   = opts

    return question_texts, options_by_q

def render_batch_block(qtexts: Dict[str,str], opts: Dict[str,List[str]], keys: List[str]) -> str:
    lines = [
        "Answer ONLY these questions. Return a SINGLE JSON with keys: " + ", ".join(keys) + ".",
        "Each value must be {\"option\": <0|1|2|3|4>, \"explain\": \"<concise topic phrase (<= 12 words)>\"}.",
        "Output strictly between:\n<BEGIN_JSON>\n{ ... }\n<END_JSON>\n"
    ]
    for qk in keys:
        n = int(qk[1:])
        lines.append(f"Q{n}. {qtexts[qk]}")
        for i, o in enumerate(opts[qk], start=1):
            lines.append(f"({i}) {o}")
        lines.append("")
    return "\n".join(lines)