# KCET Math Solver - Complete Project Documentation

**Version:** 0.1  
**Status:** Architecture agreed; repo skeleton + MCP/microservices scaffold created; monolith mode runnable; microservices optional.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Requirements](#requirements)
3. [System Architecture](#system-architecture)
4. [Component Details](#component-details)
5. [Data Contracts](#data-contracts)
6. [Implementation Guide](#implementation-guide)
7. [Deployment](#deployment)
8. [Roadmap](#roadmap)

## Project Overview

The KCET Math Solver is an intelligent system designed to automatically solve Karnataka Common Entrance Test (KCET) mathematical multiple-choice questions. The system uses a multi-agent architecture with specialized LLMs, symbolic verification, and distributed processing to achieve high accuracy while maintaining efficiency.

### Key Features

- **Multi-format Input Processing**: Handles KCET papers in both TXT and PDF formats _(Upcoming)_
- **Intelligent Question Routing**: Classifies questions by topic _(Done)_ and difficulty for specialized handling _(Upcomping)_
- **Agentic Problem Solving**: Uses specialized agents with tool-enabled verification - Regex _(Done)_ different Tools _(Upcoming)_
- **Symbolic Verification**: Employs SymPy for deterministic mathematical verification _(Done)_ but for sentence type Questions _(Upcoming)_
- **Cost-Optimized**: Supports local open-source LLMs to minimize operational costs _(Done - Qwen/Deepseek)_
- **Scalable Architecture**: Modular design supporting both monolith _(Ongoing)_ and microservices deployment _(Upcoming)_

## Requirements

### Functional Requirements

- **Input Sources**: Process KCET math papers as TXT and PDF files
- **Question Parsing**: Extract question blocks, options (A-D), and identify figure/diagram questions _(Upcoming)_
- **Intelligent Routing**: Classify questions by topic (algebra, calculus, discrete math) and difficulty
- **Agentic Solving**: Deploy specialized solver LLMs with tool-first verification
- **Verification**: Use SymPy for symbolic equality checks and numeric validation
- **Output Generation**: Produce CSV/JSONL with chosen options, explanations, and topic classifications
- **Evaluation**: Compare results against answer keys with detailed reporting _(Testing)_

### Non-Functional Requirements

- **Deterministic Verification**: Symbolic equality and numeric checks as hard gates
- **Cost Control**: Prefer open-source LLMs locally; batch only the router component
- **Observability**: Structured logging, per-stage timing, and attempt tracing
- **Deployability**: Support for virtual environments, Docker images, and optional Docker Compose
- **Extensibility**: Tools exposed via Model Context Protocol (MCP) for cross-runtime reuse

## System Architecture

### High-Level Architecture

The system follows a pipeline architecture with specialized components:

```
Input → Ingestion → Routing → Agent Processing → Verification → Output → Evaluation
```

### Architecture Diagrams

#### D1: End-to-End Pipeline
![Figure 1: Complete system pipeline from document ingestion to report generation](./images/image_1.PNG)

#### D2: Router Micro-Batch Processing
![Figure 2: Sequence diagram showing batched router processing for efficiency](./images/image_2.png)

#### D3: Agent State Machine
![Figure 3: State diagram showing the agent problem-solving workflow](./images/image_3_1.png)

#### D4: Deployment Architecture
![Figure 4: Container diagram showing microservices deployment structure](./images/image_4.png)

## Component Details

### 1. Ingestion & Normalization (P1-P2)

**Purpose**: Convert raw PDF/TXT files into structured question objects

**Implementation**:
- Uses PyMuPDF/pdfplumber for robust text extraction
- Segments content into question blocks
- Extracts multiple choice options (A-D)
- Normalizes whitespace and special characters
- Assigns unique question IDs and computes content hashes

**Output**: `Question{ qid, question, options[], has_figure, question_hash }`

### 2. Router (P3)

**Purpose**: Classify questions for optimal agent assignment

**Features**:
- Micro-batch processing `(16-64 questions)` for GPU efficiency
- Classification by topic `(algebra, calculus, discrete math)`
- Difficulty assessment `(Easy, Medium, Hard)`
- Tool hint generation for solver guidance

**Implementation**:
- Small, fine-tuned LLM for cost efficiency
- Pluggable model architecture
- Caching of routing decisions

**Output**: `RouteDecision{ qid, qtype, difficulty, tool_hints[] }`

### 3. Bucketer & Scheduler (P4)

**Purpose**: Organize questions into specialized processing queues

**Logic**:
- Combines `Question + RouteDecision → AgentTask`
- Creates topic-specific buckets (e.g., `bucket.algebra.E`, `bucket.calculus.M`, `bucket.discrete.H`)
- Implements trigger policies: size≥N or age≥T
- Load balancing across available workers _(optional/Upcoming)_

### 4. Agentic Solving (P5)

**Architecture**: Specialized workers using LangGraph for state management

**Agent Types**:
- **AlgebraAgent**: Linear equations, inequalities, polynomial solving
- **CalculusAgent**: Derivatives, integrals, limits, optimization
- **DiscreteAgent**: Combinatorics, probability, logic

**Solving Loop**:
1. **Draft**: Solver LLM generates `{final_answer, form}`
2. **Tool-Verify**: SymPy symbolic equality + numeric validation + option matching
3. **Critic**: On failure, LLM provides hints for repair
4. **Repair**: Attempt solution correction
5. **Termination**: Success or budget exhaustion → abstain (option 0)

### 5. Verification System

**Multi-layered Approach**:
- **Symbolic Verification**: SymPy equation solving and simplification
- **Numeric Validation**: Spot checks with test values
- **Option Matching**: Exact correspondence with provided choices
- **Form Checking**: Verify answer format consistency

### 6. Writer & Evaluator (P6)

**Outputs**:
- `model_preds.csv`: All predictions with explanations
- `model_preds_mismatch.csv`: Failed verification cases
- Accuracy metrics by topic and difficulty
- Detailed attempt traces for debugging

### 7. Telemetry & Storage (P7) _(Optional)_

**Database Schema**:
- **Relational**: SQLite→Postgres for metadata _(Optional)_
- **Blob Storage**: PDFs, raw text, logs, traces _(Optional)_
- **Cache**: Redis for idempotency and routing decisions _(Optional)_ 

**Observability**:
- Structured JSON logging
- Per-stage timing metrics
- Attempt budget tracking
- Error categorization

### 8. MCP Tooling (Model Context Protocol)

**Tool Servers**:
- **sympy-mcp**: Mathematical operations (simplify, solve, numeric_check)
- **pdf-mcp**: Document parsing (parse_pdf_to_questions)
- **eval-mcp**: Result evaluation (compare_predictions_to_key)

**Benefits**:
- Cross-runtime tool reuse
- Standardized interfaces
- Easy testing and mocking
- Future extensibility

## Data Contracts

### Question Schema
```json
{
  "qid": "Q1",
  "question": "Solve 3x + 8 < 17",
  "options": ["x<1", "x<2", "x<3", "x<4"],
  "has_figure": false,
  "question_hash": "sha256:..."
}
```

### RouteDecision Schema
```json
{
  "qid": "Q1",
  "qtype": "algebra",
  "difficulty": "E",
  "tool_hints": ["sympy.solve"]
}
```

### AgentTask Schema
```json
{
  "task_id": "task-Q1-...",
  "question": { "...Question..." },
  "route": { "...RouteDecision..." },
  "plan": {
    "steps": ["solve", "simplify", "numeric_check"],
    "budget": 3
  }
}
```

### Prediction Schema
```json
{
  "qid": "Q1",
  "option_index": 3,
  "qtype": "algebra", 
  "explanation": "3x+8<17 ⇒ x<3",
  "tool_trace": ["sympy.solve", "numeric_check"],
  "question_hash": "sha256:..."
}
```

## Implementation Guide

### Project Structure

```
kcet-math-solver/
├── README.md
├── requirements.txt
├── Dockerfile
├── data/
│   ├── paper.txt
│   └── answer_key.csv
├── images/
│   └── image1.png
├── docker/
│   └── docker-compose.micro.yml
├── services/
│   ├── sympy-mcp/
│   ├── pdf-mcp/
│   └── eval-mcp/
├── src/
|   ├── __init__.py
|   ├── main.py                      # Main orchestrator
|   ├── config.py                    # Global configuration
|   │
|   ├── p1_ingestion/                # P1: Document Ingestion & Parsing
|   │   ├── __init__.py
|   │   ├── config.py                # P1-specific config
|   │   ├── readers.py               # PDF/TXT readers
|   │   ├── cleaners.py              # Text cleaning
|   │   ├── extractors.py            # Question extraction
|   │   ├── validators.py            # Validation
|   │   ├── parser.py                # Main parser
|   │   └── api.py                   # Public API
|   │
|   ├── p2_routing/                  # P2: Question Routing & Classification
|   │   ├── __init__.py
|   │   ├── config.py
|   │   ├── classifier.py            # Topic classification
|   │   ├── difficulty.py            # Difficulty assessment
|   │   ├── router.py                # Main router
|   │   └── api.py
|   │
|   ├── p3_planning/                 # P3: Step Planning & Budgeting
|   │   ├── __init__.py
|   │   ├── planner.py               # Step planner
|   │   ├── budgeter.py              # Budget allocation
|   │   └── api.py
|   │
|   ├── p4_solving/                  # P4: Problem Solving (Agent)
|   │   ├── __init__.py
|   │   ├── agent.py                 # Main agent
|   │   ├── solver.py                # Solver logic
|   │   ├── tools.py                 # Tool usage
|   │   └── api.py
|   │
|   ├── p5_verification/             # P5: Answer Verification
|   │   ├── __init__.py
|   │   ├── verifier.py              # Verification logic
|   │   ├── symbolic.py              # Symbolic verification
|   │   ├── numeric.py               # Numeric checks
|   │   └── api.py
|   │
|   ├── p6_output/                   # P6: Output Generation
|   │   ├── __init__.py
|   │   ├── writer.py                # Write outputs
|   │   ├── formatter.py             # Format results
|   │   └── api.py
|   │
|   ├── p7_evaluation/               # P7: Evaluation & Metrics
|   │   ├── __init__.py
|   │   ├── evaluator.py             # Main evaluator
|   │   ├── metrics.py               # Metrics calculation
|   │   └── api.py
|   │
|   ├── llm/                         # LLM Interfaces (shared)
|   │   ├── __init__.py
|   │   ├── router_llm.py            # Router LLM
|   │   ├── solver_llm.py            # Solver LLM
|   │   └── base.py                  # Base LLM interface
|   │
|   ├── integration/                 # Integration Layer
|   │   ├── __init__.py
|   │   ├── mcp_client.py            # MCP client
|   │   └── tools.py                 # Tool integrations
|   │
|   └── shared/                      # Shared Utilities
|       ├── __init__.py
|       ├── io.py                    # I/O operations
|       ├── schema.py                # Data schemas
|       ├── normalize.py             # Text normalization
|       └── logging.py               # Logging utilities    
|
├── scripts/
│   └── run_local.sh
└── tests/
    └── test_placeholder.py
```

### Software Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Runtime | Python 3.11 + venv | Isolated, reproducible environment |
| Orchestration | LangGraph | Explicit graph/state for agent loops |
| Math Engine | SymPy | Deterministic algebra/calculus verification |
| Router LLM | Small, pluggable model | Cheap, micro-batched classification |
| Solver LLM | Pluggable (local/API) | Flexible cost/performance trade-offs |
| Local LLM | vLLM/TGI/Ollama | Serve open-source models locally |
| PDF Processing | PyMuPDF + pdfplumber | Robust text extraction |
| Workflow | Prefect | Schedule and observe full runs |
| API | FastAPI | Optional job submission interface |
| Deployment _(Upcoming)_| Docker + Compose | Containerized infrastructure |
| Tool Protocol | MCP | Standardized tool interfaces |

### Configuration & Run Modes

#### Environment Variables
```bash
# MCP Service Endpoints (microservices mode)
SYMPY_MCP_URL=http://localhost:8001
PDF_MCP_URL=http://localhost:8002
EVAL_MCP_URL=http://localhost:8003

# Infrastructure
LOG_LEVEL=INFO
DB_DSN=postgresql://user:pass@localhost/kcet
CACHE_URL=redis://localhost:6379
```

#### Monolith Mode (Development)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.main data/paper.txt data/answer_key.csv --out data/
```

#### Microservices Mode (Production) _(Optional)_
```bash
docker compose -f docker/docker-compose.micro.yml up --build
```

## Deployment

### Local Development
1. Clone repository and set up virtual environment
2. Install dependencies: `pip install -r requirements.txt`
3. Run in monolith mode for rapid iteration
4. Use local file system and SQLite for simplicity

## Roadmap

### Phase 1: Core Implementation (Current)
- ✅ Wire LangGraph agent graphs
- ✅ Implement symbolic verification pipeline
- ✅ Create monolith mode for development
- 🔄 Add critic and repair mechanisms

### Phase 2: MCP Integration
- 🔄 Swap local tools to MCP client calls
- ⏳ Implement HTTP-based tool servers
- ⏳ Add configuration flags for tool routing

### Phase 3: Optimization
- ⏳ Integrate local vLLM/Ollama for cost efficiency
- ⏳ Implement advanced caching strategies
- ⏳ Add comprehensive monitoring and alerting

### Phase 4: Advanced Features
- ⏳ Fine-tune specialized models for KCET domain
- ⏳ Implement active learning for model improvement
- ⏳ Add support for additional exam formats

## Key Design Principles

### Deterministic Verification
Mathematical problems require exact answers. The system uses SymPy's symbolic computation capabilities as a "hard gate" - solutions must pass symbolic verification before being accepted, regardless of LLM confidence.

### Cost Optimization
The architecture prioritizes cost efficiency through:
- Local open-source LLMs where possible
- Micro-batching only where beneficial (router)
- Aggressive caching and memoization
- Efficient resource utilization

### Extensibility
The MCP-based tool architecture ensures the system can evolve:
- Tools can be reused across different orchestrators
- Easy addition of new mathematical capabilities
- Pluggable LLM backends for different use cases

### Observability
Comprehensive logging and metrics enable:
- Performance optimization
- Error diagnosis and resolution
- Quality assurance and validation
- Cost tracking and optimization

## Conclusion

The KCET Math Solver represents a sophisticated approach to automated mathematical problem solving, combining the reasoning capabilities of modern LLMs with the precision of symbolic computation. The modular architecture ensures both development velocity and production scalability, while the emphasis on deterministic verification maintains the accuracy required for educational assessment applications.

The system's design balances multiple competing concerns - accuracy vs. speed, cost vs. capability, simplicity vs. extensibility - through thoughtful architectural choices and clear separation of concerns. As the project evolves, this foundation will support both immediate needs and future enhancements in the rapidly advancing field of AI-powered education technology.