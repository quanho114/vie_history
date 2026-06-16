# HistoriAI — Developer Commands
# Run `make help` to see all available targets.

.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ─── Prerequisites ────────────────────────────────────────────────────────────

.PHONY: install
install: ## Install all dependencies (API + web)
	cd apps/api && pip install -e ".[dev]" && cd -
	cd apps/web && npm install && cd -

.PHONY: install-api
install-api: ## Install API dependencies
	cd apps/api && pip install -e ".[dev]"

.PHONY: install-web
install-web: ## Install web dependencies
	cd apps/web && npm install

# ─── Development ───────────────────────────────────────────────────────────────

.PHONY: dev
dev: dev-api dev-web ## Run both API and web dev servers

.PHONY: dev-api
dev-api: ## Run API dev server (port 8000)
	cd apps/api && uvicorn app.main:app --reload --port 8000 --host 0.0.0.0

.PHONY: dev-web
dev-web: ## Run web dev server (port 5173)
	cd apps/web && npm run dev

# ─── Docker ─────────────────────────────────────────────────────────────────

.PHONY: up
up: ## Start all Docker services
	docker-compose up -d

.PHONY: down
down: ## Stop all Docker services
	docker-compose down

.PHONY: logs
logs: ## Tail Docker logs (all services)
	docker-compose logs -f

.PHONY: logs-api
logs-api: ## Tail API logs
	docker-compose logs -f api

.PHONY: logs-redis
logs-redis: ## Tail Redis logs
	docker-compose logs -f redis

.PHONY: db-migrate
db-migrate: ## Run database migrations
	cd apps/api && alembic upgrade head

.PHONY: db-rollback
db-rollback: ## Rollback last migration
	cd apps/api && alembic downgrade -1

# ─── Testing ─────────────────────────────────────────────────────────────────

.PHONY: test
test: test-api test-web ## Run all tests

.PHONY: test-api
test-api: ## Run API tests
	cd apps/api && pytest tests/ -v

.PHONY: test-api-cov
test-api-cov: ## Run API tests with coverage
	cd apps/api && pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

.PHONY: test-web
test-web: ## Run web tests
	cd apps/web && npm run test -- --run

# ─── Linting & Formatting ───────────────────────────────────────────────────

.PHONY: lint
lint: lint-api lint-web ## Run all linters

.PHONY: lint-api
lint-api: ## Run ruff lint on API
	cd apps/api && ruff check app/

.PHONY: lint-api-fix
lint-api-fix: ## Fix ruff lint issues in API
	cd apps/api && ruff check app/ --fix

.PHONY: lint-web
lint-web: ## Run ESLint on web
	cd apps/web && npm run lint

.PHONY: fmt
fmt: fmt-api fmt-web ## Format all code

.PHONY: fmt-api
fmt-api: ## Format API code with ruff
	cd apps/api && ruff format app/

.PHONY: fmt-web
fmt-web: ## Format web code with prettier
	cd apps/web && npx prettier --write "src/**/*.tsx" "src/**/*.ts"

# ─── Type Checking ───────────────────────────────────────────────────────────

.PHONY: typecheck
typecheck: typecheck-api typecheck-web ## Run all type checkers

.PHONY: typecheck-api
typecheck-api: ## Run mypy on API
	cd apps/api && python -m mypy app/ --ignore-missing-imports

.PHONY: typecheck-web
typecheck-web: ## Run TypeScript type check on web
	cd apps/web && npm run type-check

# ─── Security ───────────────────────────────────────────────────────────────

.PHONY: security
security: ## Run security checks
	cd apps/api && bandit -r app/ -f txt

# ─── Build ─────────────────────────────────────────────────────────────────

.PHONY: build-web
build-web: ## Build web production bundle
	cd apps/web && npm run build

# ─── Cleanup ────────────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove generated files and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	cd apps/web && npm run clean 2>/dev/null || true
