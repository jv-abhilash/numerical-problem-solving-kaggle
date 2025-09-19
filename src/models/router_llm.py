# models/local_qwen.py
import os, torch
from typing import Optional
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

_CACHE = {}

def _load_local(model_id: str):
    if model_id in _CACHE:
        return _CACHE[model_id]
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        bnb_4bit_use_double_quant=True,
    )
    tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        trust_remote_code=True,
        device_map="auto",
        quantization_config=bnb,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
    )
    _CACHE[model_id] = (tok, model)
    return tok, model

def chat(model_id: str, system: str, user: str, max_new_tokens: int = 64, temperature: float = 0.0, top_p: float = 0.9) -> str:
    tok, model = _load_local(model_id)
    messages = [{"role":"system","content":system},{"role":"user","content":user}]
    prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tok(prompt, return_tensors="pt").to(model.device)
    max_new_tokens = max(4, min(max_new_tokens, 256))
    with torch.no_grad():
        out = model.generate(
            **inputs,
            do_sample=temperature > 0.0,
            temperature=max(0.0, temperature),
            top_p=top_p,
            max_new_tokens=max_new_tokens,
            eos_token_id=tok.eos_token_id,
        )
    text = tok.decode(out[0], skip_special_tokens=True)
    return text[len(prompt):].strip()