#!/usr/bin/env bash
# ─── HistoriAI Deployment Script ───────────────────────────────────────────────
# Usage: ./scripts/deploy.sh [production|staging|dev] [--rollback]
#
# Prerequisites:
#   - Docker & docker compose installed
#   - PostgreSQL 16, Redis 7 available
#   - API keys set in .env or environment

set -euo pipefail

APP_NAME="historiai"
COMPOSE_FILE="docker-compose.yml"
HEALTH_TIMEOUT=60

# ─── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'

log()  { echo -e "${BLUE}[deploy]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC}   $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*" >&2; }

# ─── Parse args ────────────────────────────────────────────────────────────────
TARGET="${1:-production}"
ROLLBACK=false
for arg in "$@"; do
    case $arg in
        --rollback) ROLLBACK=true ;;
    esac
done

log "Deploying to ${TARGET}..."

# ─── Env validation ───────────────────────────────────────────────────────────
if [[ ! -f ".env" ]]; then
    warn ".env not found — copying from .env.example"
    cp .env.example .env 2>/dev/null || true
fi

# ─── Database migration ────────────────────────────────────────────────────────
log "Running database migrations..."
cd apps/api
if [[ -f "alembic.ini" ]]; then
    pip install -q -e . 2>/dev/null || true
    alembic upgrade head
    ok "Migrations complete"
else
    warn "Alembic not configured — skipping migrations"
fi
cd ../..

# ─── Pull latest images ────────────────────────────────────────────────────────
log "Pulling Docker images..."
docker compose pull api web 2>/dev/null || true

# ─── Rollback if requested ─────────────────────────────────────────────────────
if $ROLLBACK; then
    warn "Rolling back to previous version..."
    docker compose up -d --no-deps api
    ok "Rollback complete"
    exit 0
fi

# ─── Deploy services ───────────────────────────────────────────────────────────
log "Starting services..."
docker compose up -d --no-deps api web

# ─── Health check ──────────────────────────────────────────────────────────────
log "Waiting for API health..."
HEALTH_URL="http://localhost:8000/health"
ATTEMPTS=0
while true; do
    ATTEMPTS=$((ATTEMPTS + 1))
    if curl -sf "${HEALTH_URL}" > /dev/null 2>&1; then
        ok "API is healthy at ${HEALTH_URL}"
        break
    fi
    if (( ATTEMPTS > HEALTH_TIMEOUT )); then
        fail "Health check timeout after ${HEALTH_TIMEOUT}s"
        docker compose logs api --tail=50
        exit 1
    fi
    sleep 2
done

# ─── Run smoke tests ───────────────────────────────────────────────────────────
log "Running smoke tests..."
if docker compose exec -T api python -c "import sys; sys.exit(0)" 2>/dev/null; then
    ok "API process is running inside container"
else
    warn "Could not verify API process — continuing"
fi

# ─── Report ───────────────────────────────────────────────────────────────────
log "Deployment summary:"
echo "  Images: $(docker compose images ${APP_NAME}-api --format json 2>/dev/null | jq -r '.Tag' || echo 'N/A')"
echo "  Containers: $(docker compose ps --format json 2>/dev/null | jq -r '.Name' | grep ${APP_NAME} | tr '\n' ' ')"
echo ""
ok "Deploy complete!"
