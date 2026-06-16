# HistoriAI Architecture

HistoriAI is organized as a focused monorepo:

```text
Vie_history/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── agents/        # Query orchestration and response pipeline
│   │   │   ├── api/routes/    # FastAPI route layer
│   │   │   ├── core/          # Config, database, cache, security, logging
│   │   │   ├── models/        # SQLAlchemy models
│   │   │   ├── retrieval/     # Retrieval adapters used by agents
│   │   │   ├── schemas/       # Pydantic API contracts
│   │   │   ├── services/      # Ingestion, retrieval, agent primitives
│   │   │   └── workers/       # Queue task entrypoints
│   │   └── tests/
│   └── web/
│       └── src/
│           ├── components/
│           ├── pages/
│           ├── stores/
│           └── lib/
├── data/                       # Seed data and normalization dictionaries
├── evals/                      # Golden retrieval/groundedness datasets
├── scripts/                    # Operational scripts
└── docs/
```

## Runtime Flow

```text
React ChatPage
  -> Zustand chatStore
  -> POST /api/v1/query/stream
  -> AgentOrchestrator
  -> QueryExpander
  -> SQLRetriever first, hybrid vector/BM25 fallback
  -> LexicalReranker
  -> AnswerSynthesizer with citation validation
  -> ResponseBuilder citations + trace
  -> SSE tokens/citations/trace
```

## Ingestion Flow

```text
POST /api/v1/ingest/url
  -> IngestService
  -> IngestionPipeline
  -> metadata extraction
  -> content files under storage/documents
  -> Document + DocumentChunk rows
  -> best-effort Qdrant indexing
```

If embeddings or Qdrant are unavailable, ingestion still persists chunks in
PostgreSQL. Query falls back to SQL retrieval so the system remains usable in
development.

## File Ingestion Flow

```text
POST /api/v1/ingest/file
  -> UploadFile saved under storage/uploads
  -> FileExtractor
  -> text/markdown direct read or PDF text extraction through pypdfium2
  -> same document/chunk/index path as URL ingestion
```

## Current Production Gaps

- The answer synthesizer can call configured LLM providers and validates
  citation markers per claim; it falls back to extractive answers when no
  provider is configured or validation fails.
- BM25 is in-memory; production lexical search should use a persistent index.
- Worker queue entrypoints exist, but URL ingestion currently runs
  synchronously for developer clarity.
- Eval scripts exist with a small seed dataset; RAGAS-style faithfulness metrics
  still need a larger curated corpus.
