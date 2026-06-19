# HistoriAI Agent

> **AI Research Agent cho Tài liệu Lịch sử Việt Nam (1945–1975)**

HistoriAI là một hệ thống AI học thuật nghiên cứu Agentic RAG cho việc tra cứu lịch sử Việt Nam. Hệ thống kết hợp **hybrid retrieval** (Qdrant vector search + Meilisearch BM25), **metadata-aware query processing**, và **citation verification pipeline** để cung cấp câu trả lời có trích dẫn nguồn chính xác.

---

## Mục lục

1. [Tổng quan kiến trúc](#kiến-trúc)
2. [Tech Stack](#tech-stack)
3. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
4. [Cài đặt lần đầu](#cài-đặt-lần-đầu)
5. [Chạy development](#chạy-development)
6. [Biến môi trường](#biến-môi-trường)
7. [Cấu trúc dự án](#cấu-trúc-dự-án)
8. [API Endpoints](#api-endpoints)
9. [Evaluation & Benchmark](#evaluation--benchmark)
10. [Testing](#testing)
11. [Observability](#observability)
12. [Makefile Commands](#makefile-commands)
13. [Troubleshooting](#troubleshooting)

---

## Kiến trúc

```
┌─────────────────────────────────────────────────────────────────┐
│                         React + Vite UI                         │
│                      http://localhost:12702                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP / SSE
┌───────────────────────────▼─────────────────────────────────────┐
│                       FastAPI Backend                           │
│                     http://localhost:12701                       │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  AI Agents  │  │   Retrieval  │  │   Ingestion Pipeline   │ │
│  │ orchestrator│  │  hybrid BM25 │  │  URL → extract → chunk │ │
│  │ synthesizer │  │  + vector +  │  │  → Qdrant + Meili      │ │
│  │  classifier │  │  reranker    │  │                        │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
└──────┬──────────────────┬──────────────────────────────────────-┘
       │                  │
   ┌───▼────┐    ┌────────▼──────────────────────────────┐
   │Postgres│    │  Docker Services                       │
   │  :5432 │    │  Redis :12704 | Qdrant :12705          │
   │(host)  │    │  Meilisearch :12707 | Langfuse :12708  │
   └────────┘    └────────────────────────────────────────┘
```

### Agent Pipeline

Mỗi query người dùng đi qua pipeline sau:

```
Query → ComplexityClassifier → DomainClassifier → QueryExpander
      → HybridRetrieval (BM25 + Vector + RRF Fusion)
      → CrossEncoderReranker → GuardedSynthesizer
      → CitationVerifier → SSE Stream Response
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **Frontend** | React 18, TypeScript, Vite |
| **Database** | PostgreSQL 16 |
| **Cache / Queue** | Redis 7, RQ (Redis Queue) |
| **Vector DB** | Qdrant (dense embeddings) |
| **Lexical Search** | Meilisearch (BM25) |
| **Embeddings** | SentenceTransformers `paraphrase-multilingual-MiniLM-L12-v2` |
| **LLM** | OpenAI GPT-4o / Anthropic Claude / Ollama (local) |
| **Observability** | Langfuse, Prometheus, Grafana, Sentry |
| **Infra** | Docker Compose |

---

## Yêu cầu hệ thống

| Tool | Phiên bản tối thiểu |
|------|---------------------|
| Docker | 24+ |
| Docker Compose | 2.20+ |
| Python | 3.11+ |
| Node.js | 20+ |
| npm | 9+ |
| Git | 2.x |

---

## Cài đặt lần đầu

### Bước 1 — Clone repo

```bash
git clone <repo-url> Vie_history
cd Vie_history
```

### Bước 2 — Cấu hình môi trường

```bash
cp .env.example .env
```

Mở `.env` và điền các giá trị bắt buộc:

```bash
# Bắt buộc: chọn 1 LLM provider
LLM_PROVIDER=openai          # openai | anthropic | openrouter | ollama
OPENAI_API_KEY=sk-...        # nếu dùng OpenAI
ANTHROPIC_API_KEY=sk-ant-... # nếu dùng Anthropic

# Bắt buộc: secret key cho JWT
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
```

### Bước 3 — Tạo Docker network (chỉ 1 lần)

```bash
docker network create historiai-network 2>/dev/null || true
```

### Bước 4 — Khởi động Docker services

```bash
docker-compose up -d
```

Kiểm tra tất cả services đang chạy:

```bash
docker-compose ps
```

Kết quả mong đợi — tất cả status phải là `Up`:

```
NAME              STATUS    PORTS
vie_postgres      Up        0.0.0.0:12703->5432/tcp
vie_redis         Up        0.0.0.0:12704->6379/tcp
vie_qdrant        Up        0.0.0.0:12705->6333/tcp
vie_meilisearch   Up        0.0.0.0:12707->7700/tcp
```

### Bước 5 — Cài đặt Backend

```bash
cd apps/api

# Tạo virtual environment
python3 -m venv venv
source venv/bin/activate     # Linux/macOS
# venv\Scripts\activate      # Windows

# Cài dependencies
pip install -e ".[dev]"

# Chạy database migrations
ALEMBIC_AUTOCOMMIT=true alembic upgrade head
```

### Bước 6 — Cài đặt Frontend

```bash
cd apps/web
npm install
```

---

## Chạy development

Cần **3 terminal** riêng biệt:

### Terminal 1 — Backend API

```bash
cd apps/api
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 12701 --reload
```

### Terminal 2 — Background Worker (ingestion jobs)

```bash
cd apps/api
source venv/bin/activate
rq worker ingest-queue --url redis://localhost:12704/0
```

### Terminal 3 — Frontend

```bash
cd apps/web
npm run dev
```

### Truy cập các services

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:12702 |
| **API Docs (Swagger)** | http://localhost:12701/docs |
| **API ReDoc** | http://localhost:12701/redoc |
| **Qdrant Dashboard** | http://localhost:12705/dashboard |
| **Meilisearch** | http://localhost:12707 |
| **Prometheus Metrics** | http://localhost:12701/metrics |
| **Prometheus UI** | http://localhost:9090 |
| **Grafana** | http://localhost:13000 (admin / historiai) |

---

## Biến môi trường

File `.env.example` chứa toàn bộ template với chú thích. Dưới đây là các nhóm quan trọng:

### LLM Provider

```bash
LLM_PROVIDER=openai            # openai | anthropic | openrouter | ollama

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Ollama (local, không cần API key)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### Database & Cache

```bash
POSTGRES_USER=vie_history
POSTGRES_PASSWORD=change_me_in_production
POSTGRES_DB=vie_history

REDIS_URL=redis://localhost:12704/0
QDRANT_URL=http://localhost:12705
MEILISEARCH_URL=http://localhost:12707
MEILISEARCH_MASTER_KEY=meili_master_key_secret
```

### Observability (tùy chọn)

```bash
# Langfuse — LLM tracing
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Sentry — error tracking
SENTRY_DSN=https://...@sentry.io/...
```

---

## Cấu trúc dự án

```
Vie_history/
├── apps/
│   ├── api/                          # FastAPI backend
│   │   ├── alembic/                  # Database migrations
│   │   ├── app/
│   │   │   ├── main.py               # Entry point
│   │   │   ├── factory.py            # App factory (middleware, DI setup)
│   │   │   ├── containers.py         # Dependency injection container
│   │   │   ├── core/                 # Config, DB, Redis, security, logging
│   │   │   ├── models/               # SQLAlchemy models
│   │   │   │   ├── user.py
│   │   │   │   ├── document.py
│   │   │   │   ├── message.py
│   │   │   │   └── audit_log.py
│   │   │   ├── schemas/              # Pydantic request/response schemas
│   │   │   ├── api/                  # Route handlers
│   │   │   │   └── routes/           # auth, query, ingest, admin, feedback
│   │   │   ├── agents/               # AI Agent logic
│   │   │   │   ├── agent_graph.py    # LangGraph agent graph
│   │   │   │   ├── orchestrator.py   # Main agent orchestrator
│   │   │   │   ├── synthesizer.py    # Guarded LLM synthesizer
│   │   │   │   ├── complexity_classifier.py
│   │   │   │   └── domain_classifier.py
│   │   │   ├── services/
│   │   │   │   ├── retrieval/        # Hybrid search pipeline
│   │   │   │   │   ├── fusion.py           # Reciprocal Rank Fusion
│   │   │   │   │   ├── vector_search.py    # Qdrant dense search
│   │   │   │   │   ├── meilisearch_bm25.py # Meilisearch BM25
│   │   │   │   │   ├── cross_encoder_reranker.py
│   │   │   │   │   ├── query_metadata_extractor.py
│   │   │   │   │   ├── hyde.py             # HyDE query expansion
│   │   │   │   │   ├── rag_fusion.py
│   │   │   │   │   └── query_service.py
│   │   │   │   ├── ingestion/        # URL ingestion pipeline
│   │   │   │   ├── citation/         # Citation verification
│   │   │   │   ├── brain/            # 5-tier memory system
│   │   │   │   ├── llm/              # LLM provider abstraction
│   │   │   │   └── evaluation/       # In-service eval helpers
│   │   │   ├── worker/               # Arq worker config
│   │   │   └── middleware/           # Rate limiting, auth middleware
│   │   ├── tests/
│   │   │   ├── unit/                 # Unit tests
│   │   │   └── integration/          # Integration tests (cần services)
│   │   └── pyproject.toml
│   │
│   └── web/                          # React frontend
│       └── src/
│           ├── components/           # Reusable UI components
│           ├── pages/                # ChatPage, AdminPage, SearchPage
│           ├── stores/               # Zustand state (chatStore, authStore)
│           ├── hooks/                # Custom hooks (SSE stream)
│           └── lib/                  # API client wrapper
│
├── data/                             # Entity catalogs, era rules, seed data
├── docs/
│   ├── AGENT_SAFETY.md              # Production safety documentation
│   ├── ARCHITECTURE.md
│   └── reproducibility.md
├── evals/                            # Evaluation harness
│   ├── golden_dataset.json          # 50 Q&A pairs (Vietnamese history)
│   ├── run_ragas.py                 # RAGAS evaluation pipeline
│   ├── run_ablation_study.py        # Ablation study (Config A–F)
│   ├── eval_retrieval.py            # MRR, Hit Rate, NDCG metrics
│   └── calculate_agreement.py       # Cohen's Kappa inter-annotator
├── infrastructure/
│   ├── prometheus/prometheus.yml
│   ├── grafana/provisioning/
│   └── docker-compose.observability.yml
├── scripts/                          # Utility & seed scripts
├── docker-compose.yml               # Core services (DB, cache, search)
├── docker-compose.full.yml          # Full stack + API + Web + Worker
├── Makefile
└── .env.example
```

---

## API Endpoints

Xem interactive docs tại http://localhost:12701/docs

| Group | Method | Path | Mô tả |
|-------|--------|------|-------|
| **Auth** | POST | `/api/v1/auth/register` | Đăng ký tài khoản |
| | POST | `/api/v1/auth/login` | Đăng nhập, nhận JWT |
| | GET | `/api/v1/auth/me` | Thông tin user hiện tại |
| **Query** | POST | `/api/v1/query` | Truy vấn đồng bộ |
| | POST | `/api/v1/query/stream` | Truy vấn SSE streaming |
| **Sessions** | GET | `/api/v1/sessions` | Danh sách phiên chat |
| | GET | `/api/v1/sessions/{id}/messages` | Lịch sử tin nhắn |
| **Ingest** | POST | `/api/v1/ingest/url` | Nạp tài liệu từ URL |
| | GET | `/api/v1/ingest/jobs` | Danh sách ingestion jobs |
| | GET | `/api/v1/ingest/jobs/{id}` | Trạng thái job |
| **Documents** | GET | `/api/v1/documents` | Danh sách tài liệu |
| | PATCH | `/api/v1/documents/{id}` | Cập nhật metadata |
| **Admin** | GET | `/api/v1/admin/stats` | Thống kê hệ thống |
| | POST | `/api/v1/admin/approve` | Duyệt tài liệu |
| **Feedback** | POST | `/api/v1/feedback` | Gửi feedback câu trả lời |
| **Metrics** | GET | `/metrics` | Prometheus metrics |

---

## Evaluation & Benchmark

### Chạy RAGAS evaluation

```bash
cd evals
source ../apps/api/venv/bin/activate

# Chạy full evaluation pipeline
python run_ragas.py

# Chạy ablation study (6 cấu hình A–F)
python run_ablation_study.py

# Đánh giá retrieval metrics (MRR, Hit@k, NDCG)
python eval_retrieval.py

# Tính Cohen's Kappa inter-annotator agreement
python calculate_agreement.py
```

### Kết quả mục tiêu

| Metric | Target |
|--------|--------|
| RAGAS Faithfulness | > 0.85 |
| Citation Precision | > 0.80 |
| Citation Recall | > 0.80 |
| Wilcoxon p-value | < 0.05 |

---

## Testing

### Unit tests

```bash
cd apps/api
source venv/bin/activate

# Chạy tất cả tests
pytest tests/ -v

# Chạy với coverage report
pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

# Chạy một file cụ thể
pytest tests/unit/test_fusion.py -v
pytest tests/unit/test_query_metadata_extractor.py -v
```

### Integration tests (cần Docker services đang chạy)

```bash
pytest tests/integration/ -v
```

### Frontend tests

```bash
cd apps/web
npm run test -- --run
```

---

## Observability

### Prometheus + Grafana

```bash
# Start observability stack
docker network create historiai-network 2>/dev/null || true
docker-compose -f docker-compose.yml -f infrastructure/docker-compose.observability.yml up -d

# Truy cập
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:13000  (admin / historiai)
# Metrics:    http://localhost:12701/metrics
```

Grafana đã được pre-configured với dashboard `infrastructure/grafana/provisioning/dashboards/historiai.json`.

### Langfuse (LLM Tracing)

```bash
# Trong .env
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
# Hoặc self-hosted: LANGFUSE_HOST=http://localhost:12708
```

---

## Makefile Commands

```bash
make help           # Xem tất cả lệnh có sẵn

# Development
make dev-api        # Chạy backend (port 12701)
make dev-web        # Chạy frontend (port 12702)

# Docker
make up             # docker-compose up -d
make down           # docker-compose down
make logs           # Tail tất cả logs
make logs-api       # Tail API logs

# Database
make db-migrate     # alembic upgrade head
make db-rollback    # alembic downgrade -1

# Testing
make test-api       # pytest tests/ -v
make test-api-cov   # pytest với coverage
make test-web       # npm run test

# Linting & Formatting
make lint-api       # ruff check app/
make lint-api-fix   # ruff check app/ --fix
make fmt-api        # ruff format app/
make fmt-web        # prettier --write src/

# Type checking
make typecheck-api  # mypy app/
make typecheck-web  # tsc --noEmit

# Cleanup
make clean          # Xóa __pycache__, .pytest_cache, etc.
```

---

## Ports Reference

| Service | Host Port |
|---------|-----------|
| FastAPI Backend | `12701` |
| React/Vite Frontend | `12702` |
| PostgreSQL | `12703` |
| Redis | `12704` |
| Qdrant REST | `12705` |
| Qdrant GRPC | `12706` |
| Meilisearch | `12707` |
| Langfuse | `12708` |
| Prometheus | `9090` |
| Grafana | `13000` |

---

## Troubleshooting

### `docker-compose up -d` thất bại — port đã bị dùng

```bash
# Kiểm tra port nào đang bị chiếm
sudo lsof -i :12703   # PostgreSQL
sudo lsof -i :12704   # Redis

# Kill process
sudo kill -9 <PID>
```

### Alembic migration lỗi `ProgrammingError: index already exists`

```bash
cd apps/api
source venv/bin/activate
ALEMBIC_AUTOCOMMIT=true alembic upgrade head
```

### Backend lỗi `Connection refused` khi kết nối services

Đảm bảo Docker services đang chạy:

```bash
docker-compose ps        # kiểm tra status
docker-compose up -d     # restart nếu cần
```

### Frontend không kết nối được API

Kiểm tra `VITE_API_URL` trong `apps/web/.env.local`:

```bash
VITE_API_URL=http://localhost:12701
```

### Reset toàn bộ database

```bash
docker-compose down -v   # xóa volumes
docker-compose up -d     # tạo lại
cd apps/api
source venv/bin/activate
ALEMBIC_AUTOCOMMIT=true alembic upgrade head
```

### Worker không nhận jobs

```bash
# Kiểm tra Redis kết nối
redis-cli -p 12704 ping   # phải trả về PONG

# Restart worker
cd apps/api
source venv/bin/activate
rq worker ingest-queue --url redis://localhost:12704/0
```

---

## Full Stack Docker (Production-like)

Chạy toàn bộ stack trong Docker (bao gồm API + Web + Worker):

```bash
docker network create historiai-network 2>/dev/null || true
docker compose -f docker-compose.yml -f docker-compose.full.yml up -d --build

# Xem logs
docker compose -f docker-compose.yml -f docker-compose.full.yml logs -f

# Rebuild sau khi sửa code
docker compose -f docker-compose.yml -f docker-compose.full.yml up -d --build
```

---

## Contributing

1. Fork repository
2. Tạo feature branch: `git checkout -b feature/ten-tinh-nang`
3. Chạy lint trước khi commit: `make lint`
4. Chạy tests: `make test-api`
5. Commit với message rõ ràng
6. Tạo Pull Request

Xem [CONTRIBUTING.md](CONTRIBUTING.md) để biết thêm chi tiết.

---

## License

MIT — xem [LICENSE](LICENSE)
