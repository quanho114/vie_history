# HistoriAI Agent 📜

> **Agentic RAG System for Vietnamese Historical Research (1945–1975)**

[![CI/CD](https://github.com/quanho114/vie_history/actions/workflows/ci.yml/badge.svg)](https://github.com/quanho114/vie_history/actions/workflows/ci.yml)
[![Evaluation](https://github.com/quanho114/vie_history/actions/workflows/eval.yml/badge.svg)](https://github.com/quanho114/vie_history/actions/workflows/eval.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-📖-red)](README.vi.md)

HistoriAI is an academic-grade Agentic RAG system for research on Vietnamese history. It combines **hybrid retrieval** (dense vectors + BM25), **multi-tier agentic query orchestration**, and a **grounded citation verification pipeline** to deliver hallucination-resistant, fully-cited answers grounded in primary source documents.

---

## Table of Contents

- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Quick Start (Docker)](#-quick-start-docker)
- [Local Development](#-local-development)
- [Evaluation](#-evaluation--benchmarks)
- [CI/CD Pipeline](#-cicd-pipeline)
- [Port Reference](#-port-reference)
- [Makefile Commands](#-makefile-commands)

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       React + Vite UI                           │
│              Chat · Documents · Graph · Timeline                │
│                    http://localhost:12702                        │
└────────────────────────────┬────────────────────────────────────┘
                             │  HTTP / SSE
┌────────────────────────────▼────────────────────────────────────┐
│                      FastAPI Backend                            │
│                    http://localhost:12701                        │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Agentic Orchestration                   │  │
│  │  Complexity Classifier → Domain Classifier → Planner    │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐  │
│  │                  Retrieval Pipeline                      │  │
│  │                                                          │  │
│  │  Query Expansion (HyDE / RAG-Fusion)                     │  │
│  │        │                                                 │  │
│  │   ┌────▼─────┐      ┌──────────────┐                    │  │
│  │   │  Qdrant  │      │  Meilisearch │                    │  │
│  │   │  Dense   │      │  BM25 Lexical│                    │  │
│  │   │  Vectors │      │  Search      │                    │  │
│  │   └────┬─────┘      └──────┬───────┘                    │  │
│  │        └─────────┬─────────┘                            │  │
│  │              RRF Fusion                                  │  │
│  │                  │                                       │  │
│  │         Cross-Encoder Reranker                           │  │
│  │         (AITeamVN/Vietnamese_Reranker)                   │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐  │
│  │               Generation & Verification                  │  │
│  │  LLM Synthesis → NLI Citation Verifier → SSE Stream     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌─────────────┐  │
│  │PostgreSQL│  │  Redis   │  │ RQ Worker │  │  Langfuse   │  │
│  │ (state)  │  │ (cache)  │  │ (ingest)  │  │ (tracing)   │  │
│  └──────────┘  └──────────┘  └───────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Query Processing Pipeline

```
User Query
  │
  ▼
Complexity Classifier ──► "fast" | "agentic" | "graph"
  │
  ▼
Query Expansion (HyDE: generate hypothetical answer → embed)
  │
  ├── Dense Vector Search (Qdrant, AITeamVN/Vietnamese_Embedding_v2, dim=1024)
  └── BM25 Lexical Search (Meilisearch, tuned for Vietnamese entities & dates)
            │
            ▼
      RRF Score Fusion (Reciprocal Rank Fusion)
            │
            ▼
  Cross-Encoder Reranker (Vietnamese_Reranker — joint query×doc scoring)
            │
            ▼
  Metadata-Aware Boosting (era, dynasty, region, year alignment)
            │
            ▼
  LLM Response Synthesis (Claude Sonnet / GPT-4o / Ollama)
            │
            ▼
  Citation Verifier (NLI claim decomposition + embedding similarity)
            │
            ▼
  SSE Streamed Response with inline citations
```

---

## 🛠 Tech Stack

### Backend (`apps/api`)

| Layer | Technology |
|---|---|
| Runtime | Python 3.11+, FastAPI, Uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy asyncio + Alembic |
| Vector Store | Qdrant (dense search) |
| Lexical Search | Meilisearch (BM25, Vietnamese-tuned) |
| Cache & Queue | Redis + RQ (background ingest workers) |
| Embeddings | `AITeamVN/Vietnamese_Embedding_v2` (dim=1024) |
| Reranker | `AITeamVN/Vietnamese_Reranker` (cross-encoder) |
| NLP | PyVi (Vietnamese word segmentation), SentenceTransformers |
| LLM Providers | Anthropic Claude, OpenAI, OpenRouter, Ollama, Gemini, Groq |
| Observability | Langfuse (LLM tracing), Prometheus, Grafana |

### Frontend (`apps/web`)

| Layer | Technology |
|---|---|
| Framework | React 18 + Vite + TypeScript |
| State | Zustand |
| Styling | Tailwind CSS + Vanilla CSS |
| Animation | Framer Motion |
| 3D Graph | Three.js + React Three Fiber |
| Icons | Lucide React |

---

## 🚀 Quick Start (Docker)

Launch the complete stack — API, web app, databases, workers — in one command:

```bash
# 1. Clone
git clone <repo-url> Vie_history
cd Vie_history

# 2. Configure environment
cp .env.example .env
# Edit .env — set at minimum:
#   LLM_PROVIDER=openai  (or anthropic, ollama, etc.)
#   OPENAI_API_KEY=sk-...

# 3. Boot
docker network create historiai-network 2>/dev/null || true
docker compose -f docker-compose.yml -f docker-compose.full.yml up -d --build
```

**Access:** `http://localhost:12702`

---

## 💻 Local Development

### 1. Start Infrastructure

```bash
docker network create historiai-network 2>/dev/null || true
docker compose up -d
# Starts: PostgreSQL · Redis · Qdrant · Meilisearch
```

### 2. Backend API

```bash
cd apps/api
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run DB migrations
ALEMBIC_AUTOCOMMIT=true alembic upgrade head

# Start API server
uvicorn app.main:app --host 0.0.0.0 --port 12701 --reload
```

### 3. Background Worker

```bash
cd apps/api && source venv/bin/activate
rq worker ingest-queue --url redis://localhost:12704/0
```

### 4. Frontend

```bash
cd apps/web
npm install
npm run dev
```

---

## 📊 Evaluation & Benchmarks

The system is continuously evaluated against a golden dataset of **50 Vietnamese historical Q&As** (sourced from the 1945–1975 period) using two pipelines:

### Retrieval Evaluation

Measures ranking quality (MRR, NDCG, Hit@k) of the hybrid search pipeline:

```bash
cd apps/api && source venv/bin/activate
python ../scripts/eval_retrieval.py
```

| Metric | Target |
|---|---|
| Hit Rate @ 5 | > 50% |
| Mean MRR | > 0.50 |
| Mean NDCG | > 0.50 |
| Avg Latency / Query | < 500ms |

### RAGAS End-to-End Evaluation

Full pipeline faithfulness and citation quality evaluation using the RAGAS framework:

```bash
cd apps/api && source venv/bin/activate
python ../evals/run_ragas.py --max-questions 10 --threshold 0.70
```

| Metric | Target |
|---|---|
| RAGAS Faithfulness | > 0.85 |
| Citation Precision | > 0.80 |
| Citation Recall | > 0.80 |
| Wilcoxon p-value | < 0.05 |

### Ablation Study

Runs 6 system configurations (A–F) to measure individual component contributions:

```bash
python evals/run_ablation_study.py
```

---

## ⚙️ CI/CD Pipeline

Every push and pull request to `main` runs the full automated pipeline:

```
Push / PR to main
       │
       ├── lint              Python (Ruff) + TypeScript (ESLint + tsc)
       ├── test-unit         pytest tests/unit/
       ├── integration-tests pytest tests/integration/ (with Postgres + Redis)
       ├── e2e-tests         Playwright (with full stack: API + DB + Qdrant + Meili)
       ├── docker-smoke-test docker compose up → /health check → down
       ├── security-scan     Trivy filesystem vulnerability scan
       │
       └── publish-docker    (main branch only)
                             Build & push to GHCR:
                             ghcr.io/<repo>-api:latest
                             ghcr.io/<repo>-web:latest
```

**Evaluation pipeline** runs separately on push/PR, with fork-safe API key guards:

```
push / PR to main
       ├── retrieval-eval    eval_retrieval.py (MRR, NDCG, Hit@k gate)
       └── ragas-eval        run_ragas.py (PR only — posts comment with metrics)
```

---

## 🔌 Port Reference

| Service | Port |
|---|---|
| FastAPI Backend | `12701` |
| React Frontend | `12702` |
| PostgreSQL | `12703` |
| Redis | `12704` |
| Qdrant REST | `12705` |
| Qdrant gRPC | `12706` |
| Meilisearch | `12707` |
| Langfuse | `12708` |
| Grafana | `13000` (admin / historiai) |
| Prometheus | `9090` |

---

## 📋 Makefile Commands

```bash
make dev-api        # Start backend API dev server (port 12701)
make dev-web        # Start React frontend dev server (port 12702)
make dev-worker     # Start RQ background ingest worker
make test-api       # Run all backend tests (pytest)
make lint-api       # Ruff lint check
make fmt-api        # Ruff format
make db-migrate     # Apply Alembic schema migrations
make clean          # Remove build artifacts, __pycache__, .pyc files
```

---

## 📁 Project Structure

```
Vie_history/
├── apps/
│   ├── api/                          # FastAPI backend
│   │   ├── alembic/                  # Database schema migrations
│   │   ├── app/
│   │   │   ├── api/                  # Route endpoints (auth, query, ingest)
│   │   │   ├── agents/               # Complexity/Domain classifier, LangGraph planner
│   │   │   ├── core/                 # Config, DB session, security, rate limiting
│   │   │   ├── models/               # SQLAlchemy models (User, Document, Message)
│   │   │   ├── schemas/              # Pydantic request/response schemas
│   │   │   ├── services/
│   │   │   │   └── retrieval/        # Hybrid search, fusion, reranker, HyDE, RAG-Fusion
│   │   │   └── worker/               # RQ background task definitions
│   │   └── tests/
│   │       ├── unit/                 # Fast unit tests (no external deps)
│   │       └── integration/          # Tests against Postgres + Redis
│   └── web/                          # React + Vite frontend
│       └── src/
│           ├── components/           # Chat, document, graph UI components
│           ├── pages/                # ChatPage, AdminPage, GraphPage, TimelinePage…
│           ├── stores/               # Zustand state (chatStore, authStore)
│           └── hooks/                # SSE stream hook, auth hook
├── data/                             # Entity catalogs, era rules, seed data
├── docs/                             # Architecture docs, plans, specs
├── evals/                            # Golden dataset, RAGAS harness, ablation study
├── infrastructure/                   # Prometheus, Grafana configs
└── scripts/                          # Ingest, seed, eval utility scripts
```

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.
