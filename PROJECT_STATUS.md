# Project Status - KCET Math Solver

## ✅ Cleanup Complete!

Removed 26 unnecessary files from debugging session. Project is now clean and organized.

---

## Current Project Structure

```
numerical_problem_solving_v2/
├── README.md                    # Main documentation
├── requirements.txt             # Python dependencies
├── requirements.lock.txt        # Locked versions
├── .env                         # Configuration
├── CLEANUP_PLAN.md             # Cleanup documentation
├── PROJECT_STATUS.md           # This file
├── data/                        # Data files
│   ├── paper.txt               # Input: 60 questions
│   ├── solver.db               # SQLite database
│   ├── p1_questions.json       # P1 output: Parsed questions
│   ├── p2_routes.json          # P2 output: Classifications
│   └── p3_planning.json        # P3 output: Plans
├── src/                         # Source code
│   ├── main.py                 # Entry point ⭐
│   ├── shared/                 # Shared utilities
│   │   ├── config.py          # Configuration from .env
│   │   ├── schema.py          # Data schemas
│   │   └── db.py              # Database helpers
│   ├── storage/                # Database layer
│   │   ├── factory.py         # Repository factory
│   │   ├── interfaces.py      # Repository interfaces
│   │   └── sqlite_repo.py     # SQLite implementation
│   ├── p1_ingestion/           # ✅ P1: Question parsing (WORKING)
│   │   ├── api.py
│   │   ├── services/
│   │   └── parsing/
│   ├── p2_routing/             # ✅ P2: Classification (WORKING)
│   │   ├── clients/           # LLM HTTP client
│   │   ├── classification/    # Heuristic router
│   │   ├── engines/           # Router engines
│   │   └── services/          # Routing service
│   ├── p3_planning/            # ✅ P3: Planning (WORKING)
│   │   ├── api.py
│   │   └── budgeting/
│   ├── p4_solving/             # ⏳ P4: Solving (TO BE IMPLEMENTED)
│   │   ├── api.py
│   │   ├── solver.py
│   │   └── tools.py
│   ├── p5_verification/        # ⏳ P5: Verification (TO BE IMPLEMENTED)
│   │   ├── api.py
│   │   ├── verifier.py
│   │   ├── numeric.py
│   │   └── symbolic.py
│   ├── p6_output/              # ⏳ P6: Output formatting (TO BE IMPLEMENTED)
│   │   ├── api.py
│   │   ├── formatter.py
│   │   └── writer.py
│   └── p7_evaluation/          # ⏳ P7: Evaluation (TO BE IMPLEMENTED)
│       ├── api.py
│       ├── evaluator.py
│       └── metrics.py
└── services/                    # External services (MCP servers)
    ├── sympy-mcp/
    ├── pdf-mcp/
    ├── eval-mcp/
    └── router-mcp/
```

---

## Pipeline Status

### ✅ Phase 1: Ingestion (WORKING)
**Purpose:** Parse questions from TXT/PDF files

**Status:** ✅ Fully functional
- Parses 60 questions from `data/paper.txt`
- Extracts question text, options, figures
- Saves to database and JSON
- **Performance:** < 1 second

**Usage:**
```bash
python -m src.main --stage p1
```

**Output:** `data/p1_questions.json` (60 questions)

---

### ✅ Phase 2: Routing (WORKING)
**Purpose:** Classify questions by topic and difficulty

**Status:** ✅ Fully functional with LLM classification
- **LLM Router:** Connects to remote server at `100.115.136.18:7000`
- **Heuristic Router:** Local keyword-based fallback
- Model: Qwen2.5-Math-7B-Instruct (7.5 GB GPU)
- **Performance:** ~2.5 minutes for 60 questions (first request includes model loading)

**Current Results:**
```
Topics:
  - algebra: 20 questions (33%)
  - calculus: 21 questions (35%)
  - discrete: 11 questions (18%)
  - geometry: 8 questions (13%)

Difficulty:
  - Easy (E): 32 questions (53%)
  - Medium (M): 28 questions (47%)

Buckets: 8 different (algebra:E, algebra:M, calculus:E, calculus:M, etc.)
```

**Configuration (`.env`):**
```
ROUTER_BASE_URL=http://100.115.136.18:7000
ROUTER_TIMEOUT=180  # 3 minutes for Tailscale + model loading
ROUTER_STRATEGY=llm_http  # or "heuristic"
```

**Usage:**
```bash
# LLM classification
python -m src.main --stage p2 --run-id <run_id> --router llm_http

# Heuristic classification (faster, local)
python -m src.main --stage p2 --run-id <run_id> --router heuristic
```

**Output:** `data/p2_routes.json` (60 classified questions)

---

### ✅ Phase 3: Planning (WORKING)
**Purpose:** Generate solving plans based on topic/difficulty

**Status:** ✅ Fully functional
- Creates solving plans for each question
- Allocates tools and max calls based on topic/difficulty
- Saves to database and JSON
- **Performance:** < 1 second

**Usage:**
```bash
python -m src.main --stage p3 --run-id <run_id>
```

**Output:** `data/p3_planning.json` (60 plans)

---

### ⏳ Phase 4: Solving (STUB - TO BE IMPLEMENTED)
**Purpose:** Solve questions using LLM and tools

**Status:** ⏳ Skeleton code exists, needs implementation
- Files exist: `api.py`, `solver.py`, `tools.py`
- Needs integration with:
  - LLM solver (Qwen3-235B or similar)
  - SymPy MCP for symbolic computation
  - Evaluation tools

**TODO:**
- [ ] Implement solver logic
- [ ] Integrate with MCP services
- [ ] Add tool orchestration
- [ ] Test with sample questions

---

### ⏳ Phase 5: Verification (STUB - TO BE IMPLEMENTED)
**Purpose:** Verify solutions numerically and symbolically

**Status:** ⏳ Skeleton code exists, needs implementation
- Files exist: `api.py`, `verifier.py`, `numeric.py`, `symbolic.py`
- Needs integration with SymPy MCP

**TODO:**
- [ ] Implement numeric verification
- [ ] Implement symbolic verification
- [ ] Add confidence scoring
- [ ] Test verification logic

---

### ⏳ Phase 6: Output (STUB - TO BE IMPLEMENTED)
**Purpose:** Format and write results

**Status:** ⏳ Skeleton code exists, needs implementation
- Files exist: `api.py`, `formatter.py`, `writer.py`
- Needs output formatting logic

**TODO:**
- [ ] Implement result formatting
- [ ] Add CSV/JSON export
- [ ] Create human-readable output
- [ ] Test output generation

---

### ⏳ Phase 7: Evaluation (STUB - TO BE IMPLEMENTED)
**Purpose:** Evaluate accuracy against answer key

**Status:** ⏳ Skeleton code exists, needs implementation
- Files exist: `api.py`, `evaluator.py`, `metrics.py`
- Needs evaluation logic

**TODO:**
- [ ] Implement accuracy metrics
- [ ] Add per-topic breakdown
- [ ] Create mismatch reports
- [ ] Test evaluation pipeline

---

## Quick Start - P1+P2+P3 Pipeline

### Run Full Pipeline (Currently Implemented):
```bash
python -m src.main --stage p1+p2+p3 --router llm_http
```

**Expected output:**
```
P1: Parsed 60 questions (run_id=paper-20251023-235611)
P2: Routed 60 questions
  Buckets: algebra:E=12, algebra:M=8, calculus:E=14, calculus:M=7,
           discrete:E=3, discrete:M=8, geometry:E=3, geometry:M=5
P3: planned 60 questions
  Topics: algebra=20, calculus=21, discrete=11, geometry=8
  Difficulties: E=32, M=28
P1+P2+P3 complete.
```

**Output files:**
- `data/p1_questions.json` - Parsed questions
- `data/p2_routes.json` - Classifications
- `data/p3_planning.json` - Plans
- `data/solver.db` - SQLite database

---

## Configuration

### Environment Variables (`.env`)

```bash
# HuggingFace API
HF_API_KEY=hf_...

# LLM Models
FALLBACK_MODEL_ID=Qwen/Qwen3-235B-A22B-Thinking-2507
ROUTER_MODEL_ID=Qwen/Qwen2.5-Math-7B-Instruct

# Router Configuration
ROUTER_BASE_URL=http://100.115.136.18:7000  # Remote LLM server
ROUTER_TIMEOUT=180                           # 3 minutes (Tailscale latency)
ROUTER_BATCH=32                              # Batch size
ROUTER_STRATEGY=llm_http                     # or "heuristic"

# MCP Services (for P4+)
SYMPY_MCP_URL=http://localhost:8001
PDF_MCP_URL=http://localhost:8002
EVAL_MCP_URL=http://localhost:8003

# Database
LOG_LEVEL=INFO
DB_DSN=postgresql://user:pass@localhost/kcet
CACHE_URL=redis://localhost:6379
```

---

## Performance Metrics

### Current (P1+P2+P3):
- **P1 (Ingestion):** < 1 second ✅
- **P2 (LLM Routing):** ~2.5 minutes for 60 questions ⚠️
  - First request: ~60 seconds (model loading)
  - Subsequent: ~2-3 seconds each
  - Network: Tailscale adds latency
- **P3 (Planning):** < 1 second ✅
- **Total:** ~2.5 minutes

### Notes:
- P2 is slow due to:
  1. Remote server through Tailscale VPN
  2. Sequential processing (one question at a time)
  3. First request includes model loading

### Future Optimization (Later):
- Batch processing (send all 60 questions at once)
- Direct connection (bypass Tailscale)
- Local deployment (if feasible)

---

## Next Steps

### Immediate (P1+P2+P3 Optimization):
1. ✅ **Clean up unnecessary files** - DONE!
2. ⏳ **Review and optimize P1/P2/P3 code** - IN PROGRESS
3. ⏳ **Add better error handling**
4. ⏳ **Add logging and metrics**
5. ⏳ **Write tests for P1/P2/P3**

### Future (P4+P5+P6+P7 Implementation):
1. Implement P4 (Solving) with LLM integration
2. Implement P5 (Verification) with SymPy MCP
3. Implement P6 (Output) formatting
4. Implement P7 (Evaluation) metrics
5. Integrate all phases into full pipeline

### Performance Optimization (Later):
1. Batch processing for P2 routing
2. Caching for repeated questions
3. Parallel processing where possible
4. Local LLM deployment option

---

## Summary

**What's Working:** ✅
- P1: Ingestion (60 questions parsed)
- P2: LLM-based classification (8 buckets, diverse topics)
- P3: Planning (topic/difficulty-based)
- Clean, organized codebase
- Proper database persistence

**What's Next:** ⏳
- Code review and optimization of P1/P2/P3
- Implement P4 (Solving)
- Implement P5 (Verification)
- Implement P6 (Output)
- Implement P7 (Evaluation)

**Current Focus:**
Focus on P1, P2, P3 correctness and optimization first, then tackle P4-P7 implementation.

---

**Last Updated:** 2025-10-24
**Status:** Production-ready for P1+P2+P3, P4-P7 to be implemented
