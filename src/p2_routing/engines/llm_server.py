# server.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
import re
import torch
import logging
from transformers import AutoTokenizer, AutoModelForCausalLM

# ---------------- Logging ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- FastAPI App ----------------
app = FastAPI(title="LLM Router Server")

# ---------------- Env ----------------
MODEL_ID: str = os.getenv("ROUTER_MODEL", "Qwen/Qwen2.5-Math-7B-Instruct")
HF_TOKEN: Optional[str] = os.getenv("HF_TOKEN") or None
# IMPORTANT: default to empty so we don't force a non-existent local path
LOCAL_MODEL_DIR: str = os.getenv("LOCAL_MODEL_DIR", "")

# ---------------- Globals ----------------
_tok = None
_model = None

# ---------------- Model Load ----------------
def _load_model():
    """Load tokenizer + model (4-bit on CUDA if available)."""
    global _tok, _model
    if _tok is not None and _model is not None:
        return

    # Decide source: local directory if it exists, otherwise hub repo ID
    use_local = bool(LOCAL_MODEL_DIR) and os.path.isdir(LOCAL_MODEL_DIR)
    source = LOCAL_MODEL_DIR if use_local else MODEL_ID

    device_has_cuda = torch.cuda.is_available()
    device_map = "auto" if device_has_cuda else "cpu"
    # Use dtype= (torch_dtype is deprecated)
    dtype = torch.float16 if device_has_cuda else torch.float32

    quant_config = None
    if device_has_cuda:
        try:
            from transformers import BitsAndBytesConfig
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        except Exception as e:
            logger.warning(f"bitsandbytes unavailable, falling back to full precision: {e}")
            quant_config = None
            # On modern NVIDIA, bf16 is fine too; stick to fp16 to be conservative.

    logger.info(
        f"Loading {MODEL_ID} from "
        f"{'local dir: ' + LOCAL_MODEL_DIR if use_local else 'Hugging Face Hub'} "
        f"on {'CUDA' if device_has_cuda else 'CPU'}"
    )

    tok_kwargs = dict(trust_remote_code=True)
    mdl_kwargs = dict(
        trust_remote_code=True,
        device_map=device_map,
        dtype=dtype,                       # <- updated to dtype=
        quantization_config=quant_config,  # None on CPU or if bnb not present
    )
    if use_local:
        tok_kwargs["local_files_only"] = True
        mdl_kwargs["local_files_only"] = True
    else:
        if HF_TOKEN:
            tok_kwargs["token"] = HF_TOKEN
            mdl_kwargs["token"] = HF_TOKEN

    _tok = AutoTokenizer.from_pretrained(source, **tok_kwargs)
    _model = AutoModelForCausalLM.from_pretrained(source, **mdl_kwargs)

    logger.info("Model ready.")

# ---------------- Generation ----------------
def _generate(prompt: str, max_new_tokens: int = 200, temperature: float = 0.1, do_sample: bool = False) -> str:
    """Generate text using the loaded model."""
    inputs = _tok(prompt, return_tensors="pt")
    # Move to the model's device
    inputs = {k: v.to(_model.device) for k, v in inputs.items()}

    eos_id = _tok.eos_token_id
    pad_id = eos_id if _tok.pad_token_id is None else _tok.pad_token_id

    with torch.no_grad():
        out = _model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            temperature=temperature,
            pad_token_id=pad_id,
            eos_token_id=eos_id,
        )
    return _tok.decode(out[0], skip_special_tokens=True)

def _cleanup():
    """Free up GPU memory when shutting down."""
    global _tok, _model
    if _model is not None:
        try:
            logger.info("Offloading model from GPU/CPU...")
            _model = _model.cpu()
        except Exception:
            pass
        del _model
    _model = None
    _tok = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("Model offloaded successfully.")

# ---------------- Lifecycle ----------------
@app.on_event("startup")
def on_startup():
    _load_model()

@app.on_event("shutdown")
def on_shutdown():
    logger.info("Shutting down...")
    _cleanup()

