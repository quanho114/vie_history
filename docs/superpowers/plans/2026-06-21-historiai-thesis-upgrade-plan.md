# Implementation Plan: HistoriAI Thesis-Grade System Upgrade

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Elevate HistoriAI from a prototype-grade RAG application to a research-grade Agentic AI system by implementing a Reproducible Evaluation Framework, NLI Singleton Citation checking with claim extraction, local NetworkX GraphRAG ranking, structured Historical Reasoning with evidence mapping, and Observability Tracing.

---

## Task List

### Phase 0: Stabilization (Sprint 0)

#### Task 0.1: Build Claim Extraction Layer
**Description:** Implement `claim_extractor.py` to segment compound sentences into distinct, atomic claims to prevent verification inaccuracies on complex statements, assigning a structural type (e.g., `event`, `actor`, `location`).
- **Acceptance criteria:**
  - [ ] Extracts clean, atomic claim sentences from any given paragraph.
  - [ ] Assigns correct classification types to each claim.
- **Verification:**
  - [ ] Test suite: `pytest apps/api/tests/unit/test_claim_extractor.py` passes.
- **Dependencies:** None
- **Files likely touched:**
  - `apps/api/app/services/citation/claim_extractor.py` (Create)
  - `apps/api/tests/unit/test_claim_extractor.py` (Create)
- **Estimated scope:** Small

#### Task 0.2: Standardize Citation Schema and Evidence Grounding
**Description:** Define citation output models mapping individual claims to source citations and prepare utility functions for mapping elements.
- **Acceptance criteria:**
  - [ ] Establish type-safe citation structures.
  - [ ] Expose helper mappings between claims and raw document sources.
- **Verification:**
  - [ ] Running type checks passes: `mypy apps/api/app/services/citation/`
- **Dependencies:** Task 0.1
- **Files likely touched:**
  - `apps/api/app/services/citation/schema.py` (Create)
- **Estimated scope:** XS

#### Task 0.3: Configuration Flags and Dependency Clean Up
**Description:** Add config parameters to toggle individual module paths (e.g., `hybrid`, `reranker`, `graph`, `verification`) to support clean ablation runs. Clean up unused libraries or redundant test artifacts.
- **Acceptance criteria:**
  - [ ] Settings schema supports toggling Agent subsystems.
  - [ ] Workspace environments are optimized for clean runs.
- **Verification:**
  - [ ] System runs without error under base configs: `pytest apps/api/tests/`
- **Dependencies:** None
- **Files likely touched:**
  - `apps/api/app/core/config.py` (Modify)
- **Estimated scope:** Small

---

### Phase 1: Scientific Validation (Sprint 1)

#### Task 1.1: Implement NLI Model Singleton
**Description:** Implement `NLIModel` caching tokenizer and model in memory, ensuring GPU/device checks are done once. Expose batch inference capability.
- **Acceptance criteria:**
  - [ ] Model loads only once (Singleton pattern).
  - [ ] Supports batch NLI classification `verify_batch(premises: list[str], hypotheses: list[str])`.
- **Verification:**
  - [ ] Test suite: `pytest apps/api/tests/unit/test_nli_singleton.py` passes.
- **Dependencies:** None
- **Files likely touched:**
  - `apps/api/app/services/citation/nli_model.py` (Create)
  - `apps/api/tests/unit/test_nli_singleton.py` (Create)
- **Estimated scope:** Small

#### Task 1.2: Implement Pre-filters and Calibrated Scorer
**Description:** Implement entity matching in `entity_checker.py` and numeric checks in `numeric_checker.py`. Update `verifier.py` to route claims to the Claim Extraction Layer, run NLI batch inference via the singleton, calibrate outputs via scaling, and compute calibrated scores using the 60% NLI-weight formula.
- **Acceptance criteria:**
  - [ ] Entity matcher checks exact and soft entity match overlaps.
  - [ ] Numeric matcher checks matching numbers in generated sentences vs source premises.
  - [ ] `verifier.py` computes the weighted calibrated score formula: $0.15 \times Entity + 0.15 \times Numeric + 0.10 \times Temporal + 0.60 \times NLI$.
- **Verification:**
  - [ ] Test suite: `pytest apps/api/tests/unit/test_citation_verifier.py` passes.
- **Dependencies:** Task 0.2, Task 1.1
- **Files likely touched:**
  - `apps/api/app/services/citation/entity_checker.py` (Create)
  - `apps/api/app/services/citation/numeric_checker.py` (Create)
  - `apps/api/app/services/citation/verifier.py` (Modify)
- **Estimated scope:** Medium

#### Task 1.3: Implement NLI Threshold Calibration
**Description:** Implement `calibration.py` to load `evals/annotator_labels.json`, compute F1-score across threshold boundaries, and identify the optimal F1 threshold instead of hardcoding.
- **Acceptance criteria:**
  - [ ] Script reads human-annotated pairs.
  - [ ] Sweeps threshold values (0.0 to 1.0) and reports optimal threshold.
- **Verification:**
  - [ ] Run: `python apps/api/app/services/citation/calibration.py` outputs optimal threshold metrics.
- **Dependencies:** Task 1.2
- **Files likely touched:**
  - `apps/api/app/services/citation/calibration.py` (Create)
- **Estimated scope:** Small

#### Task 1.4: Evaluation Experiment Controller Setup
**Description:** Set up directory structure for versioned experiments and code the Experiment Controller (`experiment.py`, `config_loader.py`, `result_manager.py`).
- **Acceptance criteria:**
  - [ ] Config loader reads YAML configurations safely.
  - [ ] Result manager creates structured outputs under `evals/results/exp_xxx/`.
- **Verification:**
  - [ ] Test suite: `pytest evals/tests/test_experiment_controller.py` passes.
- **Dependencies:** None
- **Files likely touched:**
  - `evals/experiments/config_loader.py` (Create)
  - `evals/experiments/result_manager.py` (Create)
  - `evals/experiments/experiment.py` (Create)
- **Estimated scope:** Medium

#### Task 1.5: Implement Deterministic and Semantic Evaluators
**Description:** Code the individual evaluator modules under `evals/evaluators/`: `deterministic_evaluator.py`, `semantic_evaluator.py`, `retrieval_evaluator.py`, `citation_evaluator.py`.
- **Acceptance criteria:**
  - [ ] `deterministic_evaluator.py` checks entity, numeric and temporal consistency. Exposes Plan Validity Score: (Required Tools Selected) / (Total Expected Tools).
  - [ ] `semantic_evaluator.py` uses embedding model similarity.
- **Verification:**
  - [ ] Test suite: `pytest evals/tests/test_evaluators.py` passes.
- **Dependencies:** Task 1.4
- **Files likely touched:**
  - `evals/evaluators/deterministic_evaluator.py` (Create)
  - `evals/evaluators/semantic_evaluator.py` (Create)
  - `evals/evaluators/retrieval_evaluator.py` (Create)
  - `evals/evaluators/citation_evaluator.py` (Create)
- **Estimated scope:** Medium

#### Task 1.6: Implement RAGAS Evaluator and Runner CLI
**Description:** Implement `ragas_evaluator.py` and rewrite the CLI runner in `evals/runner.py`. Supports `--sample-size 50` (stratified balanced) and `--full-eval` modes. Runs queries through Naive, Hybrid, Graph, and Agentic pipelines.
- **Acceptance criteria:**
  - [ ] CLI runner coordinates pipeline runs and writes experiment folder outputs.
  - [ ] Integrates RAGAS evaluation when API keys are available, and deterministic evaluators.
- **Verification:**
  - [ ] Run: `python evals/runner.py --sample-size 4` completes successfully.
- **Dependencies:** Task 1.5
- **Files likely touched:**
  - `evals/evaluators/ragas_evaluator.py` (Create)
  - `evals/runner.py` (Create/Overwrite)
- **Estimated scope:** Medium

### Checkpoint: Phase 1 (Sprint 1)
- [ ] Evaluation CLI executes with `--sample-size 4` successfully.
- [ ] Local deterministic evaluations calculate factual, entity, and numeric consistency scores without mock inputs.
- [ ] NLI verifier runs singleton batch verification.

---

### Phase 2: Retrieval Enhancement (Sprint 2)

#### Task 2.1: Graph Exporter & Cache
**Description:** Implement graph caching and NetworkX graph loader. Queries Neo4j database to build and cache a local `DiGraph` representation in memory, writing metadata records.
- **Acceptance criteria:**
  - [ ] Graph cache saves and loads binary pickle at `/apps/api/storage/graph_cache/graph.pkl`.
  - [ ] Exports metadata tracking node count, edge count, Neo4j version, and timestamps to `metadata.json`.
- **Verification:**
  - [ ] Test suite: `pytest apps/api/tests/unit/test_graph_cache.py` passes.
- **Dependencies:** None
- **Files likely touched:**
  - `apps/api/app/services/graph/graph_cache.py` (Create)
  - `apps/api/app/services/graph/analytics/graph_exporter.py` (Create)
- **Estimated scope:** Small

