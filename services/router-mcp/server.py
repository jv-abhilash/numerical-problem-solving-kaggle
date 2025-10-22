"""
MCP Router Service - FastAPI Server with GPU-accelerated 7B Model
Provides question routing using Qwen2.5-Math-7B-Instruct model
"""
from __future__ import annotations
import os
import logging
from typing import List, Dict, Any, Optional, Literal
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mcp-router")

# Type definitions
Topic = Literal["algebra", "calculus", "discrete", "geometry"]
Difficulty = Literal["E", "M", "H"]

# Global model and tokenizer (loaded at startup)
model = None
tokenizer = None

# Configuration
MODEL_ID = os.getenv("ROUTER_MODEL_ID", "Qwen/Qwen2.5-Math-7B-Instruct")
API_KEY = os.getenv("MCP_API_KEY", None)  # Optional API key for authentication
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "32"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))

# Topic labels for classification
TOPICS = ["algebra", "calculus", "discrete", "geometry"]
DIFFICULTIES = ["E", "M", "H"]

# System prompt for router
SYSTEM_PROMPT = """You are a mathematics question classifier. Classify each question into exactly one of these categories:
- algebra: equations, inequalities, polynomials, sequences, series, binomial theorem
- calculus: integration, differentiation, limits, trigonometry
- discrete: probability, permutations, combinations, sets, logic, LPP
- geometry: coordinate geometry, triangles, circles, polygons, locus

Also assess difficulty:
- E (Easy): straightforward, direct application
- M (Medium): requires multiple steps or concepts
- H (Hard): complex, multiple concepts, advanced reasoning

Respond ONLY in JSON format:
{"topic": "algebra|calculus|discrete|geometry", "difficulty": "E|M|H", "subtopic": "optional", "confidence": 0.0-1.0}"""


# Pydantic models
class QuestionInput(BaseModel):
    qid: str = Field(..., description="Question ID")
    stem: str = Field(..., description="Question text")
    options: List[str] = Field(default_factory=list, description="Multiple choice options")


class RoutingRequest(BaseModel):
    tool: str = Field(default="route_questions", description="Tool name")
    inputs: List[QuestionInput] = Field(..., description="List of questions to route")


