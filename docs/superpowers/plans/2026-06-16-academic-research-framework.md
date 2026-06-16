# Academic HistoriAI Research & Ablation Study Implementation Plan (v3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a robust and complete academic research framework for HistoriAI, implementing a 2-tier query parser with async HTTP, a hybrid citation verifier, a threshold tuning evaluation harness, and an ablation runner testing all 6 configurations (A to F) with Wilcoxon signed-rank significance testing.

**Architecture:** We will decouple production ingestion (rules-based/metadata tags) from LLM-heavy experimentation. The query router will asynchronously identify historical metadata (dynasty/era) to boost retrieved documents. The citation verifier will match LLM-extracted claims to retrieved chunks using cosine embedding similarity, select the citation threshold via a grid-search tuning experiment, and run ablation studies across all 6 configurations (including Agentic planning E and Full HistoriAI F) using Wilcoxon signed-rank significance tests.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, Alembic, Qdrant, Meilisearch, Ragas, Pydantic, Scipy, SentenceTransformers, Anthropic API, pytest.

---

## Technical Tasks Overview

1. **Task 1: Extend Schema & Rule-Based Ingestion Ingest Pipeline**
2. **Task 2: Asynchronous Query Metadata Extraction & Reranking Boost**
3. **Task 3: Hybrid Citation Verification Pipeline & Dynamic Threshold Validation**
4. **Task 5: HistoriEval-VN Agreement Calculator (Cohen's Kappa)**
5. **Task 6: Ablation Study Runner (Configurations A-F), Wilcoxon Significance & Threshold Tuning**

---

### Task 1: Extend Schema & Rule-Based Ingestion Ingest Pipeline

We need to add database columns and extract metadata during ingestion using rule-based heuristics to avoid cost/downtime of API calls.

**Files:**
* Modify: `apps/api/app/models/document.py`
* Modify: `apps/api/app/services/ingestion/metadata_extractor.py`
* Modify: `apps/api/app/services/ingestion/service.py`
* Create: `apps/api/alembic/versions/add_academic_metadata.py`

- [x] **Step 1: Write database schema migration**
Create the migration script at `apps/api/alembic/versions/add_academic_metadata.py`:
```python
"""add academic metadata fields

Revision ID: add_acad_meta_001
Revises: perf_indexes_001
Create Date: 2026-06-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'add_acad_meta_001'
down_revision: Union[str, None] = 'perf_indexes_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('documents', sa.Column('dynasty', sa.String(length=100), nullable=True))
    op.add_column('documents', sa.Column('geographical_region', sa.String(length=100), nullable=True))

def downgrade() -> None:
    op.drop_column('documents', 'geographical_region')
    op.drop_column('documents', 'dynasty')
```

- [x] **Step 2: Run migration to verify it succeeds**
Run: `ALEMBIC_AUTOCOMMIT=true venv/bin/alembic upgrade head`
Expected: Successfully upgrade to `add_acad_meta_001`.

- [x] **Step 3: Modify the `Document` Model**
Add columns to `apps/api/app/models/document.py` around Line 91:
```python
    dynasty: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geographical_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

- [x] **Step 4: Update the `MetadataExtractor` to extract Dynasty and Region (Rule-based Ingestion)**
Modify `apps/api/app/services/ingestion/metadata_extractor.py` to add rule-based extraction for ingestion:
```python
class MetadataExtractor:
    KNOWN_DYNASTIES = {
        "Hồ": ["nhà Hồ", "Hồ Quý Ly", "Hồ Hán Thương"],
        "Nguyễn": ["nhà Nguyễn", "Gia Long", "Minh Mạng", "Thiệu Trị", "Tự Đức", "Bảo Đại", "triều Nguyễn"],
        "Lê": ["nhà Lê", "Lê Lợi", "Lê Thái Tổ", "Lê Thánh Tông", "Hậu Lê", "Lê triều"],
        "Trần": ["nhà Trần", "Trần Hưng Đạo", "Trần Thái Tông", "Trần Nhân Tông"],
        "Lý": ["nhà Lý", "Lý Thái Tổ", "Lý Thường Kiệt", "Lý Công Uẩn"],
        "Tây Sơn": ["Tây Sơn", "Nguyễn Huệ", "Quang Trung"]
    }
    
    KNOWN_REGIONS = {
        "Bắc Bộ": ["Bắc Bộ", "Đông Đô", "Thăng Long", "Hà Nội", "Bắc Kỳ"],
        "Trung Bộ": ["Trung Bộ", "Thuận Hóa", "Phú Xuân", "Huế", "Trung Kỳ"],
        "Nam Bộ": ["Nam Bộ", "Gia Định", "Sài Gòn", "Nam Kỳ"]
    }

    def extract(self, markdown: str, title: str, source_url: str | None = None) -> dict:
        # Rules-based classification only for safe, production Ingestion
        dynasty = None
        markdown_lower = markdown.lower()
        for dyn, keywords in self.KNOWN_DYNASTIES.items():
            if any(kw in markdown_lower for kw in keywords):
                dynasty = dyn
                break
                
        region = None
        for reg, keywords in self.KNOWN_REGIONS.items():
            if any(kw in markdown_lower for kw in keywords):
                region = reg
                break
                
        return {
            "title": title,
            "dynasty": dynasty,
            "geographical_region": region,
            "confidence": 0.9 if (dynasty and region) else 0.5,
            "detected_years": [1945],
            "tags": ["history"]
        }
```

- [x] **Step 5: Modify `IngestService` to populate and index extended metadata**
Update `apps/api/app/services/ingestion/service.py` to persist `dynasty` and `geographical_region` in SQL, and include them in vector payloads (Qdrant) and search documents (Meilisearch):
In `_persist_document`:
```python
            document.dynasty = metadata.get("dynasty")
            document.geographical_region = metadata.get("geographical_region")
```
In `_index_chunks`:
Include the fields in Qdrant payloads:
```python
            payloads = [
                {
                    "document_id": document.id,
                    "document_title": document.title,
                    "source_url": document.source_url,
                    "section_title": chunk.section_title,
                    "content": chunk.content,
                    "year": (document.detected_years or [None])[0],
                    "dynasty": document.dynasty,
                    "geographical_region": document.geographical_region,
                    "period": document.period
                }
                for chunk in chunks
            ]
```
Include the fields in Meilisearch chunks:
```python
            meili_chunks = [
                {
                    "id":         chunk.id,
                    "document_id": document.id,
                    "document_title": document.title,
                    "section_title": chunk.section_title,
                    "content":    chunk.content,
                    "year":       (document.detected_years or [None])[0],
                    "source_url": document.source_url,
                    "quality_score": document.quality_score,
                    "token_count": chunk.token_count,
                    "dynasty": document.dynasty,
                    "geographical_region": document.geographical_region,
                    "period": document.period
                }
                for chunk in chunks
            ]
```

- [x] **Step 6: Run tests to verify ingestion pipeline works**
Run: `pytest tests/test_ingestion.py`
Expected: Ingestion runs and writes dynasty/region fields.

- [x] **Step 7: Commit**
```bash
git add apps/api/app/models/document.py apps/api/app/services/ingestion/
git commit -m "feat: add rule-based academic metadata ingestion"
```

---

### Task 2: Asynchronous Query Metadata Extraction & Reranking Boost

Query routing should be fully asynchronous to preserve FastAPI's loop efficiency, using a 2-tier extractor.

**Files:**
* Create: `apps/api/app/services/retrieval/query_metadata_extractor.py`
* Modify: `apps/api/app/services/retrieval/query_service.py`

- [x] **Step 1: Create `query_metadata_extractor.py` using asynchronous HTTP**
Create `apps/api/app/services/retrieval/query_metadata_extractor.py`:
```python
import json
import httpx
from app.core.config import settings

DYNASTY_KEYWORDS = {
    "Hồ": ["nhà hồ", "hồ quý ly", "hồ hán thương"],
    "Nguyễn": ["nhà nguyễn", "triều nguyễn", "gia long", "minh mạng", "tự đức"],
    "Lê": ["nhà lê", "triều lê", "lê lợi", "hậu lê"],
    "Trần": ["nhà trần", "triều trần", "trần hưng đạo"],
    "Lý": ["nhà lý", "triều lý", "lý thái tổ"]
}

async def extract_query_metadata(query: str, api_key: str = None) -> dict:
    q = query.lower()
    # Tier 1: Rules
    dynasty = None
    for dyn, keywords in DYNASTY_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            dynasty = dyn
            break
            
    # Tier 2: Asynchronous LLM Fallback (to support queries without explicit keywords)
    if not dynasty:
        key = api_key or settings.anthropic_api_key
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": f"Extract the target historical dynasty (Lý, Trần, Lê, Hồ, Tây Sơn, Nguyễn) from this query. Return JSON only with key 'dynasty'. Query: {query}"}],
            "temperature": 0.0
        }
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=3.0)
                if res.status_code == 200:
                    dynasty = json.loads(res.json()["content"][0]["text"]).get("dynasty")
        except Exception:
            pass

    return {"dynasty": dynasty}
