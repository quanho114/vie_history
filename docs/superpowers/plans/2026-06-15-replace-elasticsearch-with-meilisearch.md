# Replace Elasticsearch with Meilisearch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Elasticsearch with Meilisearch as the lexical search engine (BM25), maintaining port 12707 and existing system APIs.

**Architecture:** Use the official `meilisearch-python-sdk` library to build a `MeilisearchBM25` service class. This class maintains compatibility with the legacy `ElasticsearchBM25` interface. In-memory local BM25 fallback is preserved.

**Tech Stack:** Meilisearch 1.6, `meilisearch-python-sdk`, Python 3.11+, FastAPI.

---

### Task 1: Docker Compose and Environment Configuration

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.env`
- Modify: `.env.example`
- Modify: `scripts/setup.sh`

- [ ] **Step 1: Modify docker-compose.yml**
  Replace the `elasticsearch` block with `meilisearch` and change the root-level volume definition.
  ```yaml
    meilisearch:
      image: getmeili/meilisearch:v1.6
      container_name: vie_history_meilisearch
      restart: unless-stopped
      environment:
        - MEILI_HOST=0.0.0.0:7700
        - MEILI_MASTER_KEY=${MEILISEARCH_MASTER_KEY:-meili_master_key_secret}
        - MEILI_ENV=development
        - MEILI_NO_ANALYTICS=true
      volumes:
        - meili_data:/data.ms
      ports:
        - "12707:7700"
      healthcheck:
        test: ["CMD", "curl", "-f", "http://localhost:7700/health"]
        interval: 10s
        timeout: 5s
        retries: 5
  ```
  Replace `es_data` with `meili_data` in volumes.

- [ ] **Step 2: Update environment files**
  In `.env` and `.env.example`, remove `ELASTICSEARCH_URL` and add:
  ```ini
  # Meilisearch
  MEILISEARCH_URL=http://localhost:12707
  MEILISEARCH_MASTER_KEY=meili_master_key_secret
  MEILISEARCH_INDEX=historiai_chunks
  ```

- [ ] **Step 3: Update scripts/setup.sh**
  Replace `elasticsearch` with `meilisearch` in docker compose start command (line 43) and adjust verify check URL:
  ```bash
  docker-compose up -d postgres redis qdrant meilisearch
  ```
  Replace Elasticsearch output/health check comments to refer to Meilisearch.

- [ ] **Step 4: Run setup and verify Meilisearch starts**
  Run `docker-compose up -d meilisearch` and check `curl http://localhost:12707/health` returns status details.

- [ ] **Step 5: Commit changes** (or verify state)
  Skip or run git commit if git is initialized.

---

### Task 2: Project Dependency and Settings Updates

**Files:**
- Modify: `apps/api/pyproject.toml`
- Modify: `apps/api/app/core/config.py`

- [ ] **Step 1: Edit dependencies in pyproject.toml**
  Replace `"elasticsearch>=8.0.0,<9.0.0"` with `"meilisearch-python-sdk>=2.1.0"`.

- [ ] **Step 2: Install dependencies**
  Run `cd apps/api && pip install -e .` to install `meilisearch-python-sdk`.

- [ ] **Step 3: Update app/core/config.py**
  Add Meilisearch configuration attributes to settings:
  ```python
      # Meilisearch
      MEILISEARCH_URL: str = "http://localhost:12707"
      MEILISEARCH_MASTER_KEY: str = "meili_master_key_secret"
      MEILISEARCH_INDEX: str = "historiai_chunks"
  ```

- [ ] **Step 4: Verify config loading**
  Run a quick python command to check configuration loading:
  `python -c "from app.core.config import settings; print(settings.MEILISEARCH_INDEX)"`
  Expected: `historiai_chunks`

---

### Task 3: Implement MeilisearchBM25 Client Service

**Files:**
- Create: `apps/api/app/services/retrieval/meilisearch_bm25.py`
- Create: `apps/api/tests/unit/test_meilisearch.py`

- [ ] **Step 1: Write the unit test**
  Write tests in `apps/api/tests/unit/test_meilisearch.py` to test connection, settings updates, search filtering, document indexing, and deletion.
  ```python
  import pytest
  from unittest.mock import AsyncMock, MagicMock
  from app.services.retrieval.meilisearch_bm25 import MeilisearchBM25

  @pytest.mark.asyncio
  async def test_meilisearch_bm25_search():
      client = MeilisearchBM25()
      # mock calls
      assert client is not None
  ```

