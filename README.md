# HistoriAI Agent

**AI Research Agent for Vietnamese Historical Documents (1945-1975)**

An AI research system for tra cuu (research) Vietnamese history, featuring workflow-based agents, grounded citations, URL ingestion, hybrid retrieval, and a modern React + FastAPI stack.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python 3.11+) |
| Frontend | React 18 + TypeScript + Vite |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Vector DB | Qdrant |
| Lexical Search | Elasticsearch (BM25) |
| AI Framework | LlamaIndex + LangGraph (planned) |
| Observability | Prometheus, Langfuse, Sentry |
| Deployment | Docker + dev on host |

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   React +   │────▶│   FastAPI   │────▶│ PostgreSQL  │
│   Vite UI   │     │   Backend   │     │  (Docker)   │
│ (dev :12702)│     │ (dev :12701)│     │  (Docker)   │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
         ┌─────────────────┼─────────────────┬───────────────┐
         ▼                 ▼                 ▼               ▼
   ┌──────────┐    ┌──────────┐    ┌──────────┐   ┌──────────┐
   │  Redis  │    │  Qdrant  │    │ Elastic- │   │ Langfuse │
   │(Docker) │    │(Docker)  │    │ search   │   │(optional)│
   │  :12704  │    │ :12705-6 │    │(Docker) │   │  :12708  │
   │          │    │ (vectors) │    │ :12707   │   │          │
   └──────────┘    └──────────┘    └──────────┘   └──────────┘
                        Prometheus metrics endpoint: GET /metrics
```

## Features

- **Workflow-based AI Agents**: Intent classification, task planning, query expansion, cross-encoder reranking, guarded synthesis, citations, and response traces
- **Retrieval**: Two-stage hybrid search (Elasticsearch BM25 + Qdrant vectors) with Reciprocal Rank Fusion and cross-encoder reranking for precision boost
- **Ingestion Pipeline**: URL/file ingestion, SSRF protection, PDF text extraction, Vietnamese text cleaning, chunk persistence, and best-effort dual-indexing (Qdrant + Elasticsearch)
- **Citation-grounded Answers**: Every claim is backed by source citations
- **SSE Streaming**: Real-time response tokens, citations, traces, and status stages in the chat UI
- **Admin Curation**: Document approval, quality scoring, job monitoring
- **JWT Authentication**: Secure user auth with role-based access

## Dev Ports

| Service | Host Port |
|---------|-----------|
| PostgreSQL | `12703` |
| Redis | `12704` |
| Qdrant REST | `12705` |
| Qdrant GRPC | `12706` |
| Elasticsearch | `12707` |
| Langfuse | `12708` |
| Prometheus | `9090` |
| Grafana | `13000` |
| FastAPI (dev) | `12701` |
| React/Vite (dev) | `12702` |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### 1. Clone and Setup

```bash
git clone <repo-url> Vie_history
cd Vie_history

# Copy environment variables
cp .env.example .env
# Edit .env with your settings (add your LLM API keys)
```

### 2. Start Services

```bash
# Create shared network
docker network create historiai-network 2>/dev/null || true

# Start core services only
docker-compose up -d

# OR start with full observability (Prometheus + Grafana)
docker-compose -f docker-compose.yml -f infrastructure/docker-compose.observability.yml up -d

# Check status
docker-compose ps
```

### 3. Initialize Database

```bash
# Chay migrations trong container postgres dang chay
docker-compose exec postgres psql -U vie_history -d vie_history -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
```

### 4. Start Backend (dev tren host)

```bash
cd apps/api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # hoac venv\Scripts\activate tren Windows

# Install dependencies
pip install -e .

# Run Alembic migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --host 0.0.0.0 --port 12701 --reload
# API Docs: http://localhost:12701/docs
```

### 5. Start Frontend (dev tren host)

```bash
cd apps/web

# Install dependencies
npm install

# Start dev server
npm run dev
# Frontend: http://localhost:12702
```

### 6. Access Services

- **Frontend**: http://localhost:12702
- **API Docs**: http://localhost:12701/docs
- **Qdrant Dashboard**: http://localhost:12705/dashboard
- **Prometheus Metrics**: http://localhost:12701/metrics
- **Prometheus UI**: http://localhost:9090
- **Grafana Dashboard**: http://localhost:13000 (admin/historiai)

### Observability Stack

```bash
# Start full observability stack (Prometheus + Grafana)
docker network create historiai-network 2>/dev/null || true
docker compose -f docker-compose.yml -f infrastructure/docker-compose.observability.yml up -d

# Prometheus: http://localhost:9090
# Grafana:   http://localhost:13000 (admin / historiai)
```

To enable Langfuse tracing, set these in `.env`:
```bash
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com  # or http://localhost:12708
```

## Development

### Backend

```bash
cd apps/api

# Activate venv
source venv/bin/activate

# Run migrations
alembic upgrade head

