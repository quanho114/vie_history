# Full Plan: Hệ thống Agentic AI — Tra Cứu Lịch Sử Việt Nam

> **Mục tiêu:** Xây dựng hệ thống AI agentic đạt chuẩn production, cho phép tra cứu lịch sử Việt Nam chính xác, có nguồn gốc rõ ràng, reasoning đa bước, với UX streaming hiện đại.
>
> **Đánh giá hiện tại:** 6.5/10 — có nền móng tốt nhưng core AI/RAG còn placeholder.
>
> **Mục tiêu đạt được:** 9+/10 — correctness, groundedness, latency, coverage đều đạt chuẩn.

---

## Mục Lục

1. [Tiêu Chí "Xuất Sắc"](#1-tiêu-chí-xuất-sắc)
2. [Kiến Trúc Tổng Thể](#2-kiến-trúc-tổng-thể)
3. [Phase 0 — Nền Móng & Cleanup](#3-phase-0--nền-móng--cleanup)
4. [Phase 1 — Data & Ingestion Pipeline](#4-phase-1--data--ingestion-pipeline)
5. [Phase 2 — Retrieval System](#5-phase-2--retrieval-system)
6. [Phase 3 — Agent Orchestration](#6-phase-3--agent-orchestration)
7. [Phase 4 — API & Streaming](#7-phase-4--api--streaming)
8. [Phase 5 — Frontend](#8-phase-5--frontend)
9. [Phase 6 — Testing & Evaluation](#9-phase-6--testing--evaluation)
10. [Phase 7 — Infrastructure & Observability](#10-phase-7--infrastructure--observability)
11. [Database Schema](#11-database-schema)
12. [Tech Stack Tổng Hợp](#12-tech-stack-tổng-hợp)
13. [Timeline & Milestones](#13-timeline--milestones)
14. [Checklist "Xuất Sắc"](#14-checklist-xuất-sắc)

**Các Sections Mới (Cải Tiến):**
- [2.5 Architecture Decision Records (ADRs)](#25-architecture-decision-records-adr)
- [2.6 Risk Analysis & Blocker Tracking](#26-risk-analysis--blocker-tracking)
- [2.7 MVP Definition (v0.1)](#27-mvp-definition-v01--demo-ready)

---

## 1. Tiêu Chí "Xuất Sắc"

Một hệ thống Agentic RAG về lịch sử Việt Nam cần đạt 4 trục đánh giá:

### 1.1 Correctness (Độ chính xác)
- Mọi claim đều trace về tài liệu gốc cụ thể, có page/section reference
- Không hallucinate — AI không bịa thông tin không có trong nguồn
- Khi có conflict giữa các nguồn, trình bày cả hai quan điểm
- Faithfulness score (RAGAS) > 0.85 trên golden test set

### 1.2 Groundedness (Căn cứ có nguồn)
- Mỗi câu trả lời kèm inline citations có thể click
- Citation hiển thị: tên tài liệu, tác giả, năm, đoạn trích liên quan
- Phân biệt rõ: **fact** (trực tiếp từ tài liệu) vs **inference** (AI suy luận)
- Ngôn ngữ phù hợp: "Theo [nguồn]..." vs "Có thể..., cần thêm tư liệu"

### 1.3 Latency (Tốc độ)
- Time To First Byte (TTFB) < 800ms
- Streaming bắt đầu trong < 1.5s
- Full response hoàn tất < 8s với câu hỏi phức tạp
- Status stages hiển thị real-time (classifying → retrieving → generating)

### 1.4 Coverage (Độ bao phủ)
- Phủ đầy đủ các thời kỳ: tiền sử → Bắc thuộc → phong kiến → cận đại → hiện đại
- Không "không biết" tùy tiện — nếu thiếu dữ liệu phải nói rõ lý do và gợi ý nguồn
- Xử lý được: tên nhiều cách viết, âm lịch/dương lịch, alias địa danh

---

## 2. Kiến Trúc Tổng Thể

```
┌─────────────────────────────────────────────────────────────┐
│                    TẦNG 1: CLIENT LAYER                      │
│  Web App (React/Vite) · Mobile · API Direct · Embed Widget  │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS / WebSocket / SSE
┌─────────────────────────▼───────────────────────────────────┐
│              TẦNG 2: API GATEWAY & AUTH                      │
│  Rate Limit · JWT/OAuth · Request Router · CORS · Logging   │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│            TẦNG 3: AGENT ORCHESTRATION (CORE)                │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │Intent        │→ │Task Planner  │→ │Tool Executor     │  │
│  │Classifier    │  │              │  │                  │  │
│  └──────────────┘  └──────────────┘  └────────┬─────────┘  │
│                                                │            │
│  ┌──────────────────────────┐  ┌───────────────▼─────────┐  │
│  │Conversation Memory &     │  │Response Synthesizer     │  │
│  │State Manager             │  │+ Citation Builder       │  │
│  └──────────────────────────┘  └─────────────────────────┘  │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │Workflow Engine: Simple · Multi-step · Parallel      │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│          TẦNG 4: KNOWLEDGE & RETRIEVAL LAYER                 │
│                                                              │
│  BM25 (Elasticsearch) ←→ Hybrid Fusion ←→ Dense (Qdrant)   │
│                              ↓                              │
│                    Cross-Encoder Reranker                    │
│                              ↓                              │
│                      Citation Builder                        │
│                              ↓                              │
│                    Eval Harness (RAGAS)                      │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              TẦNG 5: DATA & INFRASTRUCTURE                   │
│  Qdrant · PostgreSQL · Redis · Celery · Elasticsearch       │
│  Langfuse (LLM tracing) · Prometheus · Grafana              │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 Cấu trúc Repo chuẩn sau khi refactor

```
Vie_history/
├── apps/
│   ├── api/                          # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py               # App entry point
│   │   │   ├── core/
│   │   │   │   ├── config.py         # Settings từ env
│   │   │   │   ├── database.py       # SQLAlchemy async engine
│   │   │   │   ├── redis.py          # Redis client
│   │   │   │   └── security.py       # JWT, OAuth
│   │   │   ├── routes/
│   │   │   │   ├── query.py          # /api/v1/query/stream
│   │   │   │   ├── ingest.py         # /api/v1/ingest
│   │   │   │   ├── auth.py           # /api/v1/auth
│   │   │   │   └── admin.py          # /api/v1/admin
│   │   │   ├── agents/
│   │   │   │   ├── orchestrator.py   # Agent chính
│   │   │   │   ├── intent_classifier.py
│   │   │   │   ├── task_planner.py
│   │   │   │   ├── tool_executor.py
│   │   │   │   ├── tools.py          # Tool definitions
│   │   │   │   └── workflows/
│   │   │   │       ├── simple.py
│   │   │   │       ├── multi_step.py
│   │   │   │       └── parallel.py
│   │   │   ├── retrieval/
│   │   │   │   ├── hybrid_retriever.py
│   │   │   │   ├── bm25_client.py    # Elasticsearch wrapper
│   │   │   │   ├── vector_client.py  # Qdrant wrapper
│   │   │   │   ├── reranker.py       # Cross-encoder
│   │   │   │   ├── hyde.py           # HyDE query expansion
│   │   │   │   └── citation_builder.py
│   │   │   ├── ingestion/
│   │   │   │   ├── pipeline.py       # Orchestrate ingestion
│   │   │   │   ├── extractors/
│   │   │   │   │   ├── pdf.py        # PDF + OCR
│   │   │   │   │   ├── wiki.py       # Wikipedia dump parser
│   │   │   │   │   ├── html.py       # Web scraper
│   │   │   │   │   └── json.py       # Structured data
│   │   │   │   ├── cleaners/
│   │   │   │   │   ├── normalizer.py # Text normalization
│   │   │   │   │   ├── deduper.py    # Deduplication
│   │   │   │   │   └── entity_norm.py # Tên nhân vật aliases
│   │   │   │   ├── chunker.py        # Semantic chunking
│   │   │   │   └── embedder.py       # Batch embedding
│   │   │   ├── models/               # SQLAlchemy ORM models
│   │   │   │   ├── document.py
│   │   │   │   ├── chunk.py
│   │   │   │   ├── session.py
│   │   │   │   └── user.py
│   │   │   ├── schemas/              # Pydantic schemas
│   │   │   │   ├── query.py
│   │   │   │   ├── ingest.py
│   │   │   │   └── auth.py
│   │   │   ├── services/             # Business logic
│   │   │   │   ├── query_service.py
│   │   │   │   ├── ingest_service.py
│   │   │   │   └── eval_service.py
│   │   │   └── workers/
│   │   │       ├── celery_app.py
│   │   │       └── tasks.py
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   ├── integration/
│   │   │   └── conftest.py
│   │   ├── alembic/                  # DB migrations
│   │   ├── requirements.txt
│   │   ├── requirements-dev.txt
│   │   └── Dockerfile
│   └── web/                          # React/Vite frontend
│       ├── src/
│       │   ├── pages/
│       │   │   ├── ChatPage.tsx      # Luồng chat DUY NHẤT
│       │   │   ├── AdminPage.tsx
│       │   │   └── SearchPage.tsx
│       │   ├── components/
│       │   │   ├── chat/
│       │   │   │   ├── MessageBubble.tsx
│       │   │   │   ├── CitationInline.tsx
│       │   │   │   ├── CitationPanel.tsx
│       │   │   │   ├── ThinkingIndicator.tsx
│       │   │   │   ├── FollowupSuggestions.tsx
│       │   │   │   └── StreamingText.tsx
│       │   │   └── ui/               # shadcn/ui components
│       │   ├── stores/
│       │   │   ├── chatStore.ts      # Zustand — DÙNG CÁI NÀY
│       │   │   └── authStore.ts
│       │   ├── hooks/
│       │   │   ├── useSSEStream.ts
│       │   │   └── useChatHistory.ts
│       │   └── lib/
│       │       ├── api.ts            # API client
│       │       └── utils.ts
│       └── Dockerfile
├── data/
│   ├── entity_aliases.json           # Lê Lợi = Lê Thái Tổ, etc.
│   ├── era_keywords.json             # Từ khóa phân loại thời đại
│   └── seed/                         # Seed data cho dev
├── evals/
│   ├── golden_dataset.json           # 200+ câu hỏi chuẩn
│   ├── run_ragas.py
│   └── metrics_report.md
├── scripts/
│   ├── seed_data.py                  # Import seed data vào DB
│   ├── bulk_ingest.py                # Ingest nhiều tài liệu
│   └── eval_retrieval.py
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── eval.yml
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── README.md
└── DEV_COMMANDS.md
```

---

## 2.5 Architecture Decision Records (ADRs)

> **Purpose:** Document WHY decisions were made, not just WHAT was chosen. Giúp future maintainers hiểu context và trade-offs.

### ADR-001: Tại sao dùng Hybrid Retrieval (BM25 + Dense)?

**Context:**
- Cần retrieval system cho Vietnamese text với:
  - Exact entity matching (tên nhân vật, địa danh, sự kiện)
  - Semantic similarity (câu hỏi diễn đạt khác nhau)
  - Speed < 200ms cho 50 candidates
  - Handle multi-word entity names (VD: "Hồ Chí Minh" phải match "Bác Hồ")

**Options Considered:**

| Option | Pros | Cons |
|--------|------|------|
| BM25 only | Fast, interpretable, exact matching tốt | Không handle semantic similarity, miss paraphrases |
| Dense only | Semantic matching tốt, embed multilingual | Miss exact matches, cần fine-tuning cho VN, chậm hơn |
| **Hybrid Fusion (RRF)** | Cân bằng cả hai, robust | Phức tạp hơn, cần tune weights |

**Decision:** Hybrid Fusion với Reciprocal Rank Fusion (RRF)
**Rationale:** 
- Vietnamese có nhiều cách diễn đạt cùng 1 ý ("Bác Hồ" = "Hồ Chí Minh" = "Người thầy vĩ đại")
- BM25 bắt exact matches, Dense bắt semantic similarity
- RRF không cần train weights, chỉ cần union và rank

**Status:** Accepted — Week 3-6

---

### ADR-002: Tại sao dùng Qdrant thay vì pgvector?

**Context:**
- Cần vector store với:
  - Filtering by metadata (era, topic, trust_score)
  - Production-grade reliability
  - Easy to operate (self-hosted)

**Options Considered:**

| Option | Pros | Cons |
|--------|------|------|
| pgvector | Đơn giản, 1 DB cho tất cả | Không scale tốt, filter chậm với large datasets |
| **Qdrant** | Native filtering, persistent, production-grade | Thêm 1 service |

**Decision:** Qdrant cho vector, PostgreSQL cho relational
**Rationale:** Qdrant có HNSW index + payload filtering tối ưu hơn pgvector. Sự tách biệt cho phép scale independent.
**Status:** Accepted — Week 3

---

### ADR-003: Tại sao dùng Claude Sonnet thay vì GPT-4?

**Context:**
- Primary LLM cho reasoning + citation generation
- Cần: tool use, long context, Vietnamese quality

**Options Considered:**

| Option | Pros | Cons |
|--------|------|------|
| GPT-4 | Good reasoning | Không tốt bằng cho tool use, đắt hơn |
| **Claude Sonnet 4** | Tốt nhất cho tool use + reasoning, context 200K | Đắt hơn Haiku |

**Decision:** Claude Sonnet 4 cho primary, Claude Haiku cho fast tasks
**Rationale:** 
- Sonnet: query synthesis, citation generation, multi-step reasoning
- Haiku: intent classification, query expansion, simple lookups
- Cost optimization: 80% queries có thể dùng Haiku

**Status:** Accepted — Week 7

---

### ADR-004: Tại sao chunk size 512 tokens?

**Context:**
- Mỗi chunk cần đủ context để standalone nhưng không quá dài
- Vietnamese text có density information cao hơn English

**Options Considered:**

| Size | Pros | Cons |
|------|------|------|
| 256 tokens | Fast, precise | Có thể mất context, nhiều chunks hơn |
| **512 tokens** | Balanced, industry standard | Đôi khi chứa 2 ý riêng biệt |
| 1024 tokens | More context | Latency cao hơn, context window waste |

**Decision:** 512 tokens với overlap 50 tokens
**Rationale:** Balance giữa precision và recall. Overlap 50 tokens để handle ý bị cắt ngang.
**Status:** Accepted — Week 4

---

## 2.6 Risk Analysis & Blocker Tracking

### Critical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Vietnamese embedding model kém quality** | Medium | High | Fine-tune multilingual-e5 trên VN corpus trước; nếu fails, dùng BM25-heavy hybrid |
| **Data license không разрешен** | High | Critical | Bắt đầu với Wikipedia (CC-BY-SA 4.0), xin license từ Viện Sử học sau |
| **Claude API rate limits hit** | Low | Medium | Implement caching + fallback local LLM (Ollama với Llama 3) |
| **Qdrant memory issues với large index** | Medium | Medium | Partition by era (1945-1954, 1954-1965, 1965-1975), sharding strategy |
| **Wikipedia dump malformed** | Medium | Medium | Validate JSON schema trước khi ingest, quarantine bad entries |
| **Single point of failure (Claude API down)** | Low | High | Circuit breaker + cached responses + graceful degradation |

### Blockers (Must resolve before Phase X)

| Blocker | Blocking Phase | Owner | Status |
|---------|---------------|-------|--------|
| Không có ANTHROPIC_API_KEY | AI features | ? | ⏳ Pending |
| Wikipedia dump access chưa setup | Phase 1 | ? | ⏳ Pending |
| PostgreSQL schema chưa migrate | Phase 1 | ? | ⏳ Pending |
| Docker compose không chạy được | All | ? | ⏳ Blocking all |

### Dependencies Map

```
Phase 0 ──┬── Phase 1 ──┬── Phase 2 ──┬── Phase 3
          │              │              │
          │   Database  │   Retrieval  │   Agent
          │   Schema    │   System     │   Logic
          │   Docker    │   BM25+Dense │   Streaming
          └──────────────┴──────────────┘
                    Sequential:
              Mỗi phase phụ thuộc previous phase hoàn thành
```

---

## 2.7 MVP Definition (v0.1 — Demo-Ready)

### MVP Philosophy

> "Làm ít nhưng làm đúng. Có cái chạy được trong 2 tuần, sau đó mới mở rộng."

### MVP Scope: "Wikipedia Q&A"

| Feature | MVP (v0.1) | Full Plan (v1.0) |
|---------|-----------|-------------------|
| **Data source** | Wikipedia VN only (CC-BY-SA) | Multi-source (SGK, Viện Sử học, primary sources) |
| **Retrieval** | BM25 + dense (basic RRF) | Hybrid fusion + reranker + HyDE |
| **Agent** | Single-step retrieval → answer | Multi-step reasoning, tool orchestration |
| **Streaming** | SSE text only | Status stages + citations loading |
| **Auth** | None (public demo) | JWT + user management |
| **Eval** | Manual spot-check (10 questions) | RAGAS automated (200 questions) |
| **Entity linking** | None | Lê Lợi = Lê Thái Tổ resolution |
| **Error handling** | Basic error messages | Graceful degradation + suggestions |

### MVP Success Criteria

**Must have (P0):**
- [ ] User hỏi câu hỏi về sự kiện lịch sử VN (1945-1975)
- [ ] Nhận câu trả lời trong < 5s
- [ ] Câu trả lời có inline citation với Wikipedia source
- [ ] Không hallucinate nghiêm trọng (fact check được bằng mắt)

**Should have (P1):**
- [ ] Streaming text response
- [ ] Clickable citations → expand để xem source
- [ ] Follow-up question suggestions

**Nice to have (P2):**
- [ ] Entity linking (Bác Hồ → Hồ Chí Minh)
- [ ] Progress indicator (classifying → retrieving → generating)

### Incremental Versions Roadmap

| Version | Target | Features | Definition of Done |
|---------|--------|----------|-------------------|
| **v0.1** | Week 2 | Wikipedia Q&A, basic UI, no auth | User hỏi → nhận answer có citation |
| **v0.3** | Week 4 | Streaming, better UI | Smooth UX, streaming text |
| **v0.5** | Week 6 | Hybrid retrieval | NDCG@5 > 0.7, better accuracy |
| **v0.7** | Week 9 | Multi-step agent | Complex questions, tool use |
| **v0.9** | Week 12 | Auth, eval automation | User accounts, RAGAS > 0.80 |
| **v1.0** | Week 14 | Production-ready | Load test pass, monitoring, docs |

### v0.1 Technical Scope

**Backend (apps/api/):**
```
- POST /api/v1/query/stream  (SSE streaming)
- GET  /api/v1/health
- In-memory session storage (Redis sau)
```

**Data:**
```
- Wikipedia dump (100-500 articles về VN history)
- Chunk: 512 tokens, overlap 50
- Embedding: multilingual-e5-small (fast, cheap)
```

**Frontend (apps/web/):**
```
- Single ChatPage.tsx
- MessageBubble with citation inline
- No auth, no history persistence
```

**Infrastructure:**
```
- Docker compose: api + qdrant + postgres
- No Redis (session in-memory)
- No Celery (sync processing OK cho MVP)
```

---

## 3. Phase 0 — Nền Móng & Cleanup

**Thời gian:** 1 tuần  
**Mục tiêu:** Xóa nợ kỹ thuật, thiết lập cơ sở sạch

### 3.1 Dọn Repo — Checklist

```bash
# Day 1: Cleanup commands
# Xóa file artifact lạ
rm apps/api/=4.3.0

# Xóa dist và build artifacts khỏi git tracking
git rm -r --cached apps/web/dist/
git rm -r --cached **/*.tsbuildinfo

# Xóa App.tsx cũ (luồng chat cũ dùng localStorage)
rm apps/web/src/App.tsx

# Verify: chỉ còn 1 entry point cho frontend
ls apps/web/src/pages/ChatPage.tsx  # Phải tồn tại
```

**Phase 0 Day-by-Day:**

| Day | Task | Deliverable | Time |
|-----|------|-------------|------|
| 1 | Dọn repo, setup .gitignore | Repo sạch, CI pass | 2-3h |
| 2 | Setup Docker compose | `docker-compose up` chạy được | 2-3h |
| 3 | Setup PostgreSQL schema | Alembic migrations work | 2h |
| 4 | Setup basic API structure | `/api/health` returns 200 | 2h |
| 5 | Setup CI/CD | GitHub Actions pass | 1h |
| 6-7 | Review + buffer | Mọi thứ hoạt động | 2h |

**Phase 0 Success Criteria:**

- [ ] `git status` clean (no untracked artifacts)
- [ ] `docker-compose up` chạy không lỗi
- [ ] `docker-compose ps` show all services healthy
- [ ] `curl http://localhost:8000/api/health` returns 200
- [ ] `curl http://localhost:3000` mở được frontend
- [ ] GitHub Actions CI pass

**.gitignore chuẩn:**

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
.env
.venv/
venv/
*.egg-info/
dist/
build/
.pytest_cache/
.coverage
htmlcov/

# Node
node_modules/
dist/
*.tsbuildinfo
.next/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Project-specific
storage/vectors/
storage/uploads/
*.log
celerybeat-schedule
```

### 3.2 Thống Nhất Luồng Frontend

**Nguyên tắc:** Chỉ có 1 luồng duy nhất:
```
User Input → ChatPage.tsx → Zustand Store → /api/v1/query/stream → SSE → UI Update
```

Không bao giờ:
- Gọi Anthropic API trực tiếp từ frontend
- Dùng localStorage cho chat state
- Dùng `/api/chat` (endpoint cũ)

### 3.3 Environment Setup

**`.env.example`** — commit file này, KHÔNG commit `.env` thật:

```env
# App
ENVIRONMENT=development
SECRET_KEY=your-secret-key-here-min-32-chars
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# AI
ANTHROPIC_API_KEY=sk-ant-...
EMBEDDING_MODEL=intfloat/multilingual-e5-large
RERANKER_MODEL=BAAI/bge-reranker-v2-m3

# Databases
POSTGRES_URL=postgresql+asyncpg://postgres:password@localhost:5432/vie_history
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # để trống nếu local

# Elasticsearch (BM25)
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_INDEX=vie_history_chunks

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Observability
LANGFUSE_SECRET_KEY=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
```

**`apps/api/app/core/config.py`:**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App
    environment: str = "development"
    secret_key: str
    allowed_origins: list[str] = ["http://localhost:3000"]
    
    # AI
    anthropic_api_key: str
    embedding_model: str = "intfloat/multilingual-e5-large"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    
    # Retrieval params
    bm25_top_k: int = 50
    dense_top_k: int = 50
    rerank_top_k: int = 8
    chunk_max_tokens: int = 512
    chunk_overlap_tokens: int = 128
    
    # Databases
    postgres_url: str
    redis_url: str
    qdrant_url: str
    qdrant_api_key: str = ""
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "vie_history_chunks"
    
    # Celery
    celery_broker_url: str
    celery_result_backend: str
    
    # Observability
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

### 3.4 CI/CD Setup

**`.github/workflows/ci.yml`:**

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install ruff mypy
      - run: ruff check apps/api/
      - run: mypy apps/api/app/ --ignore-missing-imports

  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: password
          POSTGRES_DB: vie_history_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r apps/api/requirements-dev.txt
      - run: pytest apps/api/tests/ --cov=app --cov-report=xml -v
        env:
          ENVIRONMENT: test
          POSTGRES_URL: postgresql+asyncpg://postgres:password@localhost:5432/vie_history_test
          REDIS_URL: redis://localhost:6379/0
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - uses: codecov/codecov-action@v4

  frontend-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm ci
        working-directory: apps/web
      - run: npm run type-check
        working-directory: apps/web
      - run: npm run lint
        working-directory: apps/web

  eval-retrieval:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    needs: [backend-test]
    steps:
      - uses: actions/checkout@v4
      - run: python evals/run_ragas.py --threshold 0.80
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

---

## 4. Phase 1 — Data & Ingestion Pipeline

**Thời gian:** 2–3 tuần  
**Mục tiêu:** Có tài liệu thật, indexable, searchable end-to-end

### 4.1 Nguồn Dữ Liệu

#### Tier 1 — Authoritative (Ưu tiên cao nhất)

| Nguồn | Format | License | Chi phí | Status |
|--------|--------|---------|---------|--------|
| **Wikipedia tiếng Việt** | Wiki XML dump | CC-BY-SA 4.0 | Miễn phí | ✅ Sẵn sàng |
| **SGK Lịch sử các cấp** | PDF scan | Public domain (sau 2020) | Miễn phí | ⏳ Cần thu thập |
| **Bách khoa toàn thư VN** | PDF/HTML | Cần xác minh | Miễn phí | ⏳ Cần xác minh |

#### Tier 2 — Secondary (Ưu tiên trung bình)

| Nguồn | Format | Chi phí | Ghi chú |
|--------|--------|---------|---------|
| Báo Nhân Dân — Lịch sử | HTML | Miễn phí | Scrape có chọn lọc |
| Thư viện Quốc gia (lib.vn) | PDF | Miễn phí | Nhiều tài liệu quý |
| Viện Sử học (vienhsu.vn) | PDF | Cần license | **License bắt buộc** |

#### Tier 3 — Supplementary (Ưu tiên thấp)

| Nguồn | Format | Ghi chú |
|--------|--------|---------|
| Luận văn lịch sử | PDF | Cần kiểm định chất lượng |
| Q&A cộng đồng đã validate | JSON | Tốt cho eval set |

#### Wikipedia Vietnamese — Chi Tiết

**Tại sao Wikipedia là lựa chọn tốt cho MVP:**

1. **Miễn phí, license rõ ràng:** CC-BY-SA 4.0 — có thể commercial use với attribution
2. **Structure tốt:** Có sections, headings, infobox — dễ parse
3. **Quantity:** ~50,000 articles liên quan đến VN history
4. **Quality:** Peer-reviewed, có citations gốc
5. **Multi-language:** Có EN/WRONG/translations để cross-check

**Wikipedia Dump Structure:**

```bash
# Download Wikipedia VN dump (khoảng 2GB compressed)
wget https://dumps.wikimedia.org/viwiki/latest/viwiki-latest-pages-articles.xml.bz2

# File size estimates
viwiki-latest-pages-articles.xml.bz2  # ~2GB compressed
viwiki-latest-pages-articles.xml       # ~15GB uncompressed
viwiki-latest-abstract.xml.gz          # ~100MB (summaries only cho MVP)
```

**Wikipedia Categories quan trọng:**

```
Category:Lịch_sử_Việt_Nam
  ├── Category: Các_cuộc_chiến_tranh_của_Việt_Nam
  ├── Category: Nhân_vật_lịch_sử_Việt_Nam
  ├── Category: Địa_danh_lịch_sử_Việt_Nam
  └── Category: Sự_kiện_lịch_sử_Việt_Nam
```

**Wikipedia Ingestion Strategy:**

| Phase | Approach | Pros | Cons |
|-------|---------|------|------|
| v0.1 MVP | WikiMedia API (online) | Đơn giản, no setup | Chậm, rate limit |
| v0.3 | XML dump parser | Nhanh, offline | Cần download + parse |
| v1.0 | Pre-processed chunks | Fastest | Cần maintain pipeline |

**Recommended: Start với XML dump** (Week 3)

### 4.2 Data Models

**`apps/api/app/models/document.py`:**

```python
from sqlalchemy import Column, String, Text, JSON, DateTime, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    CLEANING = "cleaning"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"

class HistoricalEra(str, enum.Enum):
    PREHISTORY = "tien_su"           # Tiền sử (trước 207 TCN)
    NORTH_DOMINATION = "bac_thuoc"   # Bắc thuộc (207 TCN – 938)
    EARLY_INDEPENDENCE = "doc_lap_dau" # Ngô–Đinh–Tiền Lê (938–1009)
    LY_TRAN = "ly_tran"              # Lý–Trần (1009–1400)
    HO_LATER_LE = "ho_hau_le"        # Hồ–Hậu Lê–Mạc (1400–1788)
    NGUYEN = "nguyen"                # Nguyễn (1802–1945)
    MODERN = "hien_dai"              # Hiện đại (1945–nay)

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    source_url = Column(String(2000), nullable=True)
    source_type = Column(String(50))  # pdf, wiki, html, json
    author = Column(String(300), nullable=True)
    publication_year = Column(Integer, nullable=True)
    era = Column(Enum(HistoricalEra), nullable=True)
    topics = Column(JSON, default=list)     # ["chiến tranh", "kinh tế"]
    raw_content = Column(Text, nullable=True)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING)
    error_message = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default="now()")
    updated_at = Column(DateTime, server_default="now()", onupdate="now()")
```

**`apps/api/app/models/chunk.py`:**

```python
class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    
    # Content
    content = Column(Text, nullable=False)         # Nội dung chunk
    context_prefix = Column(Text, nullable=True)   # Summary của section cha
    
    # Position
    chunk_index = Column(Integer)          # Thứ tự trong document
    section_title = Column(String(500), nullable=True)
    page_ref = Column(String(50), nullable=True)
    
    # Historical metadata
    era = Column(Enum(HistoricalEra), nullable=True)
    topics = Column(JSON, default=list)    # ["chiến tranh", "ngoại giao"]
    entities = Column(JSON, default=list)  # ["Trần Hưng Đạo", "Bạch Đằng"]
    date_refs = Column(JSON, default=list) # ["1288", "năm Mậu Tý"]
    
    # Indexing
    token_count = Column(Integer)
    qdrant_point_id = Column(String(100), nullable=True)
    es_doc_id = Column(String(100), nullable=True)
    
    # Trust score (0–1): nguồn càng uy tín càng cao
    trust_score = Column(Float, default=0.5)
    
    created_at = Column(DateTime, server_default="now()")
```

### 4.3 Extractors

**`apps/api/app/ingestion/extractors/pdf.py`:**

```python
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from pathlib import Path

class PDFExtractor:
    """
    Extract text từ PDF với fallback OCR cho scan.
    Phát hiện tự động: PDF text-based hay image-based.
    """
    
    MIN_TEXT_DENSITY = 0.1  # chars per pixel — dưới đây → dùng OCR
    
    async def extract(self, file_path: str) -> ExtractedDocument:
        doc = fitz.open(file_path)
        pages = []
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            
            # Nếu text quá ít → trang này là scan image → dùng OCR
            text_density = len(text) / (page.rect.width * page.rect.height)
            if text_density < self.MIN_TEXT_DENSITY:
                text = await self._ocr_page(page)
            
            pages.append(PageContent(
                page_number=page_num + 1,
                text=text.strip(),
                has_ocr=text_density < self.MIN_TEXT_DENSITY
            ))
        
        return ExtractedDocument(
            pages=pages,
            total_pages=len(doc),
            extraction_method="pdf+ocr"
        )
    
    async def _ocr_page(self, page: fitz.Page) -> str:
        """OCR với tiếng Việt — cần tesseract-lang-vie installed"""
        mat = fitz.Matrix(2, 2)  # scale 2x cho quality tốt hơn
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        
        text = pytesseract.image_to_string(
            img, 
            lang="vie+eng",  # Vietnamese + English
            config="--psm 6"  # Assume a single uniform block of text
        )
        return text
```

**`apps/api/app/ingestion/extractors/wiki.py`:**

```python
import mwparserfromhell
import xml.etree.ElementTree as ET
from typing import Iterator

class WikipediaExtractor:
    """
    Parse Wikipedia XML dump.
    Download: https://dumps.wikimedia.org/viwiki/latest/viwiki-latest-pages-articles.xml.bz2
    """
    
    HISTORY_CATEGORIES = [
        "Lịch sử Việt Nam", "Triều đại Việt Nam", "Nhân vật lịch sử Việt Nam",
        "Chiến tranh Việt Nam", "Địa danh lịch sử Việt Nam"
    ]
    
    def stream_articles(self, dump_path: str) -> Iterator[WikiArticle]:
        """Stream từng article từ dump file, lọc liên quan lịch sử"""
        context = ET.iterparse(dump_path, events=["end"])
        
        for event, elem in context:
            if elem.tag.endswith("}page"):
                article = self._parse_page(elem)
                if article and self._is_history_related(article):
                    yield article
                elem.clear()
    
    def _parse_page(self, page_elem) -> WikiArticle | None:
        ns = page_elem.find("{*}ns")
        if ns is None or ns.text != "0":  # Chỉ lấy mainspace articles
            return None
        
        title = page_elem.find("{*}title").text
        revision = page_elem.find("{*}revision")
        if revision is None:
            return None
        
        wikitext = revision.find("{*}text").text or ""
        
        # Parse WikiText → plain text + structure
        parsed = mwparserfromhell.parse(wikitext)
        
        # Extract sections với headings
        sections = self._extract_sections(parsed)
        plain_text = parsed.strip_code()
        
        return WikiArticle(
            title=title,
            sections=sections,
            plain_text=plain_text,
            categories=self._extract_categories(wikitext)
        )
    
    def _extract_sections(self, parsed) -> list[Section]:
        sections = []
        current_heading = "Mở đầu"
        current_content = []
        
        for node in parsed.nodes:
            if isinstance(node, mwparserfromhell.nodes.Heading):
                if current_content:
                    sections.append(Section(
                        title=current_heading,
                        content=" ".join(current_content)
                    ))
                current_heading = str(node.title).strip()
                current_content = []
            elif isinstance(node, mwparserfromhell.nodes.Text):
                text = str(node).strip()
                if text:
                    current_content.append(text)
        
        if current_content:
            sections.append(Section(title=current_heading, content=" ".join(current_content)))
        
        return sections
    
    def _is_history_related(self, article: WikiArticle) -> bool:
        return any(cat in self.HISTORY_CATEGORIES for cat in article.categories) or \
               any(keyword in article.title for keyword in ["lịch sử", "triều", "khởi nghĩa", "trận"])
```

### 4.4 Cleaner & Entity Normalization

**`apps/api/app/ingestion/cleaners/entity_norm.py`:**

```python
import json
from pathlib import Path

class VietnameseEntityNormalizer:
    """
    Chuẩn hóa tên nhân vật, địa danh, triều đại.
    Đảm bảo "Lê Lợi" và "Lê Thái Tổ" map về cùng entity.
    """
    
    def __init__(self):
        aliases_path = Path("data/entity_aliases.json")
        self.aliases = json.loads(aliases_path.read_text(encoding="utf-8"))
        
        # Build reverse map: alias → canonical name
        self.reverse_map = {}
        for canonical, alias_list in self.aliases.items():
            for alias in alias_list:
                self.reverse_map[alias.lower()] = canonical
    
    def normalize(self, text: str) -> str:
        """Thay thế aliases bằng tên canonical trong text"""
        for alias, canonical in sorted(
            self.reverse_map.items(), 
            key=lambda x: len(x[0]), 
            reverse=True  # Xử lý tên dài trước
        ):
            text = text.replace(alias, canonical)
            text = text.replace(alias.title(), canonical)
        return text
    
    def extract_entities(self, text: str) -> list[str]:
        """Trích xuất tất cả named entities từ text"""
        entities = []
        text_lower = text.lower()
        
        for alias, canonical in self.reverse_map.items():
            if alias in text_lower and canonical not in entities:
                entities.append(canonical)
        
        return entities
```

**`data/entity_aliases.json`:**

```json
{
  "Lê Lợi": ["Lê Thái Tổ", "Bình Định Vương", "Lê Lợi vương"],
  "Nguyễn Huệ": ["Quang Trung", "Nguyễn Quang Bình", "Hoàng đế Quang Trung"],
  "Trần Quốc Tuấn": ["Hưng Đạo Vương", "Hưng Đạo Đại Vương", "Trần Hưng Đạo"],
  "Ngô Quyền": ["Ngô vương", "Vương Ngô Quyền"],
  "Đinh Bộ Lĩnh": ["Đinh Tiên Hoàng", "Vạn Thắng Vương"],
  "Lý Công Uẩn": ["Lý Thái Tổ"],
  "Hà Nội": ["Thăng Long", "Đông Đô", "Đông Kinh", "Hà Nội"],
  "Thành phố Hồ Chí Minh": ["Sài Gòn", "Gia Định", "TP.HCM", "Sài Gòn–Gia Định"],
  "Huế": ["Phú Xuân", "kinh đô Huế"],
  "Triều Nguyễn": ["nhà Nguyễn", "vương triều Nguyễn"],
  "Triều Trần": ["nhà Trần", "vương triều Trần"],
  "Triều Lý": ["nhà Lý", "vương triều Lý"],
  "Triều Lê": ["nhà Lê", "Hậu Lê", "Lê sơ"],
  "Kháng chiến chống Mỹ": ["chiến tranh Việt Nam", "kháng chiến chống Mỹ cứu nước"],
  "Kháng chiến chống Pháp": ["kháng Pháp", "chiến tranh Đông Dương"]
}
```

### 4.5 Semantic Chunker

**`apps/api/app/ingestion/chunker.py`:**

```python
from dataclasses import dataclass
from typing import Optional
import tiktoken

@dataclass
class ChunkResult:
    content: str
    context_prefix: str        # Summary của section cha — ĐÂY LÀ KEY TECHNIQUE
    section_title: str
    chunk_index: int
    token_count: int
    era: Optional[str]
    entities: list[str]
    date_refs: list[str]

class VietnameseHistoricalChunker:
    """
    Hierarchical chunking với context enrichment.
    
    Kỹ thuật quan trọng: mỗi chunk nhỏ kèm theo summary của section cha.
    Khi retrieve, model có đủ context để hiểu chunk không bị lơ lửng.
    
    Ví dụ:
        context_prefix = "Phần này nói về trận Bạch Đằng năm 938, 
                          cuộc kháng chiến của Ngô Quyền chống Nam Hán."
        content = "Quân ta đã cắm cọc nhọn xuống lòng sông, 
                   chờ thủy triều lên rồi nhử địch vào..."
    """
    
    MAX_TOKENS = 512
    OVERLAP_TOKENS = 128
    
    def __init__(self):
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.era_detector = EraDetector()
        self.entity_extractor = VietnameseEntityNormalizer()
        self.date_extractor = DateExtractor()
    
    def chunk_document(self, doc: ExtractedDocument) -> list[ChunkResult]:
        chunks = []
        chunk_index = 0
        
        for section in doc.sections:
            # Tạo context prefix từ section title + summary ngắn
            context_prefix = self._create_context_prefix(section)
            
            # Tokenize section content
            tokens = self.tokenizer.encode(section.content)
            
            # Sliding window
            start = 0
            while start < len(tokens):
                end = min(start + self.MAX_TOKENS, len(tokens))
                window_tokens = tokens[start:end]
                window_text = self.tokenizer.decode(window_tokens)
                
                # Đảm bảo không cắt giữa câu
                window_text = self._trim_to_sentence_boundary(window_text)
                
                if len(window_text.strip()) < 50:  # Skip chunk quá ngắn
                    break
                
                chunks.append(ChunkResult(
                    content=window_text,
                    context_prefix=context_prefix,
                    section_title=section.title,
                    chunk_index=chunk_index,
                    token_count=len(self.tokenizer.encode(window_text)),
                    era=self.era_detector.detect(window_text),
                    entities=self.entity_extractor.extract_entities(window_text),
                    date_refs=self.date_extractor.extract(window_text),
                ))
                chunk_index += 1
                
                # Move window với overlap
                overlap_start = max(0, end - self.OVERLAP_TOKENS)
                start = overlap_start if overlap_start > start else end
                
                if start >= end:
                    break
        
        return chunks
    
    def _create_context_prefix(self, section: Section) -> str:
        """
        Tạo prefix context ngắn gọn cho section.
        Dùng LLM hoặc rule-based summarization.
        """
        # Rule-based (nhanh, không tốn token)
        if len(section.content) < 200:
            return section.content
        
        # Lấy 2 câu đầu của section làm context
        sentences = section.content.split(".")[:2]
        summary = ". ".join(s.strip() for s in sentences if s.strip())
        return f"[{section.title}] {summary}"
    
    def _trim_to_sentence_boundary(self, text: str) -> str:
        """Cắt text tại ranh giới câu cuối cùng"""
        endings = [".", "!", "?", "…"]
        last_end = max(text.rfind(e) for e in endings)
        if last_end > len(text) * 0.7:  # Chỉ cắt nếu còn đủ content
            return text[:last_end + 1]
        return text
```

**`apps/api/app/ingestion/cleaners/normalizer.py`:**

```python
import re
import unicodedata

class VietnameseTextNormalizer:
    """Chuẩn hóa text tiếng Việt từ nhiều nguồn khác nhau"""
    
    def normalize(self, text: str) -> str:
        text = self._fix_encoding(text)
        text = self._remove_boilerplate(text)
        text = self._normalize_whitespace(text)
        text = self._normalize_punctuation(text)
        text = self._normalize_dates(text)
        return text.strip()
    
    def _fix_encoding(self, text: str) -> str:
        """Fix common encoding issues với tiếng Việt"""
        # Normalize Unicode (NFC cho tiếng Việt)
        return unicodedata.normalize("NFC", text)
    
    def _remove_boilerplate(self, text: str) -> str:
        """Xóa header/footer/watermark lặp lại"""
        patterns = [
            r"Trang \d+ / \d+",
            r"Copyright ©.*?\n",
            r"Bản quyền thuộc.*?\n",
            r"\[sửa\]|\[sửa mã nguồn\]",  # Wikipedia edit links
            r"Wikimedia Commons.*?\n",
            r"Tham khảo\n.*?(?=\n\n)",      # Skip references sections
        ]
        for pattern in patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
        return text
    
    def _normalize_dates(self, text: str) -> str:
        """Chuẩn hóa format ngày tháng"""
        # "năm 938 sau Công nguyên" → "năm 938 SCN"
        text = re.sub(r"sau [Cc]ông [Nn]guyên", "SCN", text)
        text = re.sub(r"trước [Cc]ông [Nn]guyên", "TCN", text)
        # "thế kỷ X" → "thế kỷ 10"
        roman_map = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5",
                     "VI": "6", "VII": "7", "VIII": "8", "IX": "9", "X": "10",
                     "XI": "11", "XII": "12", "XIII": "13", "XIV": "14", "XV": "15",
                     "XVI": "16", "XVII": "17", "XVIII": "18", "XIX": "19", "XX": "20"}
        for roman, arabic in roman_map.items():
            text = re.sub(rf"thế kỷ {roman}\b", f"thế kỷ {arabic}", text)
        return text
```

### 4.6 Embedder

**`apps/api/app/ingestion/embedder.py`:**

```python
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import Optional

class ChunkEmbedder:
    """
    Embedding với multilingual-e5-large.
    Hỗ trợ tiếng Việt tốt, 1024 dimensions, MTEB top performance.
    
    QUAN TRỌNG: E5 yêu cầu prefix "query: " cho query và "passage: " cho documents.
    """
    
    MODEL_NAME = "intfloat/multilingual-e5-large"
    
    def __init__(self):
        self.model = SentenceTransformer(self.MODEL_NAME)
        self.dimension = 1024
    
    def embed_chunks(self, chunks: list[ChunkResult], 
                     batch_size: int = 32) -> list[np.ndarray]:
        """
        Embed list chunks với passage prefix.
        Kèm context_prefix vào content để embedding phong phú hơn.
        """
        texts = []
        for chunk in chunks:
            # Kết hợp context prefix + content
            if chunk.context_prefix:
                full_text = f"{chunk.context_prefix}\n\n{chunk.content}"
            else:
                full_text = chunk.content
            
            # E5 yêu cầu prefix "passage: " cho documents
            texts.append(f"passage: {full_text}")
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,  # L2 normalize
            show_progress_bar=True
        )
        return embeddings.tolist()
    
    def embed_query(self, query: str) -> list[float]:
        """Embed query với "query: " prefix"""
        embedding = self.model.encode(
            f"query: {query}",
            normalize_embeddings=True
        )
        return embedding.tolist()
```

### 4.7 Celery Workers

**`apps/api/app/workers/tasks.py`:**

```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "vie_history",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
    task_routes={
        "tasks.process_document": {"queue": "ingestion"},
        "tasks.embed_chunks": {"queue": "embedding"},
    }
)

@celery_app.task(
    bind=True, 
    max_retries=3,
    rate_limit="5/m",   # Tránh overload API embedding
    name="tasks.process_document"
)
def process_document(self, document_id: str):
    """
    Main ingestion task với đầy đủ error handling và status tracking.
    Retry với exponential backoff khi có lỗi.
    """
    from app.ingestion.pipeline import IngestionPipeline
    from app.models.document import DocumentStatus
    import asyncio
    
    async def run():
        pipeline = IngestionPipeline()
        
        try:
            # Stage 1: Extraction
            await pipeline.update_status(document_id, DocumentStatus.EXTRACTING)
            raw = await pipeline.extract(document_id)
            
            # Stage 2: Cleaning
            await pipeline.update_status(document_id, DocumentStatus.CLEANING)
            cleaned = await pipeline.clean(raw)
            
            # Stage 3: Chunking
            await pipeline.update_status(document_id, DocumentStatus.CHUNKING)
            chunks = await pipeline.chunk(cleaned, document_id)
            
            # Stage 4: Embedding (heavy — async batch)
            await pipeline.update_status(document_id, DocumentStatus.EMBEDDING)
            embeddings = await pipeline.embed(chunks)
            
            # Stage 5: Index vào Qdrant + Elasticsearch
            await pipeline.update_status(document_id, DocumentStatus.INDEXING)
            await pipeline.index(chunks, embeddings, document_id)
            
            # Done
            await pipeline.update_status(
                document_id, 
                DocumentStatus.COMPLETED,
                chunk_count=len(chunks)
            )
            
        except Exception as exc:
            await pipeline.update_status(
                document_id, 
                DocumentStatus.FAILED,
                error=str(exc)
            )
            # Retry với exponential backoff: 60s, 120s, 240s
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    
    asyncio.run(run())
```

---

## 5. Phase 2 — Retrieval System

**Thời gian:** 2 tuần  
**Mục tiêu:** Hybrid retrieval chính xác, persistent, có reranking

### 5.1 Qdrant Setup (Vector Store)

**`apps/api/app/retrieval/vector_client.py`:**

```python
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue, MatchAny, Range
)
from app.core.config import settings

class QdrantVectorClient:
    COLLECTION_NAME = "vie_history_chunks"
    VECTOR_SIZE = 1024  # multilingual-e5-large
    
    def __init__(self):
        self.client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None
        )
    
    async def ensure_collection(self):
        """Tạo collection nếu chưa có"""
        collections = await self.client.get_collections()
        exists = any(c.name == self.COLLECTION_NAME 
                     for c in collections.collections)
        
        if not exists:
            await self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=Distance.COSINE
                ),
                # HNSW config cho performance tốt
                hnsw_config={"m": 16, "ef_construct": 100}
            )
            
            # Tạo payload indexes để filter nhanh
            for field in ["era", "topics", "entities", "document_id"]:
                await self.client.create_payload_index(
                    collection_name=self.COLLECTION_NAME,
                    field_name=field,
                    field_schema="keyword"
                )
    
    async def upsert_chunks(self, chunks: list[Chunk], 
                             embeddings: list[list[float]]):
        points = [
            PointStruct(
                id=str(chunk.id),
                vector=embedding,
                payload={
                    "chunk_id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "content": chunk.content,
                    "context_prefix": chunk.context_prefix,
                    "section_title": chunk.section_title,
                    "era": chunk.era,
                    "topics": chunk.topics,
                    "entities": chunk.entities,
                    "date_refs": chunk.date_refs,
                    "trust_score": chunk.trust_score,
                    "page_ref": chunk.page_ref,
                }
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
        
        # Batch upsert
        batch_size = 100
        for i in range(0, len(points), batch_size):
            await self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=points[i:i+batch_size]
            )
    
    async def search(
        self, 
        query_vector: list[float],
        top_k: int = 50,
        era_filter: str | None = None,
        topic_filter: str | None = None,
        min_trust_score: float = 0.0
    ) -> list[ScoredChunk]:
        
        # Build filter conditions
        must_conditions = []
        
        if era_filter:
            must_conditions.append(
                FieldCondition(key="era", match=MatchValue(value=era_filter))
            )
        if topic_filter:
            must_conditions.append(
                FieldCondition(key="topics", match=MatchValue(value=topic_filter))
            )
        if min_trust_score > 0:
            must_conditions.append(
                FieldCondition(key="trust_score", range=Range(gte=min_trust_score))
            )
        
        query_filter = Filter(must=must_conditions) if must_conditions else None
        
        results = await self.client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
            score_threshold=0.3  # Loại bỏ kết quả quá kém
        )
        
        return [
            ScoredChunk(
                chunk_id=r.payload["chunk_id"],
                content=r.payload["content"],
                context_prefix=r.payload.get("context_prefix", ""),
                section_title=r.payload.get("section_title", ""),
                era=r.payload.get("era"),
                entities=r.payload.get("entities", []),
                trust_score=r.payload.get("trust_score", 0.5),
                page_ref=r.payload.get("page_ref"),
                score=r.score,
                retrieval_method="dense"
            )
            for r in results
        ]
```

### 5.2 Elasticsearch BM25 Setup

**`apps/api/app/retrieval/bm25_client.py`:**

```python
from elasticsearch import AsyncElasticsearch
from app.core.config import settings

class ElasticsearchBM25Client:
    """
    Persistent BM25 với Elasticsearch.
    Hỗ trợ tiếng Việt: icu_tokenizer + custom analyzer.
    """
    
    INDEX_CONFIG = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "vietnamese_analyzer": {
                        "type": "custom",
                        "tokenizer": "icu_tokenizer",
                        "filter": [
                            "icu_folding",      # Xử lý diacritics (dấu)
                            "lowercase",
                            "vietnamese_stop"   # Stop words tiếng Việt
                        ]
                    }
                },
                "filter": {
                    "vietnamese_stop": {
                        "type": "stop",
                        "stopwords": [
                            "và", "của", "là", "được", "trong", "đã", "có",
                            "với", "này", "những", "đó", "về", "từ", "như",
                            "thì", "để", "cũng", "không", "nhưng", "vào"
                        ]
                    }
                }
            },
            "similarity": {
                "bm25_similarity": {
                    "type": "BM25",
                    "k1": 1.5,   # Tăng lên vì text lịch sử có term frequency cao
                    "b": 0.75
                }
            }
        },
        "mappings": {
            "properties": {
                "content": {
                    "type": "text",
                    "analyzer": "vietnamese_analyzer",
                    "similarity": "bm25_similarity"
                },
                "context_prefix": {
                    "type": "text",
                    "analyzer": "vietnamese_analyzer",
                    "boost": 1.5  # Context prefix quan trọng hơn
                },
                "section_title": {
                    "type": "text",
                    "analyzer": "vietnamese_analyzer",
                    "boost": 2.0  # Title rất quan trọng
                },
                "era": {"type": "keyword"},
                "topics": {"type": "keyword"},
                "entities": {"type": "keyword"},
                "trust_score": {"type": "float"},
                "chunk_id": {"type": "keyword"},
                "document_id": {"type": "keyword"},
            }
        }
    }
    
    def __init__(self):
        self.client = AsyncElasticsearch(settings.elasticsearch_url)
        self.index = settings.elasticsearch_index
    
    async def ensure_index(self):
        exists = await self.client.indices.exists(index=self.index)
        if not exists:
            await self.client.indices.create(
                index=self.index,
                body=self.INDEX_CONFIG
            )
    
    async def index_chunks(self, chunks: list[Chunk]):
        """Bulk index chunks"""
        actions = []
        for chunk in chunks:
            actions.append({
                "_index": self.index,
                "_id": str(chunk.id),
                "_source": {
                    "chunk_id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "content": chunk.content,
                    "context_prefix": chunk.context_prefix,
                    "section_title": chunk.section_title,
                    "era": chunk.era,
                    "topics": chunk.topics,
                    "entities": chunk.entities,
                    "trust_score": chunk.trust_score,
                }
            })
        
        from elasticsearch.helpers import async_bulk
        await async_bulk(self.client, actions)
    
    async def search(
        self, 
        query: str,
        top_k: int = 50,
        era_filter: str | None = None,
        topic_filter: str | None = None
    ) -> list[ScoredChunk]:
        
        # Multi-match query với boosting
        must = [{
            "multi_match": {
                "query": query,
                "fields": [
                    "content",
                    "context_prefix^1.5",
                    "section_title^2.0"
                ],
                "type": "best_fields",
                "fuzziness": "AUTO"  # Hỗ trợ typo nhỏ
            }
        }]
        
        # Entity boost: nếu query có tên nhân vật → boost chunks có entity đó
        entities_in_query = self._extract_query_entities(query)
        if entities_in_query:
            must.append({
                "terms": {
                    "entities": entities_in_query,
                    "boost": 2.0
                }
            })
        
        filter_clauses = []
        if era_filter:
            filter_clauses.append({"term": {"era": era_filter}})
        if topic_filter:
            filter_clauses.append({"term": {"topics": topic_filter}})
        
        query_body = {
            "query": {
                "bool": {
                    "must": must,
                    "filter": filter_clauses
                }
            },
            "size": top_k
        }
        
        response = await self.client.search(index=self.index, body=query_body)
        
        return [
            ScoredChunk(
                chunk_id=hit["_source"]["chunk_id"],
                content=hit["_source"]["content"],
                context_prefix=hit["_source"].get("context_prefix", ""),
                section_title=hit["_source"].get("section_title", ""),
                era=hit["_source"].get("era"),
                entities=hit["_source"].get("entities", []),
                trust_score=hit["_source"].get("trust_score", 0.5),
                score=hit["_score"],
                retrieval_method="sparse"
            )
            for hit in response["hits"]["hits"]
        ]
```

### 5.3 HyDE Query Expansion

**`apps/api/app/retrieval/hyde.py`:**

```python
import anthropic
from app.core.config import settings

class HyDEExpander:
    """
    Hypothetical Document Embedding.
    
    Thay vì embed câu hỏi trực tiếp, generate một "câu trả lời giả định"
    từ sách lịch sử, rồi embed cái đó. Kết quả retrieve tốt hơn nhiều
    với câu hỏi ngắn hoặc không đủ context.
    
    Ví dụ:
        Query: "Trận Đống Đa năm nào?"
        HyDE doc: "Trận Đống Đa diễn ra vào mùa xuân năm Kỷ Dậu (1789),
                   khi Hoàng đế Quang Trung (Nguyễn Huệ) chỉ huy đại quân
                   Tây Sơn đánh bại 29 vạn quân Thanh xâm lược..."
    """
    
    PROMPT_TEMPLATE = """Bạn là một nhà sử học Việt Nam. Hãy viết một đoạn văn ngắn (3-5 câu) 
như thể trích từ sách lịch sử học thuật Việt Nam, cung cấp thông tin về: {query}

Chỉ viết đoạn văn trả lời, không có lời giải thích thêm. 
Viết bằng tiếng Việt, chính xác và học thuật."""
    
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    
    async def expand(self, query: str) -> str:
        """Generate hypothetical document cho query"""
        message = await self.client.messages.create(
            model="claude-haiku-4-5-20251001",  # Dùng Haiku cho nhanh và rẻ
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": self.PROMPT_TEMPLATE.format(query=query)
            }]
        )
        return message.content[0].text
```

### 5.4 Cross-Encoder Reranker

**`apps/api/app/retrieval/reranker.py`:**

```python
from sentence_transformers import CrossEncoder
from app.core.config import settings
import numpy as np

class CrossEncoderReranker:
    """
    Cross-encoder reranking với bge-reranker-v2-m3.
    Model này hỗ trợ tiếng Việt, Chinese, English tốt.
    
    Khác với bi-encoder (embed riêng rồi so sánh), cross-encoder
    nhận (query, passage) cùng lúc → chính xác hơn nhiều nhưng chậm hơn.
    Vì vậy chỉ dùng để rerank top-20 từ hybrid fusion.
    """
    
    MODEL_NAME = "BAAI/bge-reranker-v2-m3"
    
    def __init__(self):
        self.model = CrossEncoder(self.MODEL_NAME)
    
    def rerank(
        self, 
        query: str, 
        chunks: list[ScoredChunk], 
        top_k: int = 8
    ) -> list[ScoredChunk]:
        
        if not chunks:
            return []
        
        # Tạo pairs (query, full_context_chunk)
        pairs = []
        for chunk in chunks:
            # Kết hợp context_prefix + content cho reranking
            full_content = chunk.content
            if chunk.context_prefix:
                full_content = f"{chunk.context_prefix}\n{chunk.content}"
            pairs.append([query, full_content])
        
        # Score tất cả pairs
        scores = self.model.predict(pairs)
        
        # Assign scores và sort
        for chunk, score in zip(chunks, scores):
            chunk.rerank_score = float(score)
            # Kết hợp rerank score + trust score
            chunk.final_score = chunk.rerank_score * 0.8 + chunk.trust_score * 0.2
        
        # Sort và return top_k
        ranked = sorted(chunks, key=lambda c: c.final_score, reverse=True)
        return ranked[:top_k]
```

### 5.5 Hybrid Retriever (Orchestrator)

**`apps/api/app/retrieval/hybrid_retriever.py`:**

```python
from collections import defaultdict
from app.retrieval.vector_client import QdrantVectorClient
from app.retrieval.bm25_client import ElasticsearchBM25Client
from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.hyde import HyDEExpander
from app.ingestion.embedder import ChunkEmbedder

class HybridRetriever:
    """
    Orchestrate toàn bộ retrieval pipeline:
    1. HyDE query expansion
    2. Parallel BM25 + Dense search
    3. Reciprocal Rank Fusion
    4. Cross-encoder reranking
    5. Contextual window expansion
    """
    
    def __init__(self):
        self.vector_client = QdrantVectorClient()
        self.bm25_client = ElasticsearchBM25Client()
        self.reranker = CrossEncoderReranker()
        self.hyde = HyDEExpander()
        self.embedder = ChunkEmbedder()
    
    async def retrieve(
        self,
        query: str,
        era_filter: str | None = None,
        topic_filter: str | None = None,
        top_k: int = 8,
        use_hyde: bool = True
    ) -> list[ScoredChunk]:
        
        # 1. Query expansion với HyDE
        search_query = query
        if use_hyde and len(query.split()) < 10:  # HyDE cho query ngắn
            hyde_doc = await self.hyde.expand(query)
            search_query = f"{query} {hyde_doc}"  # Combine
        
        # 2. Parallel search
        import asyncio
        query_embedding = self.embedder.embed_query(query)
        
        dense_results, sparse_results = await asyncio.gather(
            self.vector_client.search(
                query_vector=query_embedding,
                top_k=50,
                era_filter=era_filter,
                topic_filter=topic_filter
            ),
            self.bm25_client.search(
                query=search_query,
                top_k=50,
                era_filter=era_filter,
                topic_filter=topic_filter
            )
        )
        
        # 3. Reciprocal Rank Fusion
        fused = self._rrf_fusion(dense_results, sparse_results, k=60)
        
        # 4. Deduplicate (chunks từ cùng document quá gần nhau)
        deduped = self._deduplicate(fused)
        
        # 5. Rerank với cross-encoder
        reranked = self.reranker.rerank(query, deduped[:20], top_k=top_k)
        
        return reranked
    
    def _rrf_fusion(
        self, 
        dense: list[ScoredChunk], 
        sparse: list[ScoredChunk],
        k: int = 60
    ) -> list[ScoredChunk]:
        """
        Reciprocal Rank Fusion: score = sum(1 / (k + rank))
        Robust hơn linear combination vì không cần tune weights.
        """
        rrf_scores = defaultdict(float)
        chunk_map = {}
        
        for rank, chunk in enumerate(dense):
            rrf_scores[chunk.chunk_id] += 1.0 / (k + rank + 1)
            chunk_map[chunk.chunk_id] = chunk
        
        for rank, chunk in enumerate(sparse):
            rrf_scores[chunk.chunk_id] += 1.0 / (k + rank + 1)
            if chunk.chunk_id not in chunk_map:
                chunk_map[chunk.chunk_id] = chunk
        
        # Sort by RRF score
        sorted_ids = sorted(rrf_scores.keys(), 
                           key=lambda x: rrf_scores[x], reverse=True)
        
        result = []
        for cid in sorted_ids:
            chunk = chunk_map[cid]
            chunk.rrf_score = rrf_scores[cid]
            result.append(chunk)
        
        return result
    
    def _deduplicate(self, chunks: list[ScoredChunk]) -> list[ScoredChunk]:
        """
        Loại bỏ chunks quá giống nhau (overlap > 80%).
        Ưu tiên giữ chunk có score cao hơn.
        """
        seen_content_hashes = set()
        result = []
        
        for chunk in chunks:
            # Simple hash-based dedup
            content_words = set(chunk.content.lower().split())
            # Kiểm tra overlap với chunks đã chọn
            is_duplicate = False
            for seen_hash in seen_content_hashes:
                # TODO: implement proper Jaccard similarity
                pass
            
            if not is_duplicate:
                content_hash = hash(chunk.content[:100])
                seen_content_hashes.add(content_hash)
                result.append(chunk)
        
        return result
```

### 5.6 Citation Builder

**`apps/api/app/retrieval/citation_builder.py`:**

```python
from dataclasses import dataclass

@dataclass
class Citation:
    index: int              # [1], [2], ... trong response
    chunk_id: str
    document_id: str
    source_title: str       # Tên tài liệu gốc
    source_author: str | None
    publication_year: int | None
    section_title: str | None
    page_ref: str | None
    relevant_excerpt: str   # Đoạn trích ngắn nhất chứng minh claim
    trust_score: float
    era: str | None

class CitationBuilder:
    """
    Map các chunks được dùng trong response về Citations có thể hiển thị.
    """
    
    async def build_citations(
        self, 
        used_chunks: list[ScoredChunk],
        document_repo: DocumentRepository
    ) -> list[Citation]:
        
        citations = []
        for idx, chunk in enumerate(used_chunks):
            doc = await document_repo.get(chunk.document_id)
            
            citation = Citation(
                index=idx + 1,
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                source_title=doc.title if doc else "Không rõ nguồn",
                source_author=doc.author if doc else None,
                publication_year=doc.publication_year if doc else None,
                section_title=chunk.section_title,
                page_ref=chunk.page_ref,
                relevant_excerpt=self._extract_relevant_excerpt(chunk.content, 200),
                trust_score=chunk.trust_score,
                era=chunk.era
            )
            citations.append(citation)
        
        return citations
    
    def _extract_relevant_excerpt(self, content: str, max_chars: int) -> str:
        """Lấy phần quan trọng nhất của chunk để preview"""
        if len(content) <= max_chars:
            return content
        # Lấy từ đầu đến câu hoàn chỉnh gần nhất với max_chars
        truncated = content[:max_chars]
        last_period = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
        if last_period > max_chars * 0.6:
            return content[:last_period + 1]
        return truncated + "..."
```

---

## 6. Phase 3 — Agent Orchestration

**Thời gian:** 3 tuần  
**Mục tiêu:** Agent thực sự reasoning, multi-step, có tool use

### 6.1 Intent Classifier

**`apps/api/app/agents/intent_classifier.py`:**

```python
import anthropic
from enum import Enum
from pydantic import BaseModel
from app.core.config import settings

class QueryIntent(str, Enum):
    FACTUAL_SIMPLE = "factual_simple"      # Khi nào, ai, ở đâu, bao nhiêu
    FACTUAL_COMPLEX = "factual_complex"    # Tại sao, như thế nào
    TIMELINE = "timeline"                   # Diễn biến theo thời gian
    CAUSAL_CHAIN = "causal_chain"          # Nguyên nhân → kết quả
    COMPARATIVE = "comparative"            # So sánh hai thực thể
    BIOGRAPHICAL = "biographical"          # Tiểu sử nhân vật
    GEOGRAPHICAL = "geographical"          # Địa danh, lãnh thổ
    OUT_OF_SCOPE = "out_of_scope"          # Không liên quan lịch sử VN

class ClassificationResult(BaseModel):
    intent: QueryIntent
    confidence: float           # 0.0 – 1.0
    era_hint: str | None        # Gợi ý thời đại nếu detect được
    topic_hint: str | None      # Gợi ý chủ đề
    entities: list[str]         # Nhân vật/địa danh được đề cập
    needs_clarification: bool   # True nếu query quá mơ hồ
    clarification_question: str | None

class IntentClassifier:
    
    SYSTEM_PROMPT = """Bạn phân tích câu hỏi về lịch sử Việt Nam và trả về JSON.

Phân loại intent:
- factual_simple: câu hỏi có 1 câu trả lời ngắn gọn (khi nào, ai, ở đâu)
- factual_complex: cần giải thích chi tiết (tại sao, như thế nào)
- timeline: hỏi về chuỗi sự kiện theo thứ tự thời gian
- causal_chain: hỏi về nguyên nhân–kết quả
- comparative: so sánh hai triều đại, nhân vật, hoặc sự kiện
- biographical: tiểu sử một nhân vật lịch sử cụ thể
- geographical: hỏi về địa danh, lãnh thổ, bản đồ
- out_of_scope: không liên quan đến lịch sử Việt Nam

Era hints: tien_su | bac_thuoc | doc_lap_dau | ly_tran | ho_hau_le | nguyen | hien_dai

Trả về JSON thuần, không có markdown."""
    
    FEW_SHOT_EXAMPLES = """
Q: "Hai Bà Trưng khởi nghĩa năm nào?"
A: {"intent": "factual_simple", "confidence": 0.98, "era_hint": "bac_thuoc", "entities": ["Hai Bà Trưng"], "needs_clarification": false, "clarification_question": null}

Q: "Tại sao nhà Trần có thể đánh bại quân Mông Cổ?"
A: {"intent": "causal_chain", "confidence": 0.95, "era_hint": "ly_tran", "entities": ["Nhà Trần", "Quân Mông Cổ"], "needs_clarification": false, "clarification_question": null}

Q: "So sánh triều Lý và triều Trần"
A: {"intent": "comparative", "confidence": 0.97, "era_hint": null, "entities": ["Triều Lý", "Triều Trần"], "needs_clarification": false, "clarification_question": null}

Q: "Lịch sử chiếc điện thoại"
A: {"intent": "out_of_scope", "confidence": 0.99, "era_hint": null, "entities": [], "needs_clarification": false, "clarification_question": null}
"""
    
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    
    async def classify(self, query: str) -> ClassificationResult:
        import json
        
        message = await self.client.messages.create(
            model="claude-haiku-4-5-20251001",  # Haiku cho fast classification
            max_tokens=300,
            system=self.SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"{self.FEW_SHOT_EXAMPLES}\n\nQ: \"{query}\"\nA:"
            }]
        )
        
        try:
            result = json.loads(message.content[0].text)
            return ClassificationResult(**result)
        except Exception:
            # Fallback nếu JSON parse fail
            return ClassificationResult(
                intent=QueryIntent.FACTUAL_COMPLEX,
                confidence=0.5,
                era_hint=None,
                topic_hint=None,
                entities=[],
                needs_clarification=False,
                clarification_question=None
            )
```

### 6.2 Tool Definitions

**`apps/api/app/agents/tools.py`:**

```python
from typing import Any

AGENT_TOOLS = [
    {
        "name": "retrieve_historical_chunks",
        "description": """Tìm kiếm thông tin lịch sử từ knowledge base.
        
Dùng khi cần: facts, events, nhân vật, địa danh, mô tả sự kiện.
KHÔNG dùng khi đã có đủ thông tin trong context hiện tại.

Khi gọi tool này, query phải cụ thể và rõ ràng nhất có thể.
Ví dụ tốt: "trận Bạch Đằng 938 Ngô Quyền chiến thuật cọc nhọn"
Ví dụ xấu: "lịch sử" (quá chung chung)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query tìm kiếm cụ thể bằng tiếng Việt"
                },
                "era_filter": {
                    "type": "string",
                    "enum": ["tien_su", "bac_thuoc", "doc_lap_dau", 
                             "ly_tran", "ho_hau_le", "nguyen", "hien_dai"],
                    "description": "Lọc theo thời đại (optional)"
                },
                "topic_filter": {
                    "type": "string",
                    "enum": ["chien_tranh", "kinh_te", "van_hoa", 
                             "ngoai_giao", "xa_hoi", "ton_giao"],
                    "description": "Lọc theo chủ đề (optional)"
                },
                "top_k": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Số chunks cần lấy"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_entity_profile",
        "description": """Lấy profile đầy đủ về một nhân vật, triều đại, hoặc địa danh lịch sử.
        
Dùng khi câu hỏi tập trung vào một thực thể cụ thể và cần thông tin toàn diện.
Tốt hơn retrieve_historical_chunks cho biographical/dynasty queries.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "Tên nhân vật/triều đại/địa danh (bất kỳ alias nào)"
                },
                "aspects": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Các khía cạnh cần biết: ['tiểu sử', 'công trạng', 'di sản']"
                }
            },
            "required": ["entity_name"]
        }
    },
    {
        "name": "build_historical_timeline",
        "description": """Xây dựng timeline các sự kiện trong một giai đoạn lịch sử.
        
Dùng cho câu hỏi về diễn biến chronological, chuỗi sự kiện.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_year": {"type": "integer", "description": "Năm bắt đầu (TCN dùng số âm)"},
                "end_year": {"type": "integer", "description": "Năm kết thúc"},
                "topic": {"type": "string", "description": "Chủ đề cần timeline (optional)"},
                "entity": {"type": "string", "description": "Lọc theo nhân vật/triều đại (optional)"}
            },
            "required": ["start_year", "end_year"]
        }
    },
    {
        "name": "compare_subjects",
        "description": """So sánh hai hoặc nhiều thực thể lịch sử theo các khía cạnh cụ thể.
        
Dùng cho câu hỏi so sánh: "so sánh X và Y", "X khác Y như thế nào".""",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject_a": {"type": "string", "description": "Thực thể A"},
                "subject_b": {"type": "string", "description": "Thực thể B"},
                "aspects": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Các khía cạnh so sánh: ['quân sự', 'kinh tế', 'văn hóa']"
                }
            },
            "required": ["subject_a", "subject_b"]
        }
    },
    {
        "name": "check_source_conflict",
        "description": """Kiểm tra khi có sự mâu thuẫn giữa các nguồn tài liệu.

Dùng khi tìm thấy các chunks có thông tin khác nhau về cùng một sự kiện/fact.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim": {"type": "string", "description": "Mệnh đề cần kiểm tra"},
                "context_chunk_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "IDs của chunks đang có conflict"
                }
            },
            "required": ["claim", "context_chunk_ids"]
        }
    }
]
```

### 6.3 Task Planner & Orchestrator

**`apps/api/app/agents/orchestrator.py`:**

```python
import anthropic
import json
from typing import AsyncIterator
from app.core.config import settings
from app.agents.intent_classifier import IntentClassifier, QueryIntent
from app.agents.tool_executor import ToolExecutor
from app.agents.tools import AGENT_TOOLS
from app.retrieval.citation_builder import CitationBuilder

SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên sâu về lịch sử Việt Nam, được xây dựng với tiêu chí 
chính xác và có nguồn gốc rõ ràng.

## Nguyên tắc cốt lõi:

### 1. Chỉ trả lời dựa trên context được cung cấp qua tools
Nếu sau khi dùng tools vẫn không có đủ thông tin, nói rõ:
"Tôi không có đủ tư liệu trong knowledge base để trả lời câu hỏi này một cách chắc chắn."
KHÔNG được bịa đặt hay dùng kiến thức không có trong nguồn.

### 2. Citation bắt buộc cho mọi claim quan trọng
Format: "Theo [TÊN NGUỒN], ..." hoặc thêm số cuối câu [1], [2]...
Mỗi fact cụ thể phải có ít nhất một citation.

### 3. Phân biệt rõ fact vs inference
- "Theo sách X, Ngô Quyền đánh bại Nam Hán năm 938" → FACT
- "Điều này cho thấy chiến lược của ông rất tài tình" → INFERENCE (đánh dấu rõ)
- "Các sử gia còn tranh luận về..." → CONTROVERSIAL (trình bày đa chiều)

### 4. Xử lý conflict giữa nguồn
Nếu hai nguồn mâu thuẫn, trình bày cả hai:
"Sách A ghi [X], trong khi sách B ghi [Y]. Phần lớn sử gia hiện đại chấp nhận..."

### 5. Ngôn ngữ phù hợp với độ chắc chắn
- Chắc chắn: "Ngô Quyền đánh trận Bạch Đằng năm 938"
- Khá chắc: "Nhiều khả năng ..., tuy nhiên cần thêm tư liệu"
- Không chắc: "Một số học giả cho rằng..., nhưng còn tranh luận"

## Quy trình làm việc:

1. Phân tích câu hỏi → xác định cần thông tin gì
2. Gọi tools phù hợp để retrieve thông tin
3. Đánh giá chất lượng và đủ/thiếu của thông tin retrieved
4. Nếu cần, gọi thêm tools (tối đa 5 tool calls)
5. Tổng hợp câu trả lời với đầy đủ citations

## Format câu trả lời:

**[Câu trả lời trực tiếp, ngắn gọn]**

[Giải thích chi tiết với citations]

---
*Nguồn tham khảo:*
- [1] Tên tài liệu, tác giả, năm
- [2] ...

*Bạn có thể hỏi thêm:*
- [Câu hỏi liên quan 1]
- [Câu hỏi liên quan 2]
- [Câu hỏi liên quan 3]"""

class AgentOrchestrator:
    
    MAX_TOOL_CALLS = 5
    
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.intent_classifier = IntentClassifier()
        self.tool_executor = ToolExecutor()
        self.citation_builder = CitationBuilder()
    
    async def stream(
        self,
        query: str,
        session_id: str,
        conversation_history: list[dict]
    ) -> AsyncIterator[dict]:
        """
        Main streaming entry point.
        Yields events: status, token, citation, suggestions, done
        """
        
        # Step 1: Classify intent
        yield {"type": "status", "stage": "classifying", "message": "Phân tích câu hỏi..."}
        
        intent = await self.intent_classifier.classify(query)
        
        if intent.intent == QueryIntent.OUT_OF_SCOPE:
            yield {"type": "token", "content": "Câu hỏi này nằm ngoài phạm vi lịch sử Việt Nam. "}
            yield {"type": "token", "content": "Tôi chỉ có thể hỗ trợ các câu hỏi liên quan đến lịch sử Việt Nam."}
            yield {"type": "done"}
            return
        
        if intent.needs_clarification:
            yield {"type": "token", "content": intent.clarification_question}
            yield {"type": "done"}
            return
        
        # Step 2: Agentic loop với tool use
        yield {"type": "status", "stage": "retrieving", "message": "Tìm kiếm tài liệu..."}
        
        messages = [
            *conversation_history,
            {"role": "user", "content": query}
        ]
        
        all_used_chunks = []
        tool_call_count = 0
        
        # Agentic loop
        while tool_call_count < self.MAX_TOOL_CALLS:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                tools=AGENT_TOOLS,
                messages=messages
            )
            
            if response.stop_reason == "end_turn":
                # Agent đã có đủ thông tin, stream response
                break
            
            if response.stop_reason == "tool_use":
                # Thực thi tools
                tool_results = []
                
                for content_block in response.content:
                    if content_block.type == "tool_use":
                        tool_call_count += 1
                        
                        yield {
                            "type": "status", 
                            "stage": "retrieving",
                            "message": f"Đang tra cứu: {content_block.name}..."
                        }
                        
                        result, chunks = await self.tool_executor.execute(
                            tool_name=content_block.name,
                            tool_input=content_block.input,
                            intent=intent
                        )
                        all_used_chunks.extend(chunks)
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": json.dumps(result, ensure_ascii=False)
                        })
                
                # Thêm vào conversation
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                break
        
        # Step 3: Stream final response
        yield {"type": "status", "stage": "generating", "message": "Tổng hợp câu trả lời..."}
        
        # Final generation với streaming
        async with self.client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=messages
        ) as stream:
            async for text in stream.text_stream:
                yield {"type": "token", "content": text}
        
        # Step 4: Build and yield citations
        citations = await self.citation_builder.build_citations(
            used_chunks=list({c.chunk_id: c for c in all_used_chunks}.values()),
            document_repo=self.tool_executor.document_repo
        )
        
        yield {"type": "citations", "sources": [c.__dict__ for c in citations]}
        
        # Step 5: Suggest follow-up questions
        suggestions = await self._suggest_followups(query, all_used_chunks)
        yield {"type": "suggestions", "questions": suggestions}
        
        yield {"type": "done", "tool_call_count": tool_call_count}
    
    async def _suggest_followups(
        self, 
        query: str, 
        chunks: list
    ) -> list[str]:
        """Generate 3 câu hỏi liên quan dựa trên query và context"""
        entities = list(set(e for c in chunks for e in c.entities))[:3]
        
        # Rule-based follow-ups (nhanh, không tốn token)
        suggestions = []
        if entities:
            suggestions.append(f"Cuộc đời và sự nghiệp của {entities[0]} như thế nào?")
        suggestions.append(f"Bối cảnh lịch sử dẫn đến sự kiện này là gì?")
        suggestions.append("Ảnh hưởng và di sản của sự kiện này đến Việt Nam ngày nay?")
        
        return suggestions[:3]
```

### 6.4 Tool Executor

**`apps/api/app/agents/tool_executor.py`:**

```python
class ToolExecutor:
    """Thực thi các tools mà agent yêu cầu"""
    
    def __init__(self):
        self.retriever = HybridRetriever()
        self.document_repo = DocumentRepository()
    
    async def execute(
        self, 
        tool_name: str, 
        tool_input: dict,
        intent: ClassificationResult
    ) -> tuple[dict, list[ScoredChunk]]:
        """
        Returns: (result_dict để trả về agent, list chunks để build citations)
        """
        
        handlers = {
            "retrieve_historical_chunks": self._retrieve_chunks,
            "get_entity_profile": self._get_entity_profile,
            "build_historical_timeline": self._build_timeline,
            "compare_subjects": self._compare_subjects,
            "check_source_conflict": self._check_conflict,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}, []
        
        return await handler(tool_input, intent)
    
    async def _retrieve_chunks(
        self, tool_input: dict, intent: ClassificationResult
    ) -> tuple[dict, list[ScoredChunk]]:
        
        chunks = await self.retriever.retrieve(
            query=tool_input["query"],
            era_filter=tool_input.get("era_filter", intent.era_hint),
            topic_filter=tool_input.get("topic_filter", intent.topic_hint),
            top_k=tool_input.get("top_k", 5)
        )
        
        result = {
            "chunks": [
                {
                    "content": c.content,
                    "context_prefix": c.context_prefix,
                    "section_title": c.section_title,
                    "era": c.era,
                    "entities": c.entities,
                    "relevance_score": round(c.final_score, 3),
                    "chunk_id": c.chunk_id
                }
                for c in chunks
            ],
            "total_found": len(chunks)
        }
        
        return result, chunks
    
    async def _build_timeline(
        self, tool_input: dict, intent: ClassificationResult
    ) -> tuple[dict, list[ScoredChunk]]:
        
        # Retrieve chunks trong khoảng thời gian
        query = f"lịch sử Việt Nam {tool_input['start_year']} đến {tool_input['end_year']}"
        if topic := tool_input.get("topic"):
            query += f" {topic}"
        
        chunks = await self.retriever.retrieve(query=query, top_k=10)
        
        # Sort theo date references
        events = []
        for chunk in chunks:
            for date_ref in chunk.date_refs:
                year = self._parse_year(date_ref)
                if year and tool_input["start_year"] <= year <= tool_input["end_year"]:
                    events.append({
                        "year": year,
                        "event_summary": chunk.content[:200],
                        "source": chunk.section_title,
                        "chunk_id": chunk.chunk_id
                    })
        
        events.sort(key=lambda x: x["year"])
        return {"timeline": events, "period": f"{tool_input['start_year']}–{tool_input['end_year']}"}, chunks
```

---

## 7. Phase 4 — API & Streaming

**Thời gian:** 1 tuần  
**Mục tiêu:** Endpoints thật, streaming đúng protocol

### 7.1 Query Route

**`apps/api/app/routes/query.py`:**

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import json
import asyncio

router = APIRouter(prefix="/api/v1", tags=["query"])

class QueryRequest(BaseModel):
    query: str
    session_id: str
    era_filter: str | None = None
    topic_filter: str | None = None

class FeedbackRequest(BaseModel):
    session_id: str
    message_id: str
    rating: int      # 1–5
    comment: str | None = None

@router.post("/query/stream")
async def query_stream(
    request: QueryRequest,
    current_user: User = Depends(get_current_user_optional),  # Optional auth
    db: AsyncSession = Depends(get_db)
):
    """
    SSE Streaming endpoint.
    
    Event protocol:
    - {"type": "status",      "stage": "classifying|retrieving|generating", "message": "..."}
    - {"type": "token",       "content": "..."}
    - {"type": "citations",   "sources": [...]}
    - {"type": "suggestions", "questions": [...]}
    - {"type": "error",       "message": "..."}
    - {"type": "done",        "metadata": {...}}
    """
    
    # Validate query
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query không được để trống")
    
    if len(request.query) > 2000:
        raise HTTPException(status_code=400, detail="Query quá dài (max 2000 ký tự)")
    
    orchestrator = AgentOrchestrator()
    history_service = ConversationHistoryService(db)
    
    async def event_generator():
        try:
            # Load conversation history
            history = await history_service.get_messages(
                session_id=request.session_id,
                limit=10  # Chỉ lấy 10 messages gần nhất
            )
            
            full_response = []
            citations = []
            
            async for event in orchestrator.stream(
                query=request.query,
                session_id=request.session_id,
                conversation_history=history
            ):
                # Send event via SSE
                yield {
                    "event": "message",
                    "data": json.dumps(event, ensure_ascii=False)
                }
                
                # Collect for saving to history
                if event["type"] == "token":
                    full_response.append(event["content"])
                elif event["type"] == "citations":
                    citations = event["sources"]
            
            # Save to conversation history
            await history_service.save_exchange(
                session_id=request.session_id,
                user_message=request.query,
                assistant_message="".join(full_response),
                citations=citations,
                user_id=current_user.id if current_user else None
            )
            
        except Exception as e:
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "error",
                    "message": "Đã xảy ra lỗi. Vui lòng thử lại."
                })
            }
            # Log error properly
            import logging
            logging.error(f"Stream error for session {request.session_id}: {e}", exc_info=True)
    
    return EventSourceResponse(event_generator())


@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Thu thập feedback để cải thiện hệ thống"""
    feedback_service = FeedbackService(db)
    await feedback_service.save(feedback)
    return {"status": "ok"}


@router.get("/sessions/{session_id}/history")
async def get_history(
    session_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Lấy lịch sử conversation của một session"""
    history_service = ConversationHistoryService(db)
    messages = await history_service.get_messages(session_id, limit)
    return {"messages": messages, "session_id": session_id}
```

### 7.2 Ingestion Route

**`apps/api/app/routes/ingest.py`:**

```python
@router.post("/ingest/url")
async def ingest_from_url(request: IngestURLRequest, ...):
    """Ingest tài liệu từ URL"""
    doc = await ingest_service.create_from_url(request.url, request.metadata)
    process_document.delay(str(doc.id))  # Celery async
    return {"document_id": str(doc.id), "status": "queued"}

@router.post("/ingest/file")
async def ingest_from_file(file: UploadFile, ...):
    """Ingest tài liệu từ file upload (PDF, TXT, JSON)"""
    # Validate file type và size
    if file.content_type not in ["application/pdf", "text/plain", "application/json"]:
        raise HTTPException(400, "Chỉ hỗ trợ PDF, TXT, JSON")
    if file.size > 50_000_000:  # 50MB max
        raise HTTPException(400, "File quá lớn (max 50MB)")
    
    doc = await ingest_service.create_from_file(file)
    process_document.delay(str(doc.id))
    return {"document_id": str(doc.id), "status": "queued"}

@router.get("/ingest/{document_id}/status")
async def get_ingest_status(document_id: str, ...):
    """Check trạng thái ingestion"""
    doc = await document_repo.get(document_id)
    return {
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "error": doc.error_message
    }
```

---

## 8. Phase 5 — Frontend

**Thời gian:** 2 tuần  
**Mục tiêu:** UI hoàn chỉnh, citation system, streaming UX

### 8.1 Zustand Store (Unified)

**`apps/web/src/stores/chatStore.ts`:**

```typescript
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export interface Citation {
  index: number;
  chunk_id: string;
  source_title: string;
  source_author: string | null;
  publication_year: number | null;
  section_title: string | null;
  page_ref: string | null;
  relevant_excerpt: string;
  trust_score: number;
  era: string | null;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  suggestions?: string[];
  timestamp: Date;
  isStreaming?: boolean;
}

export type StreamingStage = 'idle' | 'classifying' | 'retrieving' | 'generating';

interface StreamingState {
  isStreaming: boolean;
  stage: StreamingStage;
  stageMessage: string;
  tokenBuffer: string;
}

interface ChatStore {
  messages: Message[];
  sessionId: string;
  streamingState: StreamingState;
  abortController: AbortController | null;
  
  // Actions
  sendMessage: (query: string) => Promise<void>;
  abortStream: () => void;
  clearHistory: () => void;
  setSessionId: (id: string) => void;
}

export const useChatStore = create<ChatStore>()(
  devtools((set, get) => ({
    messages: [],
    sessionId: crypto.randomUUID(),
    streamingState: {
      isStreaming: false,
      stage: 'idle',
      stageMessage: '',
      tokenBuffer: '',
    },
    abortController: null,
    
    sendMessage: async (query: string) => {
      const { sessionId } = get();
      
      // Add user message
      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content: query,
        timestamp: new Date(),
      };
      
      // Add empty assistant message (will be filled by stream)
      const assistantMessageId = crypto.randomUUID();
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      };
      
      set(state => ({
        messages: [...state.messages, userMessage, assistantMessage],
        streamingState: {
          isStreaming: true,
          stage: 'classifying',
          stageMessage: 'Phân tích câu hỏi...',
          tokenBuffer: '',
        }
      }));
      
      // Create abort controller
      const controller = new AbortController();
      set({ abortController: controller });
      
      try {
        const response = await fetch('/api/v1/query/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, session_id: sessionId }),
          signal: controller.signal,
        });
        
        if (!response.ok) throw new Error('Stream request failed');
        
        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            
            try {
              const event = JSON.parse(line.slice(6));
              
              switch (event.type) {
                case 'status':
                  set(state => ({
                    streamingState: {
                      ...state.streamingState,
                      stage: event.stage,
                      stageMessage: event.message,
                    }
                  }));
                  break;
                  
                case 'token':
                  set(state => {
                    const newBuffer = state.streamingState.tokenBuffer + event.content;
                    return {
                      streamingState: {
                        ...state.streamingState,
                        stage: 'generating',
                        tokenBuffer: newBuffer,
                      },
                      messages: state.messages.map(m =>
                        m.id === assistantMessageId
                          ? { ...m, content: newBuffer }
                          : m
                      )
                    };
                  });
                  break;
                  
                case 'citations':
                  set(state => ({
                    messages: state.messages.map(m =>
                      m.id === assistantMessageId
                        ? { ...m, citations: event.sources }
                        : m
                    )
                  }));
                  break;
                  
                case 'suggestions':
                  set(state => ({
                    messages: state.messages.map(m =>
                      m.id === assistantMessageId
                        ? { ...m, suggestions: event.questions }
                        : m
                    )
                  }));
                  break;
                  
                case 'error':
                  set(state => ({
                    messages: state.messages.map(m =>
                      m.id === assistantMessageId
                        ? { ...m, content: 'Đã xảy ra lỗi. Vui lòng thử lại.', isStreaming: false }
                        : m
                    )
                  }));
                  break;
                  
                case 'done':
                  set(state => ({
                    messages: state.messages.map(m =>
                      m.id === assistantMessageId
                        ? { ...m, isStreaming: false }
                        : m
                    ),
                    streamingState: {
                      isStreaming: false,
                      stage: 'idle',
                      stageMessage: '',
                      tokenBuffer: '',
                    }
                  }));
                  break;
              }
            } catch {
              // Skip malformed events
            }
          }
        }
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        
        set(state => ({
          messages: state.messages.map(m =>
            m.id === assistantMessageId
              ? { ...m, content: 'Kết nối bị gián đoạn. Vui lòng thử lại.', isStreaming: false }
              : m
          ),
          streamingState: { isStreaming: false, stage: 'idle', stageMessage: '', tokenBuffer: '' }
        }));
      } finally {
        set({ abortController: null });
      }
    },
    
    abortStream: () => {
      const { abortController } = get();
      abortController?.abort();
      set(state => ({
        messages: state.messages.map(m =>
          m.isStreaming ? { ...m, isStreaming: false } : m
        ),
        streamingState: { isStreaming: false, stage: 'idle', stageMessage: '', tokenBuffer: '' }
      }));
    },
    
    clearHistory: () => set({ messages: [], sessionId: crypto.randomUUID() }),
    setSessionId: (id) => set({ sessionId: id }),
  }))
);
```

### 8.2 Citation Component

**`apps/web/src/components/chat/CitationInline.tsx`:**

```tsx
import React, { useState } from 'react';
import type { Citation } from '@/stores/chatStore';

interface Props {
  citation: Citation;
}

export const CitationInline: React.FC<Props> = ({ citation }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  const eraLabels: Record<string, string> = {
    tien_su: 'Tiền sử',
    bac_thuoc: 'Bắc thuộc',
    ly_tran: 'Lý–Trần',
    ho_hau_le: 'Hậu Lê',
    nguyen: 'Triều Nguyễn',
    hien_dai: 'Hiện đại',
  };
  
  return (
    <span className="relative inline-block">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="citation-marker text-xs font-medium text-blue-600 hover:text-blue-800 
                   bg-blue-50 hover:bg-blue-100 rounded px-1 transition-colors"
        aria-label={`Xem nguồn ${citation.index}: ${citation.source_title}`}
      >
        [{citation.index}]
      </button>
      
      {isOpen && (
        <div className="citation-popover absolute z-50 bottom-full left-0 mb-2 w-80
                        bg-white border border-gray-200 rounded-lg shadow-lg p-4">
          {/* Header */}
          <div className="flex items-start justify-between mb-2">
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-sm text-gray-900 truncate">
                {citation.source_title}
              </h4>
              {citation.source_author && (
                <p className="text-xs text-gray-500">
                  {citation.source_author}
                  {citation.publication_year && `, ${citation.publication_year}`}
                </p>
              )}
            </div>
            <button 
              onClick={() => setIsOpen(false)}
              className="text-gray-400 hover:text-gray-600 ml-2 flex-shrink-0"
            >
              ✕
            </button>
          </div>
          
          {/* Metadata badges */}
          <div className="flex flex-wrap gap-1 mb-3">
            {citation.era && (
              <span className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full">
                {eraLabels[citation.era] || citation.era}
              </span>
            )}
            {citation.section_title && (
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                {citation.section_title}
              </span>
            )}
            {citation.page_ref && (
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                Trang {citation.page_ref}
              </span>
            )}
          </div>
          
          {/* Excerpt */}
          <blockquote className="text-xs text-gray-700 bg-gray-50 rounded p-2 
                                  border-l-2 border-amber-400 italic">
            "{citation.relevant_excerpt}"
          </blockquote>
          
          {/* Trust score */}
          <div className="mt-2 flex items-center gap-1">
            <span className="text-xs text-gray-400">Độ tin cậy:</span>
            <div className="flex gap-0.5">
              {[1,2,3,4,5].map(i => (
                <div 
                  key={i}
                  className={`w-2 h-2 rounded-full ${
                    i <= Math.round(citation.trust_score * 5) 
                      ? 'bg-green-400' 
                      : 'bg-gray-200'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </span>
  );
};
```

### 8.3 Thinking Indicator

**`apps/web/src/components/chat/ThinkingIndicator.tsx`:**

```tsx
import React from 'react';
import type { StreamingStage } from '@/stores/chatStore';

const STAGE_CONFIG: Record<StreamingStage, { icon: string; label: string; color: string }> = {
  idle: { icon: '', label: '', color: '' },
  classifying: { 
    icon: '🔍', 
    label: 'Phân tích câu hỏi...', 
    color: 'text-blue-600'
  },
  retrieving: { 
    icon: '📚', 
    label: 'Tìm kiếm tài liệu lịch sử...', 
    color: 'text-amber-600'
  },
  generating: { 
    icon: '✍️', 
    label: 'Tổng hợp câu trả lời...', 
    color: 'text-green-600'
  },
};

interface Props {
  stage: StreamingStage;
  message?: string;
}

export const ThinkingIndicator: React.FC<Props> = ({ stage, message }) => {
  if (stage === 'idle') return null;
  
  const config = STAGE_CONFIG[stage];
  
  return (
    <div className="flex items-center gap-2 text-sm py-1">
      <span className="text-base">{config.icon}</span>
      <span className={config.color}>
        {message || config.label}
      </span>
      <span className="flex gap-0.5">
        {[0, 1, 2].map(i => (
          <span
            key={i}
            className={`w-1 h-1 rounded-full bg-current animate-bounce`}
            style={{ animationDelay: `${i * 150}ms` }}
          />
        ))}
      </span>
    </div>
  );
};
```

---

## 9. Phase 6 — Testing & Evaluation

**Thời gian:** Song song với các phase khác  
**Mục tiêu:** Test coverage > 70%, eval pipeline tự động

### 9.1 Unit Tests — Backend

**`apps/api/tests/unit/test_chunker.py`:**

```python
import pytest
from app.ingestion.chunker import VietnameseHistoricalChunker

class TestVietnameseHistoricalChunker:
    
    @pytest.fixture
    def chunker(self):
        return VietnameseHistoricalChunker()
    
    def test_basic_chunking(self, chunker):
        """Đảm bảo chunker tạo ra chunks hợp lệ"""
        doc = ExtractedDocument(
            sections=[Section(
                title="Trận Bạch Đằng",
                content="Năm 938, Ngô Quyền đã dùng kế cắm cọc nhọn xuống lòng sông Bạch Đằng. "
                        "Khi thủy triều lên, quân ta nhử địch vào. Khi triều rút, thuyền địch "
                        "bị cọc đâm thủng. Quân Nam Hán đại bại."
            )]
        )
        
        chunks = chunker.chunk_document(doc)
        
        assert len(chunks) >= 1
        assert all(c.content for c in chunks)
        assert all(c.section_title == "Trận Bạch Đằng" for c in chunks)
    
    def test_context_prefix_included(self, chunker):
        """Context prefix phải được gắn vào mỗi chunk"""
        doc = ExtractedDocument(
            sections=[Section(
                title="Kháng chiến chống Mông Cổ",
                content="Lần 1 (1258): " + "Quân Mông Cổ xâm lược. " * 30
            )]
        )
        
        chunks = chunker.chunk_document(doc)
        
        assert all(c.context_prefix for c in chunks)
        assert "Kháng chiến" in chunks[0].context_prefix
    
    def test_no_sentence_split(self, chunker):
        """Chunker không được cắt giữa câu"""
        text = "Câu một hoàn chỉnh. Câu hai hoàn chỉnh. Câu ba hoàn chỉnh."
        doc = ExtractedDocument(sections=[Section(title="Test", content=text)])
        
        chunks = chunker.chunk_document(doc)
        
        for chunk in chunks:
            # Mỗi chunk phải kết thúc bằng dấu câu
            assert chunk.content.strip()[-1] in ".!?…"
    
    def test_era_detection(self, chunker):
        """Era phải được detect chính xác"""
        doc = ExtractedDocument(sections=[Section(
            title="Test",
            content="Năm 938, Ngô Quyền đánh bại quân Nam Hán."
        )])
        
        chunks = chunker.chunk_document(doc)
        assert any(c.era == "doc_lap_dau" for c in chunks)
    
    def test_entity_extraction(self, chunker):
        """Entities phải được extract"""
        doc = ExtractedDocument(sections=[Section(
            title="Test",
            content="Trần Quốc Tuấn (Hưng Đạo Vương) chỉ huy quân Trần."
        )])
        
        chunks = chunker.chunk_document(doc)
        assert "Trần Quốc Tuấn" in chunks[0].entities
```

**`apps/api/tests/integration/test_retrieval.py`:**

```python
import pytest
import asyncio

@pytest.mark.asyncio
class TestHybridRetrieval:
    
    async def test_hai_ba_trung_retrieval(self, retriever):
        """Câu hỏi về Hai Bà Trưng phải trả về chunks liên quan"""
        chunks = await retriever.retrieve("Hai Bà Trưng khởi nghĩa năm nào?")
        
        assert len(chunks) >= 3
        # Phải có chunks đề cập đến năm 40 hoặc Trưng Trắc
        relevant = [c for c in chunks 
                   if "40" in c.content or "Trưng Trắc" in c.content 
                   or "Trưng Nhị" in c.content]
        assert len(relevant) >= 1
    
    async def test_entity_alias_retrieval(self, retriever):
        """'Lê Lợi' và 'Lê Thái Tổ' phải cho kết quả tương đương"""
        chunks_a = await retriever.retrieve("Lê Lợi lập triều đại nào?")
        chunks_b = await retriever.retrieve("Lê Thái Tổ lập triều đại nào?")
        
        sources_a = {c.chunk_id for c in chunks_a}
        sources_b = {c.chunk_id for c in chunks_b}
        
        # Jaccard similarity > 0.3 (alias handling hoạt động)
        intersection = len(sources_a & sources_b)
        union = len(sources_a | sources_b)
        assert intersection / union > 0.3
    
    async def test_era_filter(self, retriever):
        """Era filter phải hoạt động đúng"""
        chunks = await retriever.retrieve(
            "các trận chiến lớn",
            era_filter="ly_tran"
        )
        
        # Tất cả chunks trả về phải thuộc thời Lý–Trần
        assert all(c.era == "ly_tran" or c.era is None for c in chunks)
    
    async def test_retrieval_relevance_scores(self, retriever):
        """Chunks phải được sort theo relevance"""
        chunks = await retriever.retrieve("trận Đống Đa Quang Trung")
        
        # Chunks phải có score giảm dần
        scores = [c.final_score for c in chunks]
        assert scores == sorted(scores, reverse=True)
    
    async def test_no_hallucination_context(self, retriever):
        """Query không có trong KB phải trả về ít/không có kết quả"""
        # "Hồ Chí Minh du lịch Nhật Bản" không phải sự kiện lịch sử
        chunks = await retriever.retrieve(
            "Hồ Chí Minh đi du lịch Nhật Bản năm 1952"
        )
        # Hoặc không có chunks, hoặc chunks không liên quan
        if chunks:
            top_score = chunks[0].final_score
            assert top_score < 0.5  # Score thấp = không liên quan
```

### 9.2 Golden Dataset Strategy

#### Golden Dataset là gì?

Golden dataset là tập hợp các câu hỏi-đáp chuẩn để đánh giá chất lượng hệ thống. Mỗi entry gồm:
- `question`: Câu hỏi test
- `ground_truth`: Câu trả lời đúng (human-verified)
- `expected_sources`: Nguồn cần retrieve được
- `era`: Thời kỳ lịch sử
- `difficulty`: easy/medium/hard

#### Golden Dataset Structure

```json
// evals/golden_dataset.json
{
  "version": "1.0",
  "total_questions": 200,
  "created_at": "2026-05-19",
  "questions": [
    {
      "id": "g001",
      "question": "Ai là người lãnh đạo cuộc khởi nghĩa Hai Bà Trưng năm 40 sau CN?",
      "ground_truth": "Trưng Trắc và Trưng Nhị là hai chị em gái cai trị quận Giao Chỉ, khởi nghĩa năm 40 sau CN chống ách đô hộ của nhà Hán.",
      "expected_sources": ["Wikipedia: Hai Bà Trưng", "SGK 10: Chương 3"],
      "era": "bac_thuoc",
      "difficulty": "easy",
      "category": "event"
    },
    {
      "id": "g002",
      "question": "Trình bày ý nghĩa lịch sử của Chiến thắng Điện Biên Phủ 1954.",
      "ground_truth": "Chiến thắng Điện Biên Phủ (7/5/1954) kết thúc thắng lợi cuộc kháng chiến chống Pháp, buộc Pháp ký Hiệp định Genève, công nhận độc lập của các nước Đông Dương.",
      "expected_sources": ["Wikipedia: Trận Điện Biên Phủ", "SGK 12: Chương 23"],
      "era": "hien_dai",
      "difficulty": "medium",
      "category": "analysis"
    }
  ]
}
```

#### Golden Dataset Coverage

| Era | Questions | Percentage |
|-----|-----------|------------|
| Tiền sử | 10 | 5% |
| Bắc thuộc | 20 | 10% |
| Ngô-Đinh-Tiền Lê | 20 | 10% |
| Lý-Trần | 40 | 20% |
| Hồ-Hậu Lê-Mạc | 30 | 15% |
| Nguyễn | 40 | 20% |
| Hiện đại (1945-1975) | 40 | 20% |

#### Question Categories

| Category | Description | Sample Questions |
|----------|-------------|------------------|
| `fact` | Hỏi sự kiện cụ thể | "Ai là vua đầu tiên của nhà Lý?" |
| `comparison` | So sánh sự kiện | "So sánh khởi nghĩa Bạch Đằng và Bắc thuộc" |
| `timeline` | Xác định thứ tự | "Sắp xếp các triều đại theo thứ tự" |
| `analysis` | Phân tích ý nghĩa | "Ý nghĩa của Tổng tiến công Tết Mậu Thân?" |
| `entity` | Về nhân vật/địa danh | "Trần Hưng Đạo là ai?" |

#### Golden Dataset Creation Process

| Phase | Tasks | Owner | Week |
|-------|-------|-------|------|
| v0.1 MVP | Tạo 50 câu hỏi cơ bản | User | 2 |
| v0.3 | Thêm 50 câu (medium difficulty) | User | 6 |
| v0.5 | Thêm 50 câu (hard + analysis) | User + AI | 10 |
| v1.0 | Review + finalize 200 câu | Expert | 14 |

#### Automated Eval Triggers

```yaml
# .github/workflows/eval.yml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  ragas-eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run RAGAS Evaluation
        run: python evals/run_ragas.py --threshold 0.75
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### 9.3 RAGAS Evaluation Pipeline

**`evals/run_ragas.py`:**

```python
"""
RAGAS Evaluation Pipeline.
Chạy: python evals/run_ragas.py --threshold 0.80
"""

import asyncio
import json
import argparse
from pathlib import Path
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,        # Câu trả lời có dựa trên context không?
    answer_relevancy,   # Câu trả lời có trả lời đúng câu hỏi không?
    context_recall,     # Context retrieved có đủ thông tin không?
    context_precision,  # Context retrieved có precision không?
)

async def run_evaluation(threshold: float = 0.80):
    # Load golden dataset
    golden_path = Path("evals/golden_dataset.json")
    golden_data = json.loads(golden_path.read_text(encoding="utf-8"))
    
    questions = []
    answers = []
    contexts_list = []
    ground_truths = []
    
    # Chạy hệ thống trên từng câu hỏi
    from app.agents.orchestrator import AgentOrchestrator
    from app.retrieval.hybrid_retriever import HybridRetriever
    
    retriever = HybridRetriever()
    
    for item in golden_data[:50]:  # Test trên 50 câu đầu (full run = 200)
        query = item["question"]
        
        # Retrieve context
        chunks = await retriever.retrieve(query, top_k=5)
        contexts = [c.content for c in chunks]
        
        # Generate answer (non-streaming for eval)
        # TODO: implement non-streaming version
        answer = item.get("generated_answer", "")
        
        questions.append(query)
        answers.append(answer)
        contexts_list.append(contexts)
        ground_truths.append(item["ground_truth"])
    
    # Build dataset
    data = {
        "question": questions,
        "answer": answers,
        "contexts": contexts_list,
        "ground_truth": ground_truths,
    }
    dataset = Dataset.from_dict(data)
    
    # Evaluate
    results = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_recall, context_precision]
    )
    
    print("\n=== RAGAS Evaluation Results ===")
    print(f"Faithfulness:     {results['faithfulness']:.3f}  (target: >{threshold})")
    print(f"Answer Relevancy: {results['answer_relevancy']:.3f}  (target: >{threshold})")
    print(f"Context Recall:   {results['context_recall']:.3f}")
    print(f"Context Precision:{results['context_precision']:.3f}")
    
    # Check thresholds
    failed = []
    if results["faithfulness"] < threshold:
        failed.append(f"faithfulness={results['faithfulness']:.3f} < {threshold}")
    if results["answer_relevancy"] < threshold:
        failed.append(f"answer_relevancy={results['answer_relevancy']:.3f} < {threshold}")
    
    if failed:
        print(f"\n❌ FAILED: {', '.join(failed)}")
        exit(1)
    else:
        print(f"\n✅ PASSED: All metrics above threshold {threshold}")
    
    # Save results
    output = {
        "timestamp": str(asyncio.get_event_loop().time()),
        "metrics": dict(results),
        "threshold": threshold,
        "passed": len(failed) == 0
    }
    Path("evals/latest_results.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False)
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.80)
    args = parser.parse_args()
    asyncio.run(run_evaluation(args.threshold))
```

### 9.3 Golden Dataset Structure

**`evals/golden_dataset.json`** (200 câu):

```json
[
  {
    "id": "001",
    "category": "factual_simple",
    "era": "bac_thuoc",
    "question": "Hai Bà Trưng khởi nghĩa vào năm nào?",
    "ground_truth": "Hai Bà Trưng khởi nghĩa vào năm 40 SCN, lật đổ ách đô hộ của nhà Hán.",
    "expected_entities": ["Trưng Trắc", "Trưng Nhị"],
    "expected_years": ["40"],
    "difficulty": "easy"
  },
  {
    "id": "002",
    "category": "causal_chain",
    "era": "ly_tran",
    "question": "Tại sao quân Mông Cổ thất bại trong ba lần xâm lược Đại Việt?",
    "ground_truth": "Quân Mông Cổ thất bại do chiến thuật vườn không nhà trống, địa hình không thuận lợi cho kỵ binh, thủy quân yếu, và tinh thần kháng chiến của quân dân Đại Việt dưới sự lãnh đạo của Trần Hưng Đạo.",
    "expected_entities": ["Trần Quốc Tuấn", "Quân Mông Cổ", "Triều Trần"],
    "expected_years": ["1258", "1285", "1288"],
    "difficulty": "medium"
  },
  {
    "id": "003",
    "category": "comparative",
    "era": null,
    "question": "So sánh triều Lý và triều Trần về văn hóa và quân sự",
    "ground_truth": "Triều Lý (1009-1225) nổi bật với phát triển Phật giáo, xây dựng Văn Miếu, thiết lập kinh đô Thăng Long. Triều Trần (1225-1400) kế thừa và phát triển, đặc biệt nổi bật với ba lần đánh bại quân Mông Cổ, phát triển chữ Nôm, và hệ thống quân sự mạnh mẽ.",
    "expected_entities": ["Triều Lý", "Triều Trần"],
    "difficulty": "hard"
  }
]
```

---

## 10. Phase 7 — Infrastructure & Observability

**Thời gian:** 1 tuần  
**Mục tiêu:** Production-ready, observable, maintainable

### 10.1 Docker Compose — Full Stack

**`docker-compose.yml`:**

```yaml
version: '3.9'

services:
  api:
    build:
      context: ./apps/api
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - POSTGRES_URL=postgresql+asyncpg://postgres:password@postgres:5432/vie_history
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
      - ELASTICSEARCH_URL=http://elasticsearch:9200
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    volumes:
      - ./apps/api:/app
      - ./data:/app/data
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_started
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build:
      context: ./apps/api
      dockerfile: Dockerfile
    environment:
      - ENVIRONMENT=development
      - POSTGRES_URL=postgresql+asyncpg://postgres:password@postgres:5432/vie_history
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
      - ELASTICSEARCH_URL=http://elasticsearch:9200
      - CELERY_BROKER_URL=redis://redis:6379/1
    volumes:
      - ./apps/api:/app
      - ./data:/app/data
      - ./storage:/app/storage
    depends_on: [postgres, redis, qdrant, elasticsearch]
    command: celery -A app.workers.celery_app worker -Q ingestion,embedding --loglevel=info --concurrency=2

  flower:
    build: ./apps/api
    ports:
      - "5555:5555"
    depends_on: [redis]
    command: celery -A app.workers.celery_app flower --port=5555
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1

  web:
    build:
      context: ./apps/web
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - ./apps/web/src:/app/src
    environment:
      - VITE_API_URL=http://localhost:8000

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: vie_history
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"  # gRPC

  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 10s
      timeout: 10s
      retries: 10

  # LLM Observability
  langfuse:
    image: ghcr.io/langfuse/langfuse:latest
    ports:
      - "3001:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/langfuse
      - NEXTAUTH_URL=http://localhost:3001
      - NEXTAUTH_SECRET=your-langfuse-secret
    depends_on: [postgres]

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  es_data:
```

### 10.2 Langfuse Integration — LLM Observability

**`apps/api/app/core/observability.py`:**

```python
from langfuse import Langfuse
from langfuse.decorators import langfuse_context, observe
from app.core.config import settings

langfuse = Langfuse(
    secret_key=settings.langfuse_secret_key,
    public_key=settings.langfuse_public_key,
    host=settings.langfuse_host
) if settings.langfuse_secret_key else None

def trace_query(session_id: str, query: str, user_id: str | None = None):
    """Tạo trace cho một query"""
    if not langfuse:
        return None
    
    return langfuse.trace(
        name="history_query",
        session_id=session_id,
        user_id=user_id,
        input=query,
        tags=["production"]
    )

def log_retrieval(trace, query: str, chunks: list, latency_ms: int):
    """Log retrieval results"""
    if not trace:
        return
    
    trace.span(
        name="hybrid_retrieval",
        input={"query": query},
        output={
            "chunk_count": len(chunks),
            "top_score": chunks[0].final_score if chunks else 0,
            "eras": list(set(c.era for c in chunks if c.era))
        },
        metadata={"latency_ms": latency_ms}
    )

def log_llm_generation(trace, model: str, input_tokens: int, 
                        output_tokens: int, latency_ms: int):
    """Log LLM call"""
    if not trace:
        return
    
    trace.generation(
        name="claude_generation",
        model=model,
        usage={
            "input": input_tokens,
            "output": output_tokens,
            "unit": "TOKENS"
        },
        metadata={"latency_ms": latency_ms}
    )
```

### 10.3 Metrics & Alerting

**`apps/api/app/core/metrics.py`:**

```python
from prometheus_client import Counter, Histogram, Gauge

# Query metrics
QUERY_TOTAL = Counter(
    "vie_history_queries_total",
    "Total queries processed",
    ["intent", "era", "status"]
)

QUERY_LATENCY = Histogram(
    "vie_history_query_latency_seconds",
    "Query latency in seconds",
    ["stage"],  # classifying, retrieving, generating
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Retrieval metrics
RETRIEVAL_CHUNKS = Histogram(
    "vie_history_retrieval_chunks",
    "Number of chunks retrieved",
    buckets=[1, 3, 5, 8, 10, 15, 20]
)

RETRIEVAL_TOP_SCORE = Histogram(
    "vie_history_retrieval_top_score",
    "Top chunk relevance score",
    buckets=[0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0]
)

# Ingestion metrics
DOCUMENTS_INGESTED = Counter(
    "vie_history_documents_ingested_total",
    "Total documents ingested",
    ["status", "source_type"]
)

CHUNKS_INDEXED = Counter(
    "vie_history_chunks_indexed_total",
    "Total chunks indexed"
)

# LLM metrics
LLM_TOKENS = Counter(
    "vie_history_llm_tokens_total",
    "Total LLM tokens used",
    ["model", "type"]  # type: input | output
)

# System health
KB_SIZE = Gauge(
    "vie_history_kb_chunks_total",
    "Total chunks in knowledge base"
)
```

---

## 11. Database Schema

```sql
-- Tạo enums
CREATE TYPE document_status AS ENUM (
    'pending', 'extracting', 'cleaning', 'chunking', 
    'embedding', 'indexing', 'completed', 'failed'
);

CREATE TYPE historical_era AS ENUM (
    'tien_su', 'bac_thuoc', 'doc_lap_dau', 
    'ly_tran', 'ho_hau_le', 'nguyen', 'hien_dai'
);

-- Documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    source_url VARCHAR(2000),
    source_type VARCHAR(50) NOT NULL,  -- pdf, wiki, html, json
    author VARCHAR(300),
    publication_year INTEGER,
    era historical_era,
    topics JSONB DEFAULT '[]',
    raw_content TEXT,
    status document_status DEFAULT 'pending',
    error_message TEXT,
    chunk_count INTEGER DEFAULT 0,
    trust_score FLOAT DEFAULT 0.5,  -- 0-1, nguồn uy tín cao hơn
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chunks
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    context_prefix TEXT,
    chunk_index INTEGER NOT NULL,
    section_title VARCHAR(500),
    page_ref VARCHAR(50),
    era historical_era,
    topics JSONB DEFAULT '[]',
    entities JSONB DEFAULT '[]',
    date_refs JSONB DEFAULT '[]',
    token_count INTEGER,
    qdrant_point_id VARCHAR(100),
    es_doc_id VARCHAR(100),
    trust_score FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sessions
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    role VARCHAR(20) NOT NULL,  -- user | assistant
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]',
    intent VARCHAR(50),
    tool_calls_count INTEGER DEFAULT 0,
    tokens_used INTEGER,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Feedback
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_era ON chunks(era);
CREATE INDEX idx_chunks_entities ON chunks USING GIN(entities);
CREATE INDEX idx_chunks_topics ON chunks USING GIN(topics);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_era ON documents(era);
```

---

## 12. Tech Stack Tổng Hợp

### Backend
| Component | Technology | Lý do chọn |
|-----------|-----------|-----------|
| Web framework | FastAPI | Async native, tự động docs, type safety |
| ORM | SQLAlchemy 2.0 async | Modern async, type-safe |
| Task queue | Celery + Redis | Mature, reliable, dễ monitor |
| Validation | Pydantic v2 | Fast, type-safe |
| Migration | Alembic | Standard cho SQLAlchemy |

### AI & ML
| Component | Technology | Lý do chọn | Alternatives |
|-----------|-----------|-----------|---------------|
| **LLM Primary** | Claude claude-sonnet-4-20250514 | Tốt nhất cho reasoning + tool use, context 200K | GPT-4o, Llama 3 70B (local) |
| **LLM Fast** | Claude haiku-4 | Rẻ ($0.025/M tok) cho simple tasks | GPT-4o-mini |
| **Embedding** | intfloat/multilingual-e5-large | SOTA multilingual, hỗ trợ tiếng Việt tốt | OpenAI text-embedding-3-large, BAAI/bge-m3 |
| **Embedding Fast** | intfloat/multilingual-e5-small | Nhanh hơn 4x, chất lượng OK cho MVP | paraphrase-multilingual-MiniLM-L12-v2 |
| **Reranker** | BAAI/bge-reranker-v2-m3 | SOTA reranking, 128 languages | BAAI/bge-reranker-base, Cohere rerank |
| **OCR** | PaddleOCR + Tesseract | Paddle cho printed VN text, Tesseract cho scanned docs | EasyOCR (simpler) |

### Embedding Model Comparison

| Model | Vietnamese Performance | Speed | Cost | Notes |
|--------|----------------------|-------|------|-------|
| multilingual-e5-large | ⭐⭐⭐⭐ | Slow | Medium | Recommended cho production |
| multilingual-e5-small | ⭐⭐⭐ | Fast | Low | Tốt cho MVP |
| bge-m3 | ⭐⭐⭐⭐ | Medium | Medium | Đa ngôn ngữ tốt |
| text-embedding-3-large | ⭐⭐⭐⭐ | Fast | High | OpenAI API required |

### LLM Comparison for Vietnamese

| Model | Vietnamese Quality | Tool Use | Context | Cost/1M tokens |
|--------|-------------------|---------|--------|----------------|
| Claude Sonnet 4 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 200K | $3.00 |
| Claude Haiku 4 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 200K | $0.025 |
| GPT-4o | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 128K | $5.00 |
| GPT-4o-mini | ⭐⭐⭐ | ⭐⭐⭐⭐ | 128K | $0.15 |

**Recommendation:** Claude Sonnet 4 cho synthesis + reasoning, Claude Haiku 4 cho classification + expansion.

### Storage & Retrieval
| Component | Technology | Lý do chọn |
|-----------|-----------|-----------|
| Vector store | Qdrant | Persistent, production-grade, filter support |
| Full-text search | Elasticsearch | Best-in-class BM25, Vietnamese analyzer |
| Relational DB | PostgreSQL 16 | JSONB, UUID, reliable |
| Cache | Redis | Session, rate limit, Celery broker |

### Frontend
| Component | Technology | Lý do chọn |
|-----------|-----------|-----------|
| Framework | React + Vite | Fast dev, ecosystem |
| State | Zustand | Simple, no boilerplate |
| Styling | Tailwind CSS | Utility-first, consistent |
| UI components | shadcn/ui | Accessible, customizable |
| Type safety | TypeScript strict | Catch errors early |

### Observability
| Component | Technology | Lý do chọn |
|-----------|-----------|-----------|
| LLM tracing | Langfuse | Best LLM observability tool |
| Metrics | Prometheus + Grafana | Standard stack |
| Task monitoring | Flower (Celery) | Built-in Celery UI |
| Error tracking | Sentry (optional) | Production error tracking |

### DevOps
| Component | Technology | Lý do chọn |
|-----------|-----------|-----------|
| Containerization | Docker + Compose | Reproducible environments |
| CI | GitHub Actions | Free, integrated |
| Eval | RAGAS | Standard RAG evaluation |

---

## 13. Timeline & Milestones

```
TUẦN 1:    [====] Phase 0: Cleanup, CI, env setup
TUẦN 2-4:  [============] Phase 1: Data ingestion pipeline  
TUẦN 3-6:  [================] Phase 2: Hybrid retrieval (overlap với P1)
TUẦN 7-9:  [============] Phase 3: Agent orchestration
TUẦN 10:   [====] Phase 4: API & Streaming
TUẦN 11-12:[========] Phase 5: Frontend
TUẦN 13-14:[========] Phase 6+7: Testing, eval, infrastructure
```

### Milestones

| Tuần | Milestone | Criteria |
|------|-----------|---------|
| 1 | Repo sạch | CI pass, 1 luồng chat duy nhất |
| 2 | v0.1 MVP | Docker compose up, 100 Wikipedia articles, 1 query → answer có citation | ⏳ |
| 4 | Retrieval working | BM25 + Dense hybrid, NDCG@5 > 0.5 (manual test) | ⏳ |
| 6 | Streaming UX | SSE streaming text, latency < 5s | ⏳ |
| 8 | v0.3 Basic agent | Intent routing, multi-step cho complex questions | ⏳ |
| 10 | Retrieval solid | NDCG@5 > 0.7, reranker integrated | ⏳ |
| 12 | v0.5 Alpha | Multi-step agent, citation panel, history | ⏳ |
| 14 | v1.0 Beta | RAGAS faithfulness > 0.75, docs complete | ⏳ |

---

## 14. Checklist "Xuất Sắc"

### Correctness
- [ ] Mọi claim có `[Nguồn: X, trang Y]` — không có câu trả lời "trần trụi"
- [ ] RAGAS faithfulness > 0.85 trên golden test set 200 câu
- [ ] Conflict detection: 2 nguồn mâu thuẫn → trình bày cả hai
- [ ] Không trả lời khi không có đủ context (thay vì hallucinate)
- [ ] Phân biệt fact vs inference trong câu trả lời

### Retrieval Quality  
- [ ] Hybrid BM25 (Elasticsearch) + Dense (Qdrant) — cả hai persistent
- [ ] HyDE cho query expansion (cải thiện 15-30% recall)
- [ ] Cross-encoder reranker (bge-reranker-v2-m3)
- [ ] Entity normalization: Lê Lợi = Lê Thái Tổ = Bình Định Vương
- [ ] Contextual chunk enrichment (context_prefix cho mỗi chunk)
- [ ] Metadata filtering: era, topic, trust_score
- [ ] Deduplication để tránh lặp chunks

### Agent Intelligence
- [ ] Intent classifier routing đúng workflow (5 intents)
- [ ] Multi-step planning cho câu hỏi phức tạp
- [ ] Parallel retrieval cho câu hỏi so sánh
- [ ] Tool use: ≤ 5 tool calls, graceful fallback
- [ ] Graceful: không có data → nói rõ, gợi ý nguồn tìm

### UX & Frontend
- [ ] Streaming với progress stages visual
- [ ] Inline citations clickable với popover preview
- [ ] Follow-up question suggestions
- [ ] Abort button để dừng streaming
- [ ] Error states handled gracefully
- [ ] Mobile responsive

### Engineering Excellence
- [ ] Test coverage > 70% backend
- [ ] RAGAS eval chạy tự động khi merge vào main
- [ ] Langfuse tracing cho mỗi query (intent, chunks, tokens, latency)
- [ ] Prometheus metrics + Grafana dashboard
- [ ] Rate limiting + authentication
- [ ] Docker compose one-command setup (`docker-compose up`)
- [ ] Alembic migrations (không schema manual)
- [ ] Comprehensive `.gitignore` (không commit build artifacts)

### Data Quality
- [ ] ≥ 1000 documents ingested (Wikipedia VI + SGK + Bách khoa toàn thư)
- [ ] Entity aliases cho 50+ nhân vật/địa danh quan trọng
- [ ] Trust scores phân biệt nguồn uy tín vs nguồn thấp
- [ ] Golden eval dataset 200 câu với ground truth

### Documentation
- [ ] README phản ánh đúng trạng thái thực tế (không hứa hẹn chưa làm)
- [ ] DEV_COMMANDS.md cập nhật đủ các lệnh
- [ ] API documentation (FastAPI auto-docs tại `/docs`)
- [ ] Architecture diagram trong README

---

> **Ghi chú cuối:** Plan này đủ để đưa project từ 6.5/10 lên 9+/10.  
> Thứ tự ưu tiên: Phase 0 → Phase 1 → Phase 2 → Phase 3.  
> Phase 4-7 có thể làm song song khi core AI/RAG đã chạy.  
> 
> Key insight: 80% chất lượng đến từ data quality + chunking + retrieval.  
> Agent orchestration quan trọng nhưng không bù được retrieval kém.  
> **Làm đúng retrieval trước. Agent sau.**