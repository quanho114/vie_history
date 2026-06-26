# HistoriAI Agent 📜

> **An Academic-Grade Agentic RAG System for Vietnamese Historical Documents (1945–1975)**

[![Language](https://img.shields.io/badge/Language-Vietnamese-red.svg)](README.vi.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Langfuse Tracing](https://img.shields.io/badge/LLM_Tracing-Langfuse-orange.svg)](https://cloud.langfuse.com)

HistoriAI is a state-of-the-art academic RAG (Retrieval-Augmented Generation) system tailored for research on Vietnamese history. It fuses **hybrid retrieval** (Qdrant Dense Vectors + Meilisearch BM25), **agentic query processing**, and a **rigorous citation verification pipeline** to deliver highly reliable, verifiable, and hallucination-free answers.

---

## ⚡ Core Technological Pillars

*   **Hybrid Retrieval Engine**: Fuses Meilisearch BM25 (for precise historical entities, dates, and names) with Qdrant vector search (for deep semantic retrieval) using **Reciprocal Rank Fusion (RRF)** to maximize information retrieval coverage.
*   **Agentic Orchestration (LangGraph)**: Manages complex user queries through a multi-tier agent network including a Complexity Classifier, Domain Classifier, and Query Expander (HyDE/RAG-Fusion).
*   **Grounded Citation Verification**: Employs Natural Language Inference (NLI) models to cross-reference every claim in the LLM response against original document source chunks, programmatically preventing hallucinations.
*   **Production-Grade Stack & Observability**: Powered by FastAPI, React + Vite, PostgreSQL, and Redis background workers. Integrated with Langfuse for tracing LLM executions and Prometheus/Grafana for infrastructure telemetry.

---

## 🚀 Quick Start (Docker Compose)

Launch the full-stack system (API, React App, Workers, and Databases) instantly using Docker:

```bash
# 1. Clone the repository
git clone <repo-url> Vie_history
cd Vie_history

# 2. Configure environmental variables
cp .env.example .env
# Edit .env and supply your LLM API Key (e.g., OPENAI_API_KEY)

# 3. Initialize network and boot containers
docker network create historiai-network 2>/dev/null || true
docker compose -f docker-compose.yml -f docker-compose.full.yml up -d --build
```

Access the user interface at: `http://localhost:12702`

---

## 🛠️ Local Development Setup

### Step 1: Run Infrastructure Services

```bash
docker network create historiai-network 2>/dev/null || true
docker compose up -d
```

### Step 2: Set up Backend API

```bash
cd apps/api
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
ALEMBIC_AUTOCOMMIT=true alembic upgrade head
```

### Step 3: Set up Frontend Web App

```bash
cd apps/web
npm install
```

---

## ⚙️ Running the Development Services

Run the services in **3 separate terminal sessions**:

*   **Terminal 1 (Backend API)**:
    ```bash
    cd apps/api && source venv/bin/activate
    uvicorn app.main:app --host 0.0.0.0 --port 12701 --reload
    ```
*   **Terminal 2 (Background Worker)**:
    ```bash
    cd apps/api && source venv/bin/activate
    rq worker ingest-queue --url redis://localhost:12704/0
    ```
*   **Terminal 3 (Frontend Web)**:
    ```bash
    cd apps/web
    npm run dev
    ```

---

## 🗺️ System Architecture

```
                     ┌───────────────────────────────────┐
                     │          React + Vite UI          │
                     │       http://localhost:12702      │
                     └─────────────────┬─────────────────┘
                                       │ HTTP / SSE
                     ┌─────────────────▼─────────────────┐
                     │          FastAPI Backend          │
                     │       http://localhost:12701      │
                     └─────────────────┬─────────────────┘
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            │                                                     │
 ┌──────────▼──────────┐                               ┌──────────▼──────────┐
 │   Qdrant Vector     │                               │ Meilisearch (BM25)  │
 │ (Dense Embeddings)  │                               │  (Lexical Search)   │
 └─────────────────────┘                               └─────────────────────┘
```

Query execution pipeline flow:
```
Query ──► Complexity/Domain Classifier ──► Query Expander (HyDE)
      ──► Hybrid Retrieval (Dense & BM25) ──► RRF Fusion 
      ──► Cross-Encoder Reranker ──► Guarded Synthesizer
      ──► Citation Verifier (NLI check) ──► SSE Stream Response
```

---

## 📊 Evaluation & Benchmarks

The system is evaluated against an academic golden dataset containing 50 complex historical Q&As using the RAGAS framework:

```bash
cd evals
source ../apps/api/venv/bin/activate

# Execute RAGAS evaluations
python run_ragas.py

# Evaluate retrieval precision (MRR, Hit@k, NDCG)
python eval_retrieval.py
```

### Performance Target Metrics:
| Metric | Target |
|---|---|
| RAGAS Faithfulness | > 0.85 |
| Citation Precision | > 0.80 |
| Citation Recall | > 0.80 |
| Wilcoxon p-value | < 0.05 |

---

## 📋 Developer Quick Reference (Makefile)

| Command | Function |
|---|---|
| `make dev-api` | Start the backend API dev server |
| `make dev-web` | Start the React frontend dev server |
| `make test-api` | Run all backend test cases |
| `make db-migrate` | Execute Alembic schema upgrades |
| `make lint-api` | Check backend formatting with Ruff |
| `make fmt-api` | Run code formattings with Ruff |
| `make clean` | Clean up build artifacts, cache, and junk |

---

## 🔌 Host Port Allocations

*   **FastAPI Backend API**: `12701`
*   **React Frontend Web**: `12702`
*   **PostgreSQL**: `12703`
*   **Redis**: `12704`
*   **Qdrant**: `12705` (REST) | `12706` (gRPC)
*   **Meilisearch**: `12707`
*   **Langfuse**: `12708`
*   **Grafana Dashboard**: `13000` (Credentials: `admin` / `historiai`)
*   **Prometheus**: `9090`

---

## 📄 License & Contributions
Distributed under the **MIT License**. For contribution rules, please refer to the `CONTRIBUTING.md` guidelines.
