from __future__ import annotations
from typing import List
from fastapi import FastAPI, Header
from pydantic import BaseModel

app = FastAPI(title="MCP Router")

class InputItem(BaseModel):
    qid: str
    stem: str
    options: List[str] = []

class MCPRequest(BaseModel):
    tool: str
    inputs: List[InputItem]

class MCPResponseItem(BaseModel):
    qid: str
    topic: str
    difficulty: str
    subtopic: str | None = None
    needs_tools: List[str] = []
    confidence: float = 0.0
    notes: str | None = None

@app.post("/mcp", response_model=List[MCPResponseItem])
def route(req: MCPRequest, authorization: str | None = Header(default=None)):
    # TODO: call your Qwen engine here (or heuristics as placeholder)
    out: List[MCPResponseItem] = []
    for it in req.inputs:
        topic = "calculus" if ("∫" in it.stem or "integral" in it.stem.lower()) else "algebra"
        out.append(MCPResponseItem(qid=it.qid, topic=topic, difficulty="M"))
    return out