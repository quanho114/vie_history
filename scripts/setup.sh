#!/bin/bash
# ───────────────────────────────────────────────────────────────
# HistoriAI Full Setup Script
# Usage: ./scripts/setup.sh
# ───────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "==> HistoriAI Setup"
echo ""

# ── 1. Docker Network ────────────────────────────────────────────
echo "[1/5] Creating Docker network..."
if ! docker network inspect historiai-network >/dev/null 2>&1; then
    docker network create historiai-network
    echo "      Network 'historiai-network' created."
else
    echo "      Network 'historiai-network' already exists."
fi

# ── 2. Backend setup ──────────────────────────────────────────────
echo "[2/5] Setting up backend..."
cd "$PROJECT_ROOT/apps/api"

if [ ! -d "venv" ]; then
    python -m venv venv
fi
source venv/bin/activate
pip install -q -e ".[dev]" 2>/dev/null || pip install -q -e .

# ── 3. Frontend setup ─────────────────────────────────────────────
echo "[3/5] Setting up frontend..."
cd "$PROJECT_ROOT/apps/web"
if [ ! -d "node_modules" ]; then
    npm install --silent
fi

# ── 4. Docker services ────────────────────────────────────────────
echo "[4/5] Starting Docker services (Postgres, Redis, Qdrant, Meili)..."
cd "$PROJECT_ROOT"
docker-compose up -d postgres redis qdrant meilisearch

# Wait for postgres
echo "      Waiting for Postgres..."
until docker exec vie_history_postgres pg_isready -U vie_history >/dev/null 2>&1; do
    sleep 2
done
echo "      Postgres ready."

# ── 5. Run migrations ─────────────────────────────────────────────
echo "[5/5] Running database migrations..."
cd "$PROJECT_ROOT/apps/api"
source venv/bin/activate
alembic upgrade head >/dev/null 2>&1 && echo "      Migrations applied." || echo "      Migrations skipped (or already applied)."

echo ""
echo "==> Setup complete!"
echo ""
echo "To start services:"
echo "  Core services only:     docker compose up -d"
echo "  Full stack:             docker compose -f docker-compose.yml -f docker-compose.full.yml up -d"
echo "  Backend dev (manual):    cd apps/api && source venv/bin/activate && uvicorn app.main:app --port 12701 --reload"
echo "  Frontend dev (manual):  cd apps/web && npm run dev"
echo ""
echo "Access:"
echo "  Frontend:   http://localhost:12702"
echo "  API Docs:   http://localhost:12701/docs"
echo "  Qdrant:     http://localhost:12705/dashboard"
echo "  Meilisearch: http://localhost:12707"
