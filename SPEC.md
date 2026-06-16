# Spec: HistoriAI — Agentic AI Vietnamese History Research System

## Objective
HistoriAI is an academic research project and evaluation system studying Agentic RAG for Vietnamese historical question answering. The project aims to evaluate whether a metadata-aware hybrid retrieval framework combined with a post-generation citation verification pipeline can mathematically improve the accuracy, groundedness, and citation reliability of Vietnamese historical answers.

### Research Contributions
1. **Primary Contribution**: A Metadata-aware Historical Retrieval framework (era, dynasty, region, and primary year alignment) for Vietnamese history.
2. **Secondary Contribution**: A hybrid Citation Verification pipeline combining LLM claim decomposition and embedding semantic similarity validation.
3. **Benchmark Dataset**: HistoriEval-VN, a balanced benchmark dataset of 500-700 Vietnamese historical questions with ground truth answers, supporting sources, and inter-annotator Cohen's Kappa consensus.
4. **Ablation & Statistical Validation**: Empirical ablation study comparing 6 system configurations (Baselines A to F) using RAGAS and retrieval metrics validated by Wilcoxon signed-rank significance testing.

### Key Metrics & Goals
1. **Faithfulness**: RAGAS Faithfulness score > 0.85 on the HistoriEval-VN benchmark.
2. **Citation Quality**: Citation Precision and Citation Recall > 0.80 on the benchmark.
3. **Statistical Significance**: Validated improvements with Wilcoxon signed-rank test p-values < 0.05.

---

## Tech Stack
### Backend (apps/api)
* **Core**: Python 3.11+, FastAPI, Uvicorn
* **Database & Persistence**: PostgreSQL (via `asyncpg` and `SQLAlchemy` asyncio), Alembic for schema migrations
* **Vector Store**: Qdrant (dense search on port 12705/12706)
* **Lexical Search**: Meilisearch (sparse/BM25 search on port 12707)
* **Caching & Queue**: Redis (via `redis-py`), RQ (Redis Queue) for background tasks (port 12704)
* **NLP & Embeddings**: SentenceTransformers (`paraphrase-multilingual-MiniLM-L12-v2`), PyVi (Vietnamese word segmentation)
* **Orchestration & LLMs**: Anthropic Claude API (Sonnet 3.5 & Haiku) / OpenAI API / Ollama (local Llama 3)
* **Observability**: Langfuse (LLM tracing), Prometheus, Grafana

### Frontend (apps/web)
* **Core**: React 18.3+, Vite, TypeScript
* **State Management**: Zustand
* **Styling**: Tailwind CSS, Vanilla CSS
* **Components & Animation**: Framer Motion, Lucide icons, Three.js / React Three Fiber (for 3D historical assets)

---

## Commands

### Environment Setup & Infra
```bash
# Start Docker services (PostgreSQL, Redis, Qdrant, Meilisearch)
docker-compose up -d

# Stop Docker services
docker-compose down

# Check running containers
docker ps
```

### Database Migrations
```bash
# Activate virtual environment
cd apps/api
source venv/bin/activate

# Apply migrations to head (using autocommit for index creation)
ALEMBIC_AUTOCOMMIT=true alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

### Application Development Runs
```bash
# Start backend API (Port 12701)
cd apps/api
venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 12701 --reload

# Start background RQ Worker
cd apps/api
venv/bin/rq worker ingest-queue --url redis://localhost:12704/0

# Start frontend development server (Port 12702)
cd apps/web
npm run dev
```

### Code Formatting & Linting
```bash
# Format and lint Python backend
cd apps/api
venv/bin/ruff check app/ --fix
venv/bin/ruff format app/

# Format and lint React frontend
cd apps/web
npm run lint
npx prettier --write "src/**/*.tsx" "src/**/*.ts"
```

---

## Project Structure
```
Vie_history/
├── apps/
│   ├── api/                          # FastAPI backend
│   │   ├── alembic/                  # Database schema migrations
│   │   ├── app/
│   │   │   ├── main.py               # API entry point & thin factory wrapper
│   │   │   ├── factory.py            # FastAPI application factory setup
│   │   │   ├── core/                 # Configs, DB sessions, security, rate limiters
│   │   │   ├── models/               # SQLAlchemy models (User, Document, Message, AuditLog)
│   │   │   ├── schemas/              # Pydantic validation schemas
│   │   │   ├── api/                  # API routing endpoints (auth, query, ingest, safety)
│   │   │   ├── agents/               # AI Agent routers, planners, & complexity classifier
│   │   │   ├── retrieval/            # Hybrid search retrieval & citation builders
│   │   │   ├── services/             # Business & Query processing logic
│   │   │   ├── worker/               # Arq background worker configurations
│   │   │   └── workers/              # Celery/Arq background task definitions
│   │   └── tests/                    # Backend unit/integration tests
│   └── web/                          # Vite React frontend
│       ├── src/
│       │   ├── components/           # Reusable UI widgets & chat components
│       │   ├── pages/                # Views (ChatPage.tsx, AdminPage.tsx, SearchPage.tsx)
│       │   ├── stores/               # Zustand state modules (chatStore.ts, authStore.ts)
│       │   ├── hooks/                # Custom React hooks (SSE stream hook)
│       │   └── lib/                  # Fetch client wrapper
├── data/                             # Entity catalogs, era rules & seed files
├── docs/                             # Documentation and plans
├── evals/                            # Golden dataset & RAGAS evaluation harness
└── scripts/                          # DB seed & batch ingestion utility scripts
```

---

## Code Style

### Backend Python Guidelines
* **Type Hints**: All functions must have complete type signatures.
* **Asynchronous Execution**: Prefer async/await for database queries (SQLAlchemy), HTTP calls (HTTPX), and database interactions.
* **Logging**: Structured logs with `structlog`. Use descriptive key-value logging rather than string-interpolated logs.

*Example Python Code Style (from Complexity Classifier):*
```python
from __future__ import annotations
from dataclasses import dataclass
from app.core.logging import get_logger

