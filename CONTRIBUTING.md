# Contributing to HistoriAI

## Project Overview

HistoriAI is a multi-agent RAG system for Vietnamese historical research (1945-1975), built with FastAPI, LangGraph, hybrid retrieval (Qdrant + Elasticsearch BM25), and a React frontend.

## Quick Start

```bash
# 1. Clone and install
make install

# 2. Start services
docker compose up -d

# 3. Run API
make dev-api

# 4. Run frontend (separate terminal)
make dev-web
```

## Development Workflow

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Redis, PostgreSQL, Qdrant, Elasticsearch (via Docker)

### Required Environment Variables

Copy `.env.example` to `.env` in `apps/api/` and fill in:

- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_PASSWORD` — Redis authentication
- `HISTORIAI_API_TOKEN` — API authentication token
- LLM API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.)

### Branch Strategy

```
main          — stable, production-ready
dev           — integration branch
feat/*        — feature branches
fix/*         — bug fix branches
improvement/* — refactoring and improvements
```

### Commit Format

```
<type>(<scope>): <description>

Types: feat | fix | docs | style | refactor | test | chore
Scope: api | web | infra | ai | docs
```

Examples:
- `fix(api): remove hardcoded fallback token in MCP server`
- `feat(ai): add Vietnamese embedding model`
- `docs(web): add Storybook stories for ChatBubble`

## Code Standards

### Python (API)

```bash
make lint-api        # Check linting
make fmt-api         # Format code
make typecheck-api   # Type checking
make test-api        # Run tests
```

- Follow PEP 8 with line length 100
- Use `ruff` for linting and formatting
- All new code must pass `ruff check` with no errors
- Add type hints to public methods
- Use async/await for all I/O operations
- Import order: stdlib → third-party → local

### TypeScript (Web)

```bash
make lint-web        # ESLint + Prettier
make typecheck-web   # TypeScript checking
```

- Use TypeScript strictly — no `any` types
- Prefer `interface` over `type` for object shapes
- Components must be functional with hooks
- Use `React.memo` for frequently re-rendered components
- Add ARIA labels to all interactive elements

## Testing Requirements

### Coverage Targets

| Area | Target |
|------|--------|
| Backend services | >80% |
| AI pipeline | >70% |
| Frontend components | >60% |
| Critical paths | 100% |

### Writing Tests

```bash
# Backend
cd apps/api
pytest tests/unit/test_retrieval.py -v
pytest tests/integration/ -v

# Frontend
cd apps/web
npm run test
```

- Test file naming: `test_<module>.py` or `<module>_test.py`
- Use `pytest-asyncio` for async tests
- Mock external services (LLM, Qdrant, Elasticsearch)
- Test error paths, not just happy paths
- Do not commit tests that access real external services

## Pull Request Process

1. **Create branch** from `dev`: `git checkout -b feat/vietnamese-reranker`
2. **Make changes** with passing tests and lint
3. **Write PR description** with:
   - Summary of what changed and why
   - Test plan (how to verify)
   - Screenshots for UI changes
4. **Pass CI** — all checks must green before merge
5. **Request review** — minimum 1 approval required
6. **Squash and merge** to `dev`

## Architecture Guidelines

### API Layer

```
routes/ → agents/ → services/ → retrieval/
                         → llm/
                         → graph/
                         → brain/
```

- Routes handle HTTP only
- Agents orchestrate business logic
- Services contain pure business logic
- Never call `print()` — use structured logging

### Frontend Layer

```
pages/     → route-level components
components/ → reusable UI components
hooks/     → data fetching and state
stores/    → Zustand global state
```

- Pages are dumb — they orchestrate components
- Components are reusable and stateless when possible
- State belongs in Zustand stores or React Query
- Never access localStorage directly — use the storage module

## Security Guidelines

- Never commit secrets, API keys, or tokens
- Use environment variables for all credentials
- Sanitize all user input before database queries
- Validate file paths before disk operations
- Never expose internal error messages to clients
- Auth bypass flags require `APP_ENV=development` AND explicit enable flag

## Getting Help

- Check existing issues before opening new ones
- For questions: open a GitHub Discussion
- For bugs: include reproduction steps and environment details

## License

By contributing, you agree that your contributions will be licensed under the project's license.