#### Task 2.2: NetworkX Graph Analytics
**Description:** Calculate PageRank, Degree Centrality, and Betweenness Centrality on the local NetworkX graph. Save computed scores into cached node properties.
- **Acceptance criteria:**
  - [ ] Centrality parameters computed using NetworkX algorithms.
  - [ ] Save computed scores to nodes properties and serialize the final map.
- **Verification:**
  - [ ] Run: `python -m app.services.graph.analytics.pagerank` computes scores correctly.
- **Dependencies:** Task 2.1
- **Files likely touched:**
  - `apps/api/app/services/graph/analytics/centrality.py` (Create)
  - `apps/api/app/services/graph/analytics/pagerank.py` (Create)
- **Estimated scope:** Small

#### Task 2.3: Upgrade GraphRAG Retrieval and Entity Resolution
**Description:** Implement alias matching in `entity_resolver.py`. Upgrade graph context retrieval in `graph_reasoner.py` to match entities by name or aliases, read PageRank/centrality importances from cache, and boost vector retrieval outputs.
- **Acceptance criteria:**
  - [ ] Entity resolution maps aliases to canonical names.
  - [ ] Document chunks are re-ranked based on entity importance scores.
- **Verification:**
  - [ ] Test suite: `pytest apps/api/tests/unit/test_graphrag_retrieval.py` passes.
- **Dependencies:** Task 2.2
- **Files likely touched:**
  - `apps/api/app/services/graph/entity_resolver.py` (Create)
  - `apps/api/app/services/graph/graph_reasoner.py` (Modify)
- **Estimated scope:** Medium

### Checkpoint: Phase 2 (Sprint 2)
- [ ] Graph analytics compute PageRank and cache graph files.
- [ ] GraphRAG boosts retrieved context using NetworkX page rank importances.

---

### Phase 3: Explainability Layer (Sprint 3)

#### Task 3.1: Rebrand & Restructure Historical Reasoning Engine
**Description:** Refactor and rename the reasoning engine to `HistoricalReasoningEngine`. Change output fields to return structured tuples (causes, consequences, turning_points, actors, timeline, conflicts) with confidence scores and explicit `evidence_links`.
- **Acceptance criteria:**
  - [ ] Output schema matches the spec.
  - [ ] Ground confidence parameters directly in computed verifier scores.
- **Verification:**
  - [ ] Test suite: `pytest apps/api/tests/unit/test_reasoning_engine.py` passes.
- **Dependencies:** None
- **Files likely touched:**
  - `apps/api/app/services/agent/historical_reasoning_engine.py` (Modify)
- **Estimated scope:** Medium

#### Task 3.2: Log Tracing and API Routing
**Description:** Write logs containing planning decisions, tool latencies, token counts, and verifications to `/apps/api/storage/traces/{query_id}.json`. Use `action_reason` parameters and map `experiment_id`. Create FastAPI routes to retrieve trace details.
- **Acceptance criteria:**
  - [ ] JSON trace logs successfully write to storage.
  - [ ] Traces log operational choices using `action_reason` instead of internal model chain-of-thoughts.
- **Verification:**
  - [ ] Run test: `pytest apps/api/tests/integration/test_trace_api.py` passes.
- **Dependencies:** None
- **Files likely touched:**
  - `apps/api/app/services/agent/trace_logger.py` (Create)
  - `apps/api/app/api/endpoints/traces.py` (Create)
- **Estimated scope:** Small

#### Task 3.3: Frontend Trace Viewer Component
**Description:** Create the React Trace Viewer Page and Hook it to route definitions. Renders execution plans, latencies, and claim validation scores cleanly.
- **Acceptance criteria:**
  - [ ] Trace viewer parses JSON output from trace endpoint correctly.
  - [ ] Cards display planning steps, tools, latencies, and calibrated verification verdicts.
- **Verification:**
  - [ ] Frontend builds cleanly.
- **Dependencies:** Task 3.2
- **Files likely touched:**
  - `apps/web/src/pages/AgentTraceViewerPage.tsx` (Create)
  - `apps/web/src/pages/index.ts` (Modify)
- **Estimated scope:** Medium

### Checkpoint: Complete
- [ ] All verification steps pass.
- [ ] Full ablation evaluations execute and output metrics.
- [ ] Ready for human review.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| NLI model performance slows down verification | High | Use singleton cache + batching claims to parallelize NLI inference. |
| Neo4j data size grows, causing NetworkX export memory leaks | Low | Export only active nodes and relationship types (`KnowledgeNode`) in subgraphs. |
| API Judge rate limits during Research mode | Medium | Runner implements delay backoffs and saves chunked intermediate results to prevent progress loss. |