class RouteResult(BaseModel):
    qid: str
    topic: Topic
    difficulty: Difficulty
    subtopic: Optional[str] = None
    needs_tools: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    notes: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup, cleanup on shutdown"""
    global model, tokenizer

    logger.info(f"Loading model: {MODEL_ID}")
    logger.info(f"Device: {DEVICE}")

    try:
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
            cache_dir="/app/models"
        )

        # Load model with GPU optimization
        if DEVICE == "cuda":
            model = AutoModelForCausalLM.from_pretrained(
                MODEL_ID,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
                cache_dir="/app/models",
                load_in_8bit=True  # Use 8-bit quantization for efficiency
            )
        else:
            model = AutoModelForCausalLM.from_pretrained(
                MODEL_ID,
                trust_remote_code=True,
                cache_dir="/app/models"
            )

        logger.info("Model loaded successfully")
        logger.info(f"Model device: {next(model.parameters()).device}")

    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

    yield

    # Cleanup
    logger.info("Shutting down, cleaning up resources")
    del model
    del tokenizer
    if DEVICE == "cuda":
        torch.cuda.empty_cache()


# Create FastAPI app
app = FastAPI(
    title="MCP Router Service",
    description="GPU-accelerated question routing using 7B LLM",
    version="1.0.0",
    lifespan=lifespan
)


def verify_api_key(authorization: Optional[str] = Header(None)) -> bool:
    """Verify API key if configured"""
    if API_KEY is None:
        return True  # No authentication required

    if authorization is None:
        return False

    # Extract Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return False

    return parts[1] == API_KEY


def classify_question(question_text: str) -> Dict[str, Any]:
    """Classify a single question using the LLM"""
    if model is None or tokenizer is None:
        raise RuntimeError("Model not loaded")

    # Prepare prompt
    user_prompt = f"Question:\n{question_text}\n\nClassify this question:"

    # Format for chat model
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    # Tokenize
    inputs = tokenizer.apply_chat_template(
        messages,
        return_tensors="pt",
        add_generation_prompt=True
    )

    if DEVICE == "cuda":
        inputs = inputs.to("cuda")

    # Generate
    with torch.no_grad():
        outputs = model.generate(
            inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE if TEMPERATURE > 0 else None,
            do_sample=TEMPERATURE > 0,
            pad_token_id=tokenizer.eos_token_id
        )

    # Decode
    response = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)

    # Parse JSON response
    import json
    try:
        result = json.loads(response.strip())

        # Normalize topic
        topic = result.get("topic", "algebra").lower()
        if topic not in TOPICS:
            # Try to map synonyms
            if topic in ["integration", "differentiation", "limits", "trig"]:
                topic = "calculus"
            elif topic in ["probability", "permutation", "combination", "sets"]:
                topic = "discrete"
            elif topic in ["vectors", "complex"]:
                topic = "algebra"
            else:
                topic = "algebra"  # default

        # Normalize difficulty
        diff = result.get("difficulty", "M").upper()
        if diff not in DIFFICULTIES:
            diff = "M"

        return {
            "topic": topic,
            "difficulty": diff,
            "subtopic": result.get("subtopic"),
            "confidence": float(result.get("confidence", 0.5)),
            "notes": None
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Failed to parse LLM response: {e}, response: {response[:100]}")
        # Return default classification
        return {
            "topic": "algebra",
            "difficulty": "M",
            "subtopic": None,
            "confidence": 0.3,
            "notes": f"Parse error: {str(e)}"
        }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model": MODEL_ID,
        "device": DEVICE,
        "model_loaded": model is not None
    }


@app.get("/info")
async def server_info():
    """Get server information"""
    gpu_info = {}
    if torch.cuda.is_available():
        gpu_info = {
            "gpu_count": torch.cuda.device_count(),
            "gpu_name": torch.cuda.get_device_name(0),
            "gpu_memory_allocated": f"{torch.cuda.memory_allocated(0) / 1024**3:.2f} GB",
            "gpu_memory_reserved": f"{torch.cuda.memory_reserved(0) / 1024**3:.2f} GB"
        }

    return {
        "model_id": MODEL_ID,
        "device": DEVICE,
        "topics": TOPICS,
        "difficulties": DIFFICULTIES,
        "gpu_info": gpu_info,
        "authentication": "enabled" if API_KEY else "disabled"
    }


@app.post("/mcp", response_model=List[RouteResult])
async def route_questions(
    request: RoutingRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Main MCP endpoint for question routing

    Accepts a batch of questions and returns routing decisions.
    """
    # Verify authentication
    if not verify_api_key(authorization):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    # Validate tool name
    if request.tool != "route_questions":
        raise HTTPException(
            status_code=400,
            detail=f"Unknown tool: {request.tool}. Expected 'route_questions'"
        )

    if not request.inputs:
        raise HTTPException(status_code=400, detail="No questions provided")

    logger.info(f"Processing {len(request.inputs)} questions")

    results = []
    for question in request.inputs:
        try:
            # Classify the question
            classification = classify_question(question.stem)

            # Infer tools based on topic
            tools = []
            if classification["topic"] in ["algebra", "calculus"]:
                tools = ["sympy"]
            elif classification["topic"] == "discrete":
                tools = ["combinatorics"]

            # Create result
            result = RouteResult(
                qid=question.qid,
                topic=classification["topic"],
                difficulty=classification["difficulty"],
                subtopic=classification.get("subtopic"),
                needs_tools=tools,
                confidence=classification["confidence"],
                notes=classification.get("notes")
            )
            results.append(result)

        except Exception as e:
            logger.error(f"Error processing question {question.qid}: {e}")
            # Return default classification on error
            results.append(RouteResult(
                qid=question.qid,
                topic="algebra",
                difficulty="M",
                confidence=0.0,
                notes=f"Error: {str(e)}"
            ))

    logger.info(f"Completed routing {len(results)} questions")
    return results


@app.post("/classify")
async def classify_single(
    question: QuestionInput,
    authorization: Optional[str] = Header(None)
):
    """Single question classification endpoint (convenience)"""
    if not verify_api_key(authorization):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    try:
        classification = classify_question(question.stem)
        return {
            "qid": question.qid,
            **classification
        }
    except Exception as e:
        logger.error(f"Classification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7001)
