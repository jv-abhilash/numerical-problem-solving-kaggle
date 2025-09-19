# models/qwen_client.py

import os
from typing import Optional, List
from dotenv import load_dotenv, find_dotenv
from huggingface_hub import InferenceClient

load_dotenv(find_dotenv(), override=False)
HF_API_KEY = os.getenv("HF_API_KEY")

_client = InferenceClient(provider="cerebras", api_key=HF_API_KEY)

MODEL_ID = "Qwen/Qwen3-235B-A22B-Thinking-2507"

# in models/qwen_client.py

def call_model(
    *args,
    max_tokens: int = 20000,
    temperature: float = 0.0,
    stop: Optional[List[str]] = None,
    model_id: Optional[str] = None,
) -> str:
    """
    Flexible chat call supporting BOTH:
      1) call_model(SYSTEM, USER, ...)
      2) call_model(MODEL_ID, SYSTEM, USER, ...)
      3) call_model(SYSTEM, USER, model_id=MODEL_ID, ...)

    This keeps solver.py working without edits while still allowing simple single-model calls.
    """
    if stop is None:
        stop = ["<END_JSON>"]

    # Parse positional args
    if len(args) == 2:
        # (system, user)
        system, user = args
        model = MODEL_ID or os.getenv("FALLBACK_MODEL_ID", MODEL_ID)
    elif len(args) == 3:
        # (model_id, system, user)
        model_candidate, system, user = args
        model = model_id or str(model_candidate)
    else:
        raise TypeError("call_model expects (system, user) or (model_id, system, user) as positional args.")

    resp = _client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
        stop=stop,
    )
    return (resp.choices[0].message.content or "").strip()