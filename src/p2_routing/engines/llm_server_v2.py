# server.py - LLM-First Classification with Keyword Fallback
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------------- FastAPI App ----------------
app = FastAPI(title="LLM Router Server")

# ---------------- Env ----------------
MODEL_ID: str = os.getenv("ROUTER_MODEL", "Qwen/Qwen2.5-Math-7B-Instruct")
HF_TOKEN: Optional[str] = os.getenv("HF_TOKEN") or None
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

    use_local = bool(LOCAL_MODEL_DIR) and os.path.isdir(LOCAL_MODEL_DIR)
    source = LOCAL_MODEL_DIR if use_local else MODEL_ID

    device_has_cuda = torch.cuda.is_available()
    device_map = "auto" if device_has_cuda else "cpu"
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

    logger.info(f"Loading {MODEL_ID} from {'local dir' if use_local else 'Hub'} on {'CUDA' if device_has_cuda else 'CPU'}")

    tok_kwargs = dict(trust_remote_code=True)
    mdl_kwargs = dict(trust_remote_code=True, device_map=device_map, dtype=dtype, quantization_config=quant_config)
    if use_local:
        tok_kwargs["local_files_only"] = True
        mdl_kwargs["local_files_only"] = True
    else:
        if HF_TOKEN:
            tok_kwargs["token"] = HF_TOKEN  # type: ignore
            mdl_kwargs["token"] = HF_TOKEN  # type: ignore

    _tok = AutoTokenizer.from_pretrained(source, **tok_kwargs)
    _model = AutoModelForCausalLM.from_pretrained(source, **mdl_kwargs)

    logger.info("Model ready.")

# ---------------- Generation ----------------
def _generate(prompt: str, max_new_tokens: int = 200, temperature: float = 0.0, do_sample: bool = False) -> str:
    """Generate text using the loaded model."""
    if _tok is None or _model is None:
        raise RuntimeError("Model not loaded. Call _load_model() first.")

    inputs = _tok(prompt, return_tensors="pt")
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

# ---------------- Lifecycle ----------------
@app.on_event("startup")
def on_startup():
    _load_model()

@app.on_event("shutdown")
def on_shutdown():
    logger.info("Shutting down...")

# ---------------- Schemas ----------------
class InputQ(BaseModel):
    qid: str
    stem: str
    options: List[str] = []

class RouteRequest(BaseModel):
    inputs: List[InputQ]

# ---------------- LLM-First Classification ----------------
def _classify_with_llm(stem: str, options: List[str]) -> Optional[Dict[str, Any]]:
    """
    Use LLM to classify the question. Returns None if fails.
    Uses a very simple, directive prompt for the 7B model.
    """
    # Build a simple, clear prompt
    prompt = f"""<|im_start|>system
You are a math question classifier. Classify each question into exactly ONE category:
- algebra (matrices, vectors, complex numbers, equations, inequalities, sequences)
- calculus (derivatives, integrals, limits, continuity, differential equations)
- discrete (probability, permutations, combinations, statistics, sets, graph theory)
- geometry (circles, triangles, conics, coordinate geometry, lines, angles)

Respond in JSON format: {{"topic": "...", "subtopic": "...", "difficulty": "E|M|H", "confidence": 0.XX}}
<|im_end|>
<|im_start|>user
Question: {stem[:400]}

Classify this question.
<|im_end|>
<|im_start|>assistant
"""

    try:
        logger.info(f"Calling LLM for classification...")
        response = _generate(prompt, max_new_tokens=100, temperature=0.0, do_sample=False)

        # Log full response for debugging
        logger.info(f"LLM raw response: {response[:200]}...")

        # Extract JSON from response
        # Look for JSON pattern
        json_match = re.search(r'\{[^{}]*\}', response)
        if json_match:
            json_str = json_match.group(0)
            result = json.loads(json_str)

            topic = result.get('topic', '').lower().strip()
            if topic not in ['algebra', 'calculus', 'discrete', 'geometry']:
                logger.warning(f"Invalid topic from LLM: {topic}")
                return None

            return {
                'topic': topic,
                'subtopic': result.get('subtopic', 'general'),
                'difficulty': result.get('difficulty', 'M').upper(),
                'confidence': float(result.get('confidence', 0.7))
            }
        else:
            logger.warning("No JSON found in LLM response")
            return None

    except Exception as e:
        logger.error(f"LLM classification error: {e}")
        return None

