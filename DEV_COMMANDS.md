# Dev Commands

## Quick Start

### First-time setup

```bash
# Chạy script setup (tạo network, cài dependencies, chạy migrations)
./scripts/setup.sh

# Hoặc thủ công:
docker network create historiai-network  # Tạo Docker network (chỉ 1 lần)
```

### 1. Chạy database services (Docker)

```bash
docker-compose up -d
```

### 2. Backend (terminal riêng)

```bash
cd apps/api

# Tạo virtual environment (chỉ lần đầu)
python -m venv venv
source venv/bin/activate    # Linux/macOS
# venv\Scripts\activate     # Windows

# Cài đặt dependencies (chỉ lần đầu)
pip install -e .

# Chạy migrations (chỉ lần đầu)
alembic upgrade head

# Start dev server
uvicorn app.main:app --host 0.0.0.0 --port 12701 --reload
```

### 3. Frontend (terminal riêng)

```bash
cd apps/web

# Cài đặt dependencies (chỉ lần đầu)
npm install

# Start dev server
npm run dev
```

## Access URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:12702 |
| API Docs | http://localhost:12701/docs |
| Qdrant Dashboard | http://localhost:12705/dashboard |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:13000 (admin / historiai) |

## Stop Services

```bash
# Stop Docker
docker-compose down

# Stop backend: Ctrl+C trong terminal
# Stop frontend: Ctrl+C trong terminal
```

## Database Migrations

```bash
cd apps/api
source venv/bin/activate

# Tạo migration mới sau khi sửa model
alembic revision --autogenerate -m "migration message"

# Chạy tất cả migrations
alembic upgrade head

# Rollback 1 migration
alembic downgrade -1

# Rollback to đầu
alembic downgrade base
```

## Linting & Formatting

```bash
cd apps/api
source venv/bin/activate
ruff check .          # check linting
ruff format .         # format code

cd ../web
npx eslint src/      # check linting
npx prettier --write src/   # format code
```

## Rebuild Docker (nếu cần)

```bash
# Rebuild và restart Docker services
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Reset Database

```bash
docker-compose down -v   # xóa data volumes
docker-compose up -d     # restart
cd apps/api
alembic upgrade head
```

## Full-Stack Docker (API + Frontend + Worker + Observability)

```bash
# Tạo network trước (chỉ 1 lần)
docker network create historiai-network 2>/dev/null || true

# Build và chạy tất cả services
docker compose -f docker-compose.yml -f docker-compose.full.yml up -d

# Xem logs
docker compose -f docker-compose.yml -f docker-compose.full.yml logs -f

# Rebuild sau khi sửa code
docker compose -f docker-compose.yml -f docker-compose.full.yml up -d --build
```

## Observability Stack

```bash
# Start Prometheus + Grafana
docker network create historiai-network 2>/dev/null || true
docker-compose -f docker-compose.yml -f infrastructure/docker-compose.observability.yml up -d

# Prometheus UI:   http://localhost:9090
# Grafana:        http://localhost:13000 (admin / historiai)
# Metrics export:  http://localhost:12701/metrics
```

## Testing

```bash
cd apps/api
source venv/bin/activate

# Chạy tất cả unit tests
pytest tests/ -v

# Chạy với coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Chạy một file test cụ thể
pytest tests/unit/test_fusion.py -v

# Chạy integration tests (cần services chạy)
pytest tests/integration/ -v
```
