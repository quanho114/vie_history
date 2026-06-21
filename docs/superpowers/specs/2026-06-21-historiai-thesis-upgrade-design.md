# Design Specification: HistoriAI Thesis-Grade System Upgrade

This document outlines the architectural changes required to elevate **HistoriAI** from a prototype RAG model to a thesis-grade, validated Vietnamese Historical QA system.

---

## 1. Architectural Overview

The core system will transition from hardcoded/fake baselines to a fully validated system with verifiable contributions in:
1. **P0: Reproducible Evaluation Framework**: Verifiable, reproducible evaluation runner with development/research modes, separating metrics into System, Retrieval, and Generation layers, featuring a deterministic Plan Validity Score.
2. **P1: Optimized Citation Verification Engine & Claim Extractor**: Dedicated Claim Extraction Layer outputting typed atomic claims, NLI confidence calibration via scaling, singleton model loading, batch inference, entity/numeric pre-filters, threshold calibration via F1 optimization, and calibrated citation scoring with 60% NLI semantic weight.
3. **P2: Alias-aware Knowledge Graph Retrieval Enhancement**: Local NetworkX-based centrality, PageRank, and alias resolution with local binary/property caching containing detailed graph metadata (no mandatory Neo4j GDS).
4. **P3: Historical Reasoning Engine**: Structured reasoning fields (causes, consequences, turning points, actors, timeline, conflicts) with confidence scores linked directly to verifier outputs, and explicit source evidence links.
5. **P4: Agent Observability Tracing**: Structured agent execution traces (`action_reason` based, avoiding generic CoT logs) versioned by `experiment_id` saved to storage and visualized in a frontend Trace Viewer.

---

## 2. Component Designs

### P0: Reproducible Evaluation Framework
To resolve the mock metrics in `run_ablation_study.py`, we introduce a robust, non-hardcoded evaluation pipeline with an Experiment Controller for full reproducibility.

#### Directory Structure
```
evals/
├── dataset/
│   └── history_qa.json                 # Core historical QA benchmark (4902 lines)
├── configs/
│   ├── naive.yaml                      # Config for Naive RAG (Vector only)
│   ├── hybrid.yaml                     # Config for Hybrid RAG (Vector + BM25)
│   ├── graph.yaml                      # Config for GraphRAG (Hybrid + KG)
│   └── agentic.yaml                    # Config for Agentic HistoriAI (Orchestration + Verification)
├── experiments/
│   ├── experiment.py                   # Experiment controller execution layer
│   ├── config_loader.py                # Load YAML parameters safely
│   └── result_manager.py               # Manage structured results per experiment ID
├── runner.py                           # CLI entry point to run evaluations
├── pipeline_runner.py                  # Integrates queries with different configurations
├── evaluators/
│   ├── __init__.py
│   ├── ragas_evaluator.py              # API-based RAGAS (Faithfulness, Relevancy, Recall)
│   ├── deterministic_evaluator.py      # Local deterministic verification metrics
│   ├── citation_evaluator.py           # Specific citation metrics (Precision, Coverage)
│   ├── semantic_evaluator.py           # Sentence embeddings similarity vs references
│   └── retrieval_evaluator.py          # Context overlap, precision, and recall
└── results/
    └── exp_xxx/                        # Versioned experiment output folder
         ├── config.yaml                # Frozen configuration used
         ├── answers.json               # Raw answers and source chunks
         ├── metrics.json               # Metric calculations (RAGAS + Deterministic)
         └── logs.json                  # Trace logs and latency records
```

#### Dual Evaluation Mode
- **Development Mode (`--sample-size 50`)**: Runs on a stratified, balanced sample (10 factual, 10 timeline, 10 comparison, 10 multihop, 10 causal) to enable fast testing.
- **Research Mode (`--full-eval`)**: Executes over the complete `history_qa.json` dataset to gather scientific defense-ready metrics.

#### Evaluator Types (Reproducible Evaluation Framework)
1. **System Metrics**:
   - Latency (seconds)
   - Token Usage (Prompt & Completion counts)
   - Retrieval Time (ms)
   - **Plan Validity Score**: Checks if the planner successfully scheduled expected nodes/tools for a given query type:
     $$\text{Plan Validity} = \frac{\text{Required Tools Selected}}{\text{Total Expected Tools}}$$
   - Tool Efficiency (ratio of useful tool calls to total tool calls)
   - Replanning Success Rate (counts how many replanning/retry triggers led to a passed verification check)
2. **Retrieval Metrics**:
   - Context Recall & Precision
   - Mean Reciprocal Rank (MRR)
   - Hit@K (for K=3, 5, 10)
3. **Generation Metrics**:
   - Faithfulness (NLI-based factuality)
   - Answer Relevancy (relevance to user query)
   - Citation Accuracy (ratio of supported claims to total claims)
   - Semantic Similarity (similarity of generated answer against ground truth reference)

---

### P1: Optimized Citation Verification Engine & Claim Extractor
Redesigns the citation verifier to run efficiently locally without reloading the model on every query.

#### Claim Extraction Layer
Before verifying, generated sentences are processed by a dedicated extraction step to split compound sentences into individual atomic claims, assigning a structural type.
- **Example**: *"Nguyễn Huệ lên ngôi Hoàng đế năm 1788 và đánh bại quân Thanh năm 1789"* is split into:
```json
[
  {
    "text": "Nguyễn Huệ lên ngôi Hoàng đế năm 1788",
    "type": "event"
  },
  {
    "text": "Nguyễn Huệ đánh bại quân Thanh năm 1789",
    "type": "event"
  }
]
```
*Supported types: `event`, `actor`, `location`, `temporal`, `concept`.*

#### NLI Confidence Calibration
Raw probabilities from the NLI classification model (entailment probability) undergo temperature scaling or Platt scaling to calibrate prediction scores against dataset parameters before final metric weighting.

#### Structural Files
- `apps/api/app/services/citation/claim_extractor.py`: Tokenizes, splits conjunctions, and extracts typed atomic claims.
- `apps/api/app/services/citation/nli_model.py`: Singleton wrapper class (`NLIModel`) caching the local tokenizer and `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` model in memory. Loaded once during app startup or lazy-loaded on the first call.
- `apps/api/app/services/citation/entity_checker.py`: Pre-filter to check exact and soft entity match.
- `apps/api/app/services/citation/numeric_checker.py`: Pre-filter to check numeric matches.
- `apps/api/app/services/citation/calibration.py`: Optimizes classification thresholds and scaling factors on `evals/annotator_labels.json` to find the mathematically optimal F1 score threshold.
- `apps/api/app/services/citation/verifier.py`: Coordinates the checks.

#### Calibrated Verification Score
$$Score_{final} = 0.15 \times Score_{entity} + 0.15 \times Score_{numeric} + 0.10 \times Score_{temporal} + 0.60 \times Score_{NLI}$$
*NLI semantic entailment represents the largest weight (60%) since verification is fundamentally semantic.*

---

### P2: Alias-aware Knowledge Graph Retrieval Enhancement
Provides advanced graph centrality and importance scoring using a local NetworkX graph built from Neo4j, using a local binary cache.

#### Caching Mechanism
- Save built graph structure and computed metrics to `/apps/api/storage/graph_cache/graph.pkl`.
- Save node properties, centrality metrics, and build metadata:
```
apps/api/storage/graph_cache/
├── graph.pkl
├── metrics.json
└── metadata.json
```
- `metadata.json` tracks Neo4j version, node count, edge count, and generated timestamp.
- Centrality/PageRank scores are updated daily or manually rebuilt via an endpoint, rather than recalculated during every query.
- System reads importance scores directly from this cache at runtime.

#### Structural Files
- `apps/api/app/services/graph/entity_resolver.py`: Matches historical names against the `name` and `aliases` array property in Neo4j.
- `apps/api/app/services/graph/graph_cache.py`: Manages the serialization and loading of `/apps/api/storage/graph_cache/graph.pkl`.
- `apps/api/app/services/graph/analytics/`:
  - `graph_exporter.py`: Queries Neo4j database to build a NetworkX `DiGraph` representation in memory.
  - `centrality.py`: Calculates degree and closeness centrality locally.
  - `pagerank.py`: Runs local PageRank to identify key historical entities.
- `apps/api/app/services/graph/graph_reasoner.py`: Combines Vector scores with NetworkX centrality scores to prioritize/boost document chunks.

---

### P3: Historical Reasoning Engine
Rebrands the "Causal World Model" to focus on structured reasoning with clear evidence mapping, grounding confidence scores directly in verifier outputs instead of LLM generation.

#### Restructured Schema
Renames the service to `HistoricalReasoningEngine` and outputs structured fields containing factors, confidence scores (computed from matching citation verification scores), and associated source markers (`evidence_links`):
```json
{
  "causes": [
    {
      "factor": "Khủng hoảng chính trị nhà Hồ cuối thế kỷ XIV",
      "confidence": 0.88,
      "evidence_links": ["S1", "S3"]
    }
  ],
  "consequences": [
    {
      "factor": "Đại Ngu rơi vào ách thống trị của nhà Minh",
      "confidence": 0.92,
      "evidence_links": ["S2", "S4"]
    }
  ]
}
```

---

### P4: Agent Observability Tracing
Logs execution traces to a local file system cache to expose the agent's operation trace, avoiding generic chain-of-thought storage.

#### Trace Formatting
Rename `reason` inside the log trace steps to `action_reason`. The content must describe strictly structural/operational choices rather than free-form LLM internal reasoning.
- **Good**: `"action_reason": "Entity resolution triggered for multi-hop relationship retrieval between 'Nguyễn Huệ' and 'Quang Trung'."`
- **Bad**: `"reason": "I think Nguyễn Huệ and Quang Trung are the same person so I am looking for both in Neo4j."`

#### Schema (`storage/traces/{query_id}.json`)
Stores structured JSON logs mapping `experiment_id`, `query_id`, plan steps, tool latencies, token count, retry counts, verification scores, and actual tools used.

#### Frontend Trace Component
An **Agent Execution Trace Page** (`/admin/traces` or `/trace/:query_id`) displaying:
- Collapsible trace log cards detailing each step.
- Planning phase (Goal + Steps).
- Executed tools log with latency badges.
- Verification panel displaying claim status (VERIFIED/REVIEW/REJECT) and calibrated scores.

---

## 3. Implementation Roadmap

### Sprint 0: Stabilization (Verification Foundation)
- [ ] Implement `claim_extractor.py` to extract typed atomic claims.
- [ ] Establish standardized citation schemas and evidence grounding layout.
- [ ] Implement config flags and clean up redundant packages/test dependencies.

### Sprint 1: Scientific Validation (Evaluation & Citation Engine)
- [ ] Implement `evals/experiments/` structure and Experiment Controller.
- [ ] Write evaluators: `ragas_evaluator.py`, `deterministic_evaluator.py` (with Plan Validity Score), `citation_evaluator.py`, `semantic_evaluator.py`, and `retrieval_evaluator.py`.
- [ ] Implement the singleton pattern in `nli_model.py` for model loading.
- [ ] Write NLI threshold calibration logic in `calibration.py` using `annotator_labels.json`.
- [ ] Refactor `verifier.py` to run batch NLI inference and evaluate the calibrated score.

### Sprint 2: Retrieval Enhancement (Graph Enhancement)
- [ ] Implement `graph_cache.py` to serialize NetworkX graphs into `/apps/api/storage/graph_cache/graph.pkl` and metadata.json.
- [ ] Build local centrality/PageRank computations in `apps/api/app/services/graph/analytics/`.
- [ ] Upgrade graph context retrieval to merge vector scores with cache-retrieved centrality scores.

### Sprint 3: Explainability Layer (Reasoning & Trace UI)
- [ ] Rename and refactor `HistoricalReasoningEngine` to use the structured evidence, mapping confidence to verifier scores.
- [ ] Implement query logging using `action_reason` to `/apps/api/storage/traces/{query_id}.json`.
- [ ] Expose trace log API routes.
- [ ] Build the frontend trace viewer interface.