# Start dev server (port 12701)
uvicorn app.main:app --host 0.0.0.0 --port 12701 --reload
```

### Frontend

```bash
cd apps/web
npm install
npm run dev   # port 12702
```

### Stop Services

```bash
# Stop Docker services
docker-compose down

# Stop backend (Ctrl+C in terminal)
# Stop frontend (Ctrl+C in terminal)
```

## Project Structure

```
Vie_history/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/routes/     # API endpoints
│   │   │   ├── core/          # config, db, cache, security, observability
│   │   │   ├── models/         # SQLAlchemy models
│   │   │   ├── schemas/        # Pydantic schemas
│   │   │   └── services/       # business logic
│   │   │       ├── agent/      # AI agent workflows
│   │   │       ├── ingestion/  # URL ingestion pipeline
│   │   │       └── retrieval/  # hybrid search (vector + BM25 + reranking)
│   │   └── alembic/            # DB migrations
│   └── web/                    # React frontend
│       └── src/
│           ├── components/     # UI components
│           ├── pages/           # Route pages
│           ├── stores/          # Zustand state
│           └── lib/             # utilities
├── docker-compose.yml
├── docker-compose.full.yml    # Full stack: API + Web + Worker + Flower + Langfuse
├── .env.example
├── evals/                      # Evaluation scripts and golden datasets
│   ├── golden_dataset.json     # 50 Vietnamese history Q&A pairs
│   ├── run_ragas.py            # RAGAS evaluation pipeline
│   ├── eval_retrieval.py       # Retrieval metrics (MRR, Hit Rate, NDCG)
│   └── eval_llm_judge.py       # LLM-as-Judge evaluation
├── scripts/                    # Utility scripts
└── infrastructure/            # Docker & monitoring configs
    ├── prometheus/
    │   └── prometheus.yml     # Prometheus scrape config
    ├── grafana/
    │   └── provisioning/
    │       ├── datasources/prometheus.yaml
    │       └── dashboards/
    │           ├── dashboard.yaml
    │           └── historiai.json   # Pre-built dashboard
    └── docker-compose.observability.yml  # Prometheus + Grafana override
```

## API Endpoints

| Group | Path | Methods |
|-------|------|---------|
| Auth | `/api/v1/auth` | POST login, register; GET me |
| Query | `/api/v1/query` | POST (sync), POST /stream (SSE) |
| Sessions | `/api/v1/sessions` | GET list, GET /{id}, GET /{id}/messages |
| Ingest | `/api/v1/ingest` | POST /url, GET /jobs, GET /jobs/{id} |
| Documents | `/api/v1/documents` | GET list, GET /{id}, PATCH /{id} |
| Admin | `/api/v1/admin` | GET /stats, POST /approve, POST /reject |
| Feedback | `/api/v1/feedback` | POST |
| Metrics | `/metrics` | GET (Prometheus format) |

## Implementation Phases

- [x] **Phase 0**: Repository setup, Docker Compose (DB only), PostgreSQL schema, FastAPI skeleton, React + Vite
- [x] **Phase 1**: URL Ingestion Pipeline (SSRF, extraction, cleaning, chunk persistence)
- [x] **Phase 2**: Retrieval foundation (SQL fallback, embedder, Qdrant/BM25 components)
- [x] **Phase 3**: Research Agent foundation (classifier, planner, verifier, reranker, guarded synthesizer)
- [x] **Phase 4**: Chat UI (single SSE flow, citations, trace-capable session state)
- [x] **Phase 5**: LLM synthesis hooks with per-claim citation validation and extractive fallback
- [x] **Phase 6**: Unit + integration tests, RAGAS evaluation pipeline, golden dataset (50 Q&A), LLM-as-Judge evaluation, GitHub Actions CI + eval workflow
- [x] **Phase 7**: Prometheus metrics, Langfuse tracing (self-hosted), Sentry error reporting, `/metrics` endpoint, Grafana dashboards, full Docker stack (API + Web + Worker + Flower)
- [x] **Phase 8**: Production Safety & Resilience (Kill switch, 5-tier memory, circuit breakers, anomaly detection, A2A protocol)

## Production Safety Features

HistoriAI implements production-grade Agentic AI safety following 2026 best practices:

- **Agent Safety Layer**: Kill switch, hard token budget enforcement, session management
- **5-Tier Memory**: Short-term, Episodic, Semantic, Procedural, Observational
- **Tool Safety**: Input validation, PII detection, output filtering, permission scoping
- **Circuit Breakers**: Prevent cascading failures, automatic recovery
- **Anomaly Detection**: Loop prevention, latency monitoring, cost tracking
- **Graceful Degradation**: Fallback chains, dead letter queue, rate limiting
- **A2A Protocol**: Multi-agent communication standard with discovery
- **Safe LangGraph**: Safety-wrapped agent graph with checkpoints

See [docs/AGENT_SAFETY.md](docs/AGENT_SAFETY.md) for detailed documentation.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT
