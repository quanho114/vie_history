# Design Spec: Replace Elasticsearch with Meilisearch

This design document outlines the steps to replace the Elasticsearch search service with Meilisearch in the HistoriAI codebase. This will reduce memory overhead and speed up local development setups.

## 1. Objectives

- Replace Elasticsearch with Meilisearch as the lexical search engine (BM25).
- Retain port mapping `12707` on the host to avoid changing port configurations elsewhere.
- Keep the Python interface compatible so other backend layers (query service, ingestion pipeline) require minimal adjustments.
- Retain the local in-memory BM25 fallback mechanism if Meilisearch is unavailable.

## 2. Approach

We will use the official `meilisearch-python-sdk` library to interact with Meilisearch. Since Meilisearch has native support for async operations, we will build a `MeilisearchBM25` service class to replace `ElasticsearchBM25`.

## 3. Detailed Design

### Section 1: Docker & Environment Configurations

#### `docker-compose.yml`
Replace the `elasticsearch` service definition with `meilisearch`:

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

Replace volume `es_data` with `meili_data` under the root level `volumes` block:
```yaml
volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  meili_data:
  neo4j_data:
  neo4j_logs:
```

#### `.env` and `.env.example`
Remove the Elasticsearch environment variables:
```ini
# ELASTICSEARCH_URL=http://localhost:12707
```

Add Meilisearch configuration keys:
```ini
# Meilisearch
MEILISEARCH_URL=http://localhost:12707
MEILISEARCH_MASTER_KEY=meili_master_key_secret
MEILISEARCH_INDEX=historiai_chunks
```

---

### Section 2: Code Integration & Dependencies

#### `apps/api/pyproject.toml`
Update dependencies:
- Remove: `"elasticsearch>=8.0.0,<9.0.0"`
- Add: `"meilisearch-python-sdk>=2.1.0"`

#### `apps/api/app/core/config.py`
Update settings definition to map the new env variables:
```python
    # Meilisearch
    MEILISEARCH_URL: str = "http://localhost:12707"
    MEILISEARCH_MASTER_KEY: str = "meili_master_key_secret"
    MEILISEARCH_INDEX: str = "historiai_chunks"
```

#### `apps/api/app/services/retrieval/meilisearch_bm25.py`
Create a new file `apps/api/app/services/retrieval/meilisearch_bm25.py` exposing:
- `class MeilisearchBM25`:
  - `initialize(self) -> bool`: Checks/creates `historiai_chunks` index. Sets `searchable_attributes`, `filterable_attributes` (`["document_id", "year"]`), and loads synonyms from `data/era_keywords.json`.
  - `search(self, query, top_k, filters, min_score) -> list[dict]`: Transforms filters to Meilisearch filter string (e.g. `year >= 1945 AND year <= 1950`) and queries the index.
  - `index_chunk(self, chunk)`: Adds a single chunk.
  - `index_chunks(self, chunks)`: Bulk-adds chunks.
  - `remove_chunk(self, chunk_id)`: Removes a chunk by ID.
  - `remove_by_document_id(self, document_id)`: Removes all chunks of a document.
  - `close(self)`: Closes client.
- `async def get_meilisearch_bm25() -> MeilisearchBM25`
- `async def close_meilisearch_bm25() -> None`

---

### Section 3: System-wide Updates

#### `apps/api/app/services/retrieval/query_service.py`
Change imports from `elasticsearch_bm25` to `meilisearch_bm25`.
Inside `QueryService`, rename references from `es_bm25` to `meili_bm25` and ensure fallback to local BM25 works.

#### `apps/api/app/services/ingestion/service.py`
Replace `get_elasticsearch_bm25` imports and calls with `get_meilisearch_bm25`.

#### `apps/api/app/events/handlers.py`
Initialize and close `meili_bm25` connections on startup and shutdown events.

#### `scripts/setup.sh`
Change the service list started by docker-compose from `elasticsearch` to `meilisearch`.
Update Meilisearch health check URL to `http://localhost:12707/health`.