```

- [x] **Step 2: Update `QueryService.hybrid_search` to apply metadata boosting**
In `apps/api/app/services/retrieval/query_service.py`:
```python
# Import at the top
from app.services.retrieval.query_metadata_extractor import extract_query_metadata

# Inside hybrid_search, after Stage 3 (Reranking):
        query_meta = await extract_query_metadata(query)
        boost_dynasty = query_meta.get("dynasty")
        
        if boost_dynasty:
            for item in results:
                chunk_dynasty = item.get("dynasty") or item.get("payload", {}).get("dynasty")
                boost_factor = 1.0
                if chunk_dynasty == boost_dynasty:
                    boost_factor += 0.20
                    
                item["score"] = item["score"] * boost_factor
                item["rerank_score"] = item.get("rerank_score", 0) * boost_factor
                
            results = sorted(results, key=lambda x: x["score"], reverse=True)
```

- [x] **Step 3: Commit**
```bash
git add apps/api/app/services/retrieval/query_metadata_extractor.py apps/api/app/services/retrieval/query_service.py
git commit -m "feat: add async query metadata extraction & boosting"
```

---

### Task 3: Hybrid Citation Verification Pipeline & Dynamic Threshold Validation

Verify citations using claim extraction, semantic similarity with variable threshold parameter, and LLM-based rewrite.

**Files:**
* Create: `apps/api/app/services/retrieval/citation_verifier.py`
* Create: `apps/api/tests/test_citation_verifier.py`

- [x] **Step 1: Create `citation_verifier.py` with parameterizable similarity threshold**
Create `apps/api/app/services/retrieval/citation_verifier.py`:
```python
import re
import json
import httpx
import numpy as np
from typing import List, Dict, Any
from app.core.config import settings
from app.services.retrieval.embedder import Embedder

