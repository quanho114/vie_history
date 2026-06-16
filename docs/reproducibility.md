# Reproducibility Guide

## Environment Setup

```bash
# Clone the repository
git clone https://github.com/your-org/historiai.git
cd historiai

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment file
cp .env.example .env
# Edit .env with your API keys
```

## Docker Setup

```bash
# Start all services
docker compose up -d

# Verify services
curl http://localhost:8000/health
```

## Evaluation

```bash
# Run benchmark evaluation
cd apps/api
pytest tests/evaluation/ -v

# Run with coverage
pytest --cov=app --cov-report=html tests/
```

## MLflow Experiment Tracking

```bash
# Start MLflow server
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlflow_artifacts

# View experiments
open http://localhost:5000
```

## Benchmark Dataset

The VH-RAG benchmark is available in `app/services/evaluation/benchmark_dataset.py`.
To generate the full dataset:

```python
from app.services.evaluation.benchmark_dataset import VHRAGBenchmark

benchmark = VHRAGBenchmark()
# Add queries from domain experts
benchmark.save("vh_rag_benchmark.json")
```