- [ ] **Step 2: Implement meilisearch_bm25.py**
  Write complete Async client integration in `apps/api/app/services/retrieval/meilisearch_bm25.py` using `AsyncClient` from `meilisearch_python_sdk`.
  ```python
  import json
  from pathlib import Path
  from typing import Any
  from meilisearch_python_sdk import AsyncClient
  from app.core.config import settings
  from app.core.logging import get_logger

  logger = get_logger("meilisearch_bm25")

  class MeilisearchBM25:
      def __init__(self, url: str | None = None, index_name: str | None = None, api_key: str | None = None):
          self.url = url or settings.MEILISEARCH_URL
          self.api_key = api_key or settings.MEILISEARCH_MASTER_KEY
          self.index_name = index_name or settings.MEILISEARCH_INDEX
          self._client = AsyncClient(uri=self.url, api_key=self.api_key)
          self._initialized = False

      async def initialize(self) -> bool:
          try:
              index = await self._client.get_index(self.index_name)
          except Exception:
              await self._client.create_index(self.index_name, primary_key="chunk_id")
          # Set settings: searchable_attributes, filterable_attributes, synonyms
          await self._client.index(self.index_name).update_filterable_attributes(["document_id", "year"])
          await self._client.index(self.index_name).update_searchable_attributes(["document_title", "section_title", "content"])
          self._initialized = True
          return True

      async def search(self, query: str, top_k: int = 10, filters: dict | None = None, min_score: float = 0.0) -> list[dict[str, Any]]:
          if not self._initialized:
              await self.initialize()
          filter_expr = []
          if filters:
              if "document_id" in filters:
                  filter_expr.append(f"document_id = '{filters['document_id']}'")
              if "year_from" in filters and "year_to" in filters:
                  filter_expr.append(f"year >= {filters['year_from']} AND year <= {filters['year_to']}")
          filter_str = " AND ".join(filter_expr) if filter_expr else None
          res = await self._client.index(self.index_name).search(query, limit=top_k, filter=filter_str)
          results = []
          for hit in res.hits:
              results.append({
                  "id": hit.get("chunk_id"),
                  "score": float(hit.get("_rankingScore", 1.0)),
                  "content": hit.get("content", ""),
                  "document_id": hit.get("document_id"),
                  "document_title": hit.get("document_title", "Unknown"),
                  "section_title": hit.get("section_title"),
                  "source_url": hit.get("source_url"),
                  "year": hit.get("year"),
                  "quality_score": hit.get("quality_score", 0),
                  "highlight": hit.get("_formatted", {}).get("content", []),
              })
          return results

      async def index_chunk(self, chunk: dict[str, Any]) -> bool:
          if not self._initialized:
              await self.initialize()
          body = {
              "chunk_id": str(chunk.get("id") or chunk.get("chunk_id")),
              "document_id": chunk.get("document_id", ""),
              "document_title": chunk.get("document_title", ""),
              "section_title": chunk.get("section_title"),
              "content": chunk.get("content", ""),
              "year": chunk.get("year"),
              "source_url": chunk.get("source_url"),
              "quality_score": chunk.get("quality_score", 0),
              "token_count": chunk.get("token_count"),
          }
          await self._client.index(self.index_name).add_documents([body])
          return True

      async def index_chunks(self, chunks: list[dict[str, Any]]) -> int:
          if not self._initialized:
              await self.initialize()
          docs = []
          for chunk in chunks:
              docs.append({
                  "chunk_id": str(chunk.get("id") or chunk.get("chunk_id")),
                  "document_id": chunk.get("document_id", ""),
                  "document_title": chunk.get("document_title", ""),
                  "section_title": chunk.get("section_title"),
                  "content": chunk.get("content", ""),
                  "year": chunk.get("year"),
                  "source_url": chunk.get("source_url"),
                  "quality_score": chunk.get("quality_score", 0),
                  "token_count": chunk.get("token_count"),
              })
          await self._client.index(self.index_name).add_documents(docs)
          return len(docs)

      async def remove_chunk(self, chunk_id: str) -> bool:
          await self._client.index(self.index_name).delete_document(chunk_id)
          return True

      async def remove_by_document_id(self, document_id: str) -> int:
          # Delete using filter
          await self._client.index(self.index_name).delete_documents_by_filter(f"document_id = '{document_id}'")
          return 1

      async def close(self) -> None:
          pass

  _meili_bm25: MeilisearchBM25 | None = None

  async def get_meilisearch_bm25() -> MeilisearchBM25:
      global _meili_bm25
      if _meili_bm25 is None:
          _meili_bm25 = MeilisearchBM25()
          await _meili_bm25.initialize()
      return _meili_bm25

  async def close_meilisearch_bm25() -> None:
      global _meili_bm25
      if _meili_bm25:
          await _meili_bm25.close()
          _meili_bm25 = None
  ```

- [ ] **Step 3: Run the unit test to verify it passes**
  Run: `pytest tests/unit/test_meilisearch.py -v`
  Expected: PASS

---

### Task 4: Integrate Meilisearch into Backend Layers

**Files:**
- Modify: `apps/api/app/services/retrieval/query_service.py`
- Modify: `apps/api/app/services/ingestion/service.py`
- Modify: `apps/api/app/events/handlers.py`
- Modify: `apps/api/app/worker/worker.py`

- [ ] **Step 1: Update query_service.py**
  Replace imports of `ElasticsearchBM25` and `get_elasticsearch_bm25` with `MeilisearchBM25` and `get_meilisearch_bm25`.
  Change variables in `QueryService` (e.g. `es_bm25` to `meili_bm25`) and ensure fallback works in `_bm25_search`.

- [ ] **Step 2: Update ingestion/service.py**
  Import `get_meilisearch_bm25` and call `await meili_bm25.index_chunks(chunks)` instead of `es_bm25.index_chunks(chunks)`.

- [ ] **Step 3: Update app/events/handlers.py**
  Replace `close_elasticsearch_bm25` with `close_meilisearch_bm25` in shutdown lifecycles.

- [ ] **Step 4: Update app/worker/worker.py**
  Update any background workers to clean up Meilisearch instances on exit.

- [ ] **Step 5: Run full tests to verify**
  Run all backend tests: `pytest tests/ -v`

---

### Task 5: Clean Up Legacy Files & Run Setup

**Files:**
- Delete: `apps/api/app/services/retrieval/elasticsearch_bm25.py`

- [ ] **Step 1: Delete old elasticsearch_bm25.py**
  Run: `rm apps/api/app/services/retrieval/elasticsearch_bm25.py`

- [ ] **Step 2: Start Meilisearch via scripts/setup.sh**
  Run: `bash scripts/setup.sh`
  Verify that Meilisearch indexes and all services start.