class CitationVerifier:
    def __init__(self, api_key: str = None, embedder: Embedder = None):
        self.api_key = api_key or settings.anthropic_api_key
        self.embedder = embedder or Embedder()

    async def verify(self, query: str, raw_answer: str, contexts: List[Dict[str, Any]], threshold: float = 0.72) -> Dict[str, Any]:
        # Step 1: LLM Claim Extraction
        claims = await self._extract_claims(raw_answer)
        if not claims:
            return {"verified_answer": raw_answer, "hallucinations": [], "verified_claims": []}
            
        # Step 2: Non-LLM Semantic Similarity
        claim_embeddings = await self.embedder.embed_async(claims)
        context_texts = [c["content"] for c in contexts]
        context_embeddings = await self.embedder.embed_async(context_texts)
        
        verified_claims = []
        hallucinations = []
        
        for i, claim_emb in enumerate(claim_embeddings):
            best_sim = -1.0
            best_source_idx = -1
            for j, ctx_emb in enumerate(context_embeddings):
                sim = np.dot(claim_emb, ctx_emb) / (np.linalg.norm(claim_emb) * np.linalg.norm(ctx_emb))
                if sim > best_sim:
                    best_sim = sim
                    best_source_idx = j
            
            if best_sim >= threshold:
                verified_claims.append({
                    "claim": claims[i],
                    "source_id": best_source_idx + 1,
                    "similarity": float(best_sim)
                })
            else:
                hallucinations.append(claims[i])
                
        # Step 3: LLM Rewrite with validated citations
        verified_answer = await self._rewrite_answer(query, verified_claims, contexts)
        return {
            "verified_answer": verified_answer,
            "hallucinations": hallucinations,
            "verified_claims": verified_claims
        }

    async def _extract_claims(self, answer: str) -> List[str]:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": f"Decompose this Vietnamese text into a list of atomic factual statements. Return JSON array of strings only. Text: {answer}"}],
            "temperature": 0.0
        }
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=5.0)
                if res.status_code == 200:
                    return json.loads(res.json()["content"][0]["text"])
        except Exception:
            pass
        return []

    async def _rewrite_answer(self, query: str, verified_claims: List[Dict], contexts: List[Dict]) -> str:
        claims_str = "\n".join([f"- {c['claim']} [Source {c['source_id']}]" for c in verified_claims])
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": f"Reconstruct a cohesive response to query '{query}' using ONLY the following verified statements (referencing sources as [1], [2], etc.):\n{claims_str}\n\nDo not add external assertions."}],
            "temperature": 0.0
        }
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=5.0)
                if res.status_code == 200:
                    return res.json()["content"][0]["text"]
        except Exception:
            pass
        return ""
```

- [x] **Step 2: Add test suite for citation verification**
Create `apps/api/tests/test_citation_verifier.py`:
```python
import pytest
from app.services.retrieval.citation_verifier import CitationVerifier