def _classify_with_keywords(stem: str, options: List[str]) -> Dict[str, Any]:
    """
    Keyword-based fallback classification.
    Returns topic, subtopic, difficulty, and confidence.
    """
    stem_lower = stem.lower()

    # CALCULUS - highest priority keywords
    if any(kw in stem_lower for kw in ['∫', 'integral', 'integrate']):
        return {'topic': 'calculus', 'subtopic': 'integration', 'difficulty': 'M', 'confidence': 0.95}
    if any(kw in stem_lower for kw in ['derivative', 'dy/dx', 'd/dx', 'differentiat']):
        return {'topic': 'calculus', 'subtopic': 'differentiation', 'difficulty': 'M', 'confidence': 0.95}
    if any(kw in stem_lower for kw in ['lim', 'limit']):
        return {'topic': 'calculus', 'subtopic': 'limits', 'difficulty': 'M', 'confidence': 0.90}

    # DISCRETE - combinatorics and probability
    if any(kw in stem_lower for kw in ['permutation', 'arrangement']):
        return {'topic': 'discrete', 'subtopic': 'permutations', 'difficulty': 'M', 'confidence': 0.95}
    if any(kw in stem_lower for kw in ['combination', 'choose', 'selection']):
        return {'topic': 'discrete', 'subtopic': 'combinations', 'difficulty': 'M', 'confidence': 0.95}
    if any(kw in stem_lower for kw in ['probability', 'dice', 'coin', 'card']):
        return {'topic': 'discrete', 'subtopic': 'probability', 'difficulty': 'M', 'confidence': 0.90}
    if any(kw in stem_lower for kw in ['mean', 'median', 'variance', 'standard deviation']):
        return {'topic': 'discrete', 'subtopic': 'statistics', 'difficulty': 'M', 'confidence': 0.90}
    if any(kw in stem_lower for kw in ['set', 'union', 'intersection']):
        return {'topic': 'discrete', 'subtopic': 'sets', 'difficulty': 'M', 'confidence': 0.85}

    # GEOMETRY - shapes and coordinate geometry
    if any(kw in stem_lower for kw in ['circle', 'radius', 'diameter']):
        return {'topic': 'geometry', 'subtopic': 'circles', 'difficulty': 'M', 'confidence': 0.95}
    if any(kw in stem_lower for kw in ['parabola', 'ellipse', 'hyperbola', 'latus rectum']):
        return {'topic': 'geometry', 'subtopic': 'conic sections', 'difficulty': 'M', 'confidence': 0.95}
    if any(kw in stem_lower for kw in ['triangle', 'polygon', 'octagon', 'diagonal']):
        return {'topic': 'geometry', 'subtopic': 'polygons', 'difficulty': 'M', 'confidence': 0.90}
    if any(kw in stem_lower for kw in ['line', 'slope', 'perpendicular', 'intercept']):
        return {'topic': 'geometry', 'subtopic': 'straight lines', 'difficulty': 'M', 'confidence': 0.85}

    # ALGEBRA - default category with specific keywords
    if any(kw in stem_lower for kw in ['matrix', 'matrices', 'determinant', 'adjoint']):
        return {'topic': 'algebra', 'subtopic': 'matrices', 'difficulty': 'M', 'confidence': 0.95}
    if any(kw in stem_lower for kw in ['vector', 'dot product', 'cross product']):
        return {'topic': 'algebra', 'subtopic': 'vectors', 'difficulty': 'M', 'confidence': 0.90}
    if any(kw in stem_lower for kw in ['complex', 'imaginary', 'modulus']):
        return {'topic': 'algebra', 'subtopic': 'complex numbers', 'difficulty': 'M', 'confidence': 0.90}
    if any(kw in stem_lower for kw in ['g.p.', 'a.p.', 'geometric progression', 'arithmetic progression']):
        return {'topic': 'algebra', 'subtopic': 'sequences and series', 'difficulty': 'M', 'confidence': 0.90}
    if any(kw in stem_lower for kw in ['inequality', 'inequalities']):
        return {'topic': 'algebra', 'subtopic': 'inequalities', 'difficulty': 'M', 'confidence': 0.85}
    if any(kw in stem_lower for kw in ['binomial', 'expansion']):
        return {'topic': 'algebra', 'subtopic': 'binomial theorem', 'difficulty': 'M', 'confidence': 0.90}

    # Default fallback
    return {'topic': 'algebra', 'subtopic': 'general', 'difficulty': 'M', 'confidence': 0.60}

def _classify_question(stem: str, options: List[str]) -> Dict[str, Any]:
    """
    Main classification function: LLM FIRST, then keyword fallback.
    Confidence ALWAYS comes from LLM when available, otherwise from keywords.
    """
    # Step 1: Try LLM first
    llm_result = _classify_with_llm(stem, options)
    if llm_result:
        logger.info(f"LLM classified: {llm_result['topic']} - {llm_result['subtopic']} (conf: {llm_result['confidence']:.2f})")
        return llm_result

    # Step 2: Fallback to keywords
    logger.info("LLM failed, using keyword fallback")
    keyword_result = _classify_with_keywords(stem, options)
    logger.info(f"Keyword classified: {keyword_result['topic']} - {keyword_result['subtopic']} (conf: {keyword_result['confidence']:.2f})")
    return keyword_result

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
    LLM-first approach with keyword fallback.
    """
    routes = []

    try:
        for q in req.inputs:
            try:
                classification = _classify_question(q.stem, q.options)

                routes.append({
                    "qid": q.qid,
                    "topic": classification['topic'],
                    "difficulty": classification['difficulty'],
                    "subtopic": classification['subtopic'],
                    "needs_tools": [],
                    "confidence": classification['confidence'],
                    "notes": None
                })

                logger.info(f"✓ {q.qid}: {classification['topic']} - {classification['subtopic']} (conf: {classification['confidence']:.2f})")

            except Exception as e:
                logger.error(f"Error classifying {q.qid}: {e}")
                routes.append({
                    "qid": q.qid,
                    "topic": "algebra",
                    "difficulty": "M",
                    "subtopic": "error",
                    "needs_tools": [],
                    "confidence": 0.5,
                    "notes": f"Error: {str(e)}"
                })

    except Exception as e:
        logger.error(f"Error processing route request: {e}")
        for q in req.inputs:
            routes.append({
                "qid": q.qid,
                "topic": "algebra",
                "difficulty": "M",
                "subtopic": "error",
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