# ---------------- Schemas ----------------
class InputQ(BaseModel):
    qid: str
    stem: str
    options: List[str] = []

class RouteRequest(BaseModel):
    inputs: List[InputQ]

# ---------------- Improved Classification ----------------
def _classify_question(stem: str, options: List[str]) -> Dict[str, Any]:
    """
    Improved prompt for better topic/subtopic classification.
    Uses keyword detection + LLM for robustness.
    """
    # Build enhanced prompt
    prompt = f"""You are a mathematics question classifier. Analyze the following question and classify it.

Question: {stem}

Instructions:
1. Identify the PRIMARY mathematical topic from: algebra, calculus, discrete, geometry
2. Identify a specific subtopic (e.g., "linear inequalities", "integration", "permutations", "circles")
3. Rate difficulty: E (easy), M (medium), or H (hard)

Topic categories:
- algebra: linear equations, inequalities, matrices, determinants, complex numbers, polynomials, sequences, series, vectors
- calculus: limits, continuity, differentiation, integration, differential equations, applications of derivatives
- discrete: combinatorics, permutations, combinations, probability, statistics, sets, relations, logic, graph theory
- geometry: coordinate geometry, circles, conics, straight lines, triangles, 3D geometry, transformations

Respond in this EXACT format (no extra text):
Topic: [one of: algebra, calculus, discrete, geometry]
Subtopic: [specific subtopic in 2-4 words]
Difficulty: [E, M, or H]

Now classify:"""

    response = _generate(prompt, max_new_tokens=100, temperature=0.1)
    logger.info(f"Model response:\n{response}")

    # Parse response
    topic = "algebra"  # default
    subtopic = None
    difficulty = "M"  # default

    # Extract from response
    lines = response.lower().split('\n')
    for line in lines:
        if 'topic:' in line:
            topic_match = line.split('topic:')[1].strip()
            # Extract first word that matches our topics
            for word in topic_match.split():
                word_clean = word.strip('.,;!?')
                if word_clean in ['algebra', 'calculus', 'discrete', 'geometry']:
                    topic = word_clean
                    break

        if 'subtopic:' in line:
            subtopic_match = line.split('subtopic:')[1].strip()
            # Remove common placeholders
            if subtopic_match and subtopic_match not in ['[subtopic]', 'subtopic', 'none', '-', 'n/a']:
                subtopic = subtopic_match.strip('.,;!?')[:50]  # limit length

        if 'difficulty:' in line:
            diff_match = line.split('difficulty:')[1].strip()
            if diff_match and diff_match[0] in 'emh':
                difficulty = diff_match[0].upper()

    # Keyword-based fallback/validation
    stem_lower = stem.lower()

    # Calculus keywords
    if any(kw in stem_lower for kw in ['derivative', 'integral', 'limit', 'continuity', 'differentiate',
                                         'integrate', 'tangent', 'normal', 'maxima', 'minima',
                                         'area under curve', 'volume of revolution', 'rate of change']):
        topic = 'calculus'
        if not subtopic:
            if 'integral' in stem_lower or 'integrate' in stem_lower:
                subtopic = 'integration'
            elif 'derivative' in stem_lower or 'differentiate' in stem_lower:
                subtopic = 'differentiation'
            elif 'limit' in stem_lower:
                subtopic = 'limits'

    # Discrete math keywords
    elif any(kw in stem_lower for kw in ['permutation', 'combination', 'probability', 'choose',
                                           'arrangements', 'selections', 'ways', 'digit', 'formed',
                                           'committee', 'group', 'statistics', 'mean', 'median',
                                           'variance', 'standard deviation', 'sets', 'venn']):
        topic = 'discrete'
        if not subtopic:
            if 'permutation' in stem_lower or 'arrangements' in stem_lower:
                subtopic = 'permutations'
            elif 'combination' in stem_lower or 'selections' in stem_lower or 'choose' in stem_lower:
                subtopic = 'combinations'
            elif 'probability' in stem_lower:
                subtopic = 'probability'
            elif 'statistics' in stem_lower or 'mean' in stem_lower or 'variance' in stem_lower:
                subtopic = 'statistics'

    # Geometry keywords
    elif any(kw in stem_lower for kw in ['circle', 'radius', 'diameter', 'chord', 'parabola', 'ellipse',
                                           'hyperbola', 'conic', 'locus', 'distance', 'slope', 'equation of line',
                                           'triangle', 'angle', 'polygon', 'coordinate', 'point', 'line',
                                           'perpendicular', 'parallel', 'area of', 'perimeter']):
        topic = 'geometry'
        if not subtopic:
            if 'circle' in stem_lower:
                subtopic = 'circles'
            elif any(kw in stem_lower for kw in ['parabola', 'ellipse', 'hyperbola', 'conic']):
                subtopic = 'conic sections'
            elif 'triangle' in stem_lower:
                subtopic = 'triangles'
            elif 'line' in stem_lower or 'slope' in stem_lower:
                subtopic = 'straight lines'

    # Algebra keywords (broader, so last)
    elif any(kw in stem_lower for kw in ['matrix', 'determinant', 'equation', 'inequality', 'polynomial',
                                           'complex number', 'vector', 'sequence', 'series', 'sum',
                                           'quadratic', 'linear', 'solve for', 'roots', 'factors']):
        topic = 'algebra'
        if not subtopic:
            if 'matrix' in stem_lower or 'determinant' in stem_lower:
                subtopic = 'matrices'
            elif 'inequality' in stem_lower or 'inequalities' in stem_lower:
                subtopic = 'linear inequalities'
            elif 'vector' in stem_lower:
                subtopic = 'vectors'
            elif 'complex' in stem_lower:
                subtopic = 'complex numbers'
            elif 'sequence' in stem_lower or 'series' in stem_lower:
                subtopic = 'sequences and series'

    # Final fallback
    if not subtopic:
        subtopic = 'general'

    return {
        'topic': topic,
        'subtopic': subtopic,
        'difficulty': difficulty
    }

# ---------------- Endpoints ----------------
@app.get("/healthz")
def healthz():
    device = "n/a"
    if _model is not None and hasattr(_model, "device"):
        device = str(_model.device)
    return {
        "ok": True,
        "model": MODEL_ID,
        "loaded": _model is not None,
        "device": device,
    }

@app.post("/route")
def route(req: RouteRequest):
    """
    Classify questions into topic/subtopic/difficulty.
    Returns a list of route records with improved classification.
    """
    routes = []

    try:
        # Process each question
        for q in req.inputs:
            try:
                classification = _classify_question(q.stem, q.options)

                routes.append({
                    "qid": q.qid,
                    "topic": classification['topic'],
                    "difficulty": classification['difficulty'],
                    "subtopic": classification['subtopic'],
                    "needs_tools": [],
                    "confidence": 0.85,  # Higher confidence with hybrid approach
                    "notes": None
                })
            except Exception as e:
                logger.error(f"Error classifying {q.qid}: {e}")
                # Fallback for individual question
                routes.append({
                    "qid": q.qid,
                    "topic": "algebra",
                    "difficulty": "M",
                    "subtopic": "general",
                    "needs_tools": [],
                    "confidence": 0.5,
                    "notes": f"Error: {str(e)}"
                })

    except Exception as e:
        logger.error(f"Error processing route request: {e}")
        # Return fallback for all if complete failure
        for q in req.inputs:
            routes.append({
                "qid": q.qid,
                "topic": "algebra",
                "difficulty": "M",
                "subtopic": "general",
                "needs_tools": [],
                "confidence": 0.5,
                "notes": f"Error: {str(e)}"
            })

    return routes

@app.post("/ask")
def ask(question: Dict[str, Any]):
    try:
        content = question.get("question", "What is the capital of France?")
        response = _generate(content)
        return {
            "answer": response,
            "model": MODEL_ID,
            "mode": "transformers"
        }
    except Exception as e:
        logger.error(f"Error in /ask: {e}")
        return {"error": str(e)}