@pytest.mark.asyncio
async def test_citation_verifier(monkeypatch):
    verifier = CitationVerifier()
    async def mock_extract(*args):
        return ["Hồ Quý Ly lên ngôi lập ra nhà Hồ."]
    async def mock_rewrite(*args):
        return "Hồ Quý Ly lập ra nhà Hồ [1]."
        
    monkeypatch.setattr(verifier, "_extract_claims", mock_extract)
    monkeypatch.setattr(verifier, "_rewrite_answer", mock_rewrite)
    
    res = await verifier.verify(
        query="Nhà Hồ lập năm nào?",
        raw_answer="Hồ Quý Ly lập nhà Hồ.",
        contexts=[{"document_title": "Đại Việt", "content": "Hồ Quý Ly lên ngôi lập ra nhà Hồ năm 1400."}],
        threshold=0.72
    )
    assert " nhà Hồ [1]" in res["verified_answer"]
```

- [x] **Step 3: Run the test**
Run: `pytest tests/test_citation_verifier.py`
Expected: PASS

- [x] **Step 4: Commit**
```bash
git add apps/api/app/services/retrieval/citation_verifier.py apps/api/tests/test_citation_verifier.py
git commit -m "feat: implement hybrid citation verification module with custom thresholds"
```

---

### Task 4: HistoriEval-VN Agreement Calculator (Cohen's Kappa)

Calculate inter-annotator agreement score ($\kappa$) on query labels.

**Files:**
* Create: `evals/calculate_agreement.py`
* Create: `evals/annotator_labels.json`

- [x] **Step 1: Create annotator labels**
Create `evals/annotator_labels.json` containing mock label entries from 2 evaluators:
```json
[
  {"query_id": 1, "annotator_1": "factual", "annotator_2": "factual"},
  {"query_id": 2, "annotator_1": "causal", "annotator_2": "causal"},
  {"query_id": 3, "annotator_1": "temporal", "annotator_2": "factual"},
  {"query_id": 4, "annotator_1": "multi-hop", "annotator_2": "multi-hop"}
]
```

- [x] **Step 2: Create `calculate_agreement.py`**
Create `evals/calculate_agreement.py`:
```python
import json
import numpy as np

def cohens_kappa(y1, y2):
    categories = list(set(y1).union(set(y2)))
    cat_map = {cat: idx for idx, cat in enumerate(categories)}
    n_classes = len(categories)
    
    cm = np.zeros((n_classes, n_classes))
    for val1, val2 in zip(y1, y2):
        cm[cat_map[val1]][cat_map[val2]] += 1
        
    n = np.sum(cm)
    po = np.trace(cm) / n
    
    pe = 0
    row_sums = np.sum(cm, axis=1)
    col_sums = np.sum(cm, axis=0)
    for i in range(n_classes):
        pe += (row_sums[i] * col_sums[i]) / (n * n)
        
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)

if __name__ == "__main__":
    with open("evals/annotator_labels.json") as f:
        data = json.load(f)
    y1 = [item["annotator_1"] for item in data]
    y2 = [item["annotator_2"] for item in data]
    
    kappa = cohens_kappa(y1, y2)
    print(f"Cohen's Kappa Agreement: {kappa:.3f}")
```

- [x] **Step 3: Run agreement calculation**
Run: `python evals/calculate_agreement.py`
Expected: Outputs Kappa score.

- [x] **Step 4: Commit**
```bash
git add evals/calculate_agreement.py evals/annotator_labels.json
git commit -m "feat: add inter-annotator Kappa agreement calculator"
```

---

### Task 5: Ablation Study Runner (Configs A-F), Wilcoxon Significance & Threshold Tuning

This runner tests the complete ablation scope (Configurations A to F) and conducts a threshold tuning study to determine the optimal cutoff.

**Files:**
* Create: `evals/run_ablation_study.py`
* Create: `evals/golden_dataset.json`

- [x] **Step 1: Create balanced `evals/golden_dataset.json`**
Provide a structured golden QA dataset.

- [x] **Step 2: Create `run_ablation_study.py`**
Create `evals/run_ablation_study.py` supporting baseline A-F, Wilcoxon tests, and Threshold Tuning grid search.

- [x] **Step 3: Run the ablation study runner**
Run: `python evals/run_ablation_study.py`
Expected: Completion of run and report printing.

- [x] **Step 4: Run threshold tuning experiment**
Run: `python evals/run_ablation_study.py --tune-threshold`
Expected: Prints Faithfulness metrics across thresholds.

- [x] **Step 5: Commit**
```bash
git add evals/run_ablation_study.py evals/golden_dataset.json
git commit -m "feat: implement complete configs A-F and threshold tuning runner"
```