logger = get_logger("complexity_classifier")

@dataclass
class ComplexityResult:
    mode: str           # "fast" | "graph" | "agentic"
    intent: str         # original intent label
    confidence: float   # 0.0–1.0

class ComplexityClassifier:
    """Classifies queries into different execution speeds without calling an LLM."""
    
    def classify(self, query: str) -> ComplexityResult:
        q = query.lower().strip()
        if any(greet in q for greet in ["chào", "hello"]):
            logger.info("complexity_classified", mode="fast", intent="greeting")
            return ComplexityResult(mode="fast", intent="greeting", confidence=0.98)
        
        # Default route
        return ComplexityResult(mode="fast", intent="factual", confidence=0.60)
```

### Frontend React/TypeScript Guidelines
* **State Management**: Use Zustand stores (`chatStore.ts`) instead of drilling props or relying heavily on local storage for global states.
* **TypeScript**: Enforce strict type checking; avoid using `any`.
* **Vanilla CSS / Tailwind**: Ensure responsiveness, clean grid alignments, and custom animations.

---

## Testing Strategy
* **Unit & Integration Testing**: Powered by `pytest` and `pytest-asyncio` inside `apps/api/tests/`.
* **Inter-Annotator Agreement**: Computed using `evals/calculate_agreement.py` for Cohen's Kappa.
* **Ablation Evaluation**: Driven by `evals/run_ablation_study.py` measuring:
  - **Retrieval Metrics**: Hit@k, MRR, Recall@k, nDCG
  - **Generation Metrics**: RAGAS Faithfulness, Answer Relevancy, Context Precision, Context Recall
  - **Citation Metrics**: Citation Precision, Citation Recall, Citation Coverage
  - **Significance Testing**: Wilcoxon signed-rank test with p-value calculations.

---

## Boundaries

### Always Do:
* Perform lint checks (`ruff`) and test runs before pushing to master.
* Write migrations for any SQLAlchemy database model updates.
* Run PostgreSQL operations utilizing connection pooling.
* Include detailed inline citations for any factual claims produced by the retrieval agents.

### Ask First:
* Introducing new external Python/Node packages or modifying dependencies.
* Modifying Postgres database schemas.
* Tweaking the CI/CD pipeline configurations in `.github/workflows/`.
* Modifying the core LLM prompt definitions.

### Never Do:
* Commit sensitive API keys (e.g. `ANTHROPIC_API_KEY`, `POSTGRES_PASSWORD`) to git. Always use `.env` files.
* Remove or mute failing unit tests without human approval.
* Directly invoke LLMs or search APIs from the React frontend. All requests must go through the FastAPI gateway.
* Add out-of-scope features (e.g., Neo4j/Knowledge Graph, fine-tuning embedding models, local LLM fallbacks, or 3D visualizations).

---

## Success Criteria
- [ ] Ingesting historical articles parses era, dynasty, and region using rule-based extraction and indexes them to Meilisearch and Qdrant.
- [ ] Hybrid search utilizes query metadata extraction to boost relevance matching.
- [ ] Citation verification executes LLM claim extraction, semantic similarity validation, and returns verified responses with inline citations.
- [ ] The ablation study runner executes configurations A-F successfully and outputs report json.
- [ ] Statistical significance testing runs Wilcoxon test on configurations C and F, producing p-value scores.

---

## Open Questions
1. **Optimal Citation Verification Threshold**: What is the mathematically proven embedding similarity threshold tuned via grid search to balance Citation Precision and Citation Recall?
2. **Annotator Disagreement Resolution**: If the Cohen's Kappa score falls below 0.8, what consensus resolution rules should be followed by the annotators to re-label disputed benchmark items?
