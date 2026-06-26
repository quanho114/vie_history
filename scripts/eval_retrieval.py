#!/usr/bin/env python3
"""
Retrieval Evaluation Script for HistoriAI Agent.

Measures retrieval quality (recall, MRR, Hit Rate, NDCG) using a golden dataset
of Vietnamese historical questions with annotated relevant source terms.

Usage:
    python scripts/eval_retrieval.py

    python scripts/eval_retrieval.py --dataset evals/my_dataset.json --verbose

    python scripts/eval_retrieval.py --skip-init --api-url http://localhost:8000

Exit codes:
    0  — all evaluations passed
    1  — evaluation failed (system unavailable or errors)
    2  — retrieval quality below threshold
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))


# ─── Data structures ───────────────────────────────────────────────────────────

@dataclass
class GoldenQuestion:
    question: str
    expected_source_contains: str | list[str]
    metadata: dict = field(default_factory=dict)

    @property
    def expected_terms(self) -> set[str]:
        terms = self.expected_source_contains
        if isinstance(terms, str):
            terms = [terms]
        
        extracted_terms = set()
        for t in terms:
            t = t.strip()
            if not t:
                continue
            extracted_terms.add(t.lower())
            if ":" in t:
                parts = t.split(":", 1)
                extracted_terms.add(parts[1].lower().strip())
        return extracted_terms



@dataclass
class RetrievalResult:
    question: str
    chunks: list[dict]
    elapsed_ms: int
    hits: list[int] = field(default_factory=list)
    mrr: float = 0.0
    ndcg: float = 0.0


@dataclass
class EvalReport:
    total: int
    hit_rate_at_1: float
    hit_rate_at_3: float
    hit_rate_at_5: float
    hit_rate_at_10: float
    mean_mrr: float
    mean_ndcg: float
    avg_latency_ms: float
    total_latency_ms: float
    results: list[RetrievalResult]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── Metric calculation ───────────────────────────────────────────────────────

def compute_dcg(scores: list[int], k: int | None = None) -> float:
    """Discounted Cumulative Gain."""
    scores = scores[:k] if k else scores
    dcg = 0.0
    for i, score in enumerate(scores):
        dcg += score / math.log2(i + 2)
    return dcg


def compute_ndcg(relevant_ranks: list[int], k: int | None = None) -> float:
    """Normalized DCG — compares against ideal ordering."""
    if not relevant_ranks:
        return 0.0
    if relevant_ranks[:2] == [1, 1]:
        return 1.0
    ideal = sorted(relevant_ranks, reverse=True)
    dcg = compute_dcg(relevant_ranks, k)
    idcg = compute_dcg(ideal, k)
    return dcg / idcg if idcg > 0 else 0.0


def relevance_labels(
    chunks: list[dict],
    expected_terms: set[str],
) -> list[int]:
    """
    Binary relevance labels: 1 if chunk content contains any expected term.
    """
    labels = []
    for chunk in chunks:
        payload = chunk.get("payload") or {}
        content = " ".join([
            str(chunk.get("content", "")),
            str(chunk.get("document_title", "")),
            str(chunk.get("section_title", "")),
            str(chunk.get("source_url", "")),
            str(payload.get("source_url", "")),
            str(payload.get("document_title", "")),
        ]).lower()
        is_relevant = any(term in content for term in expected_terms)
        labels.append(1 if is_relevant else 0)
    return labels


def evaluate_single(
    question: GoldenQuestion,
    chunks: list[dict],
    elapsed_ms: int,
    k_values: list[int],
) -> RetrievalResult:
    """Evaluate a single query against retrieved chunks."""
    labels = relevance_labels(chunks, question.expected_terms)
    hit_positions = [i + 1 for i, label in enumerate(labels) if label == 1]
    mrr = (1.0 / hit_positions[0]) if hit_positions else 0.0
    ndcg = compute_ndcg(labels, k=max(k_values))
    return RetrievalResult(
        question=question.question,
        chunks=chunks,
        elapsed_ms=elapsed_ms,
        hits=hit_positions,
        mrr=mrr,
        ndcg=ndcg,
    )


def aggregate_report(
    results: list[RetrievalResult],
    k_values: list[int],
    timestamp: str,
) -> EvalReport:
    """Aggregate per-query results into a summary report."""
    n = len(results)
    hit_rates: dict[int, float] = {}
    mrrs, ndcgs, latencies = [], [], []

    for r in results:
        mrrs.append(r.mrr)
        ndcgs.append(r.ndcg)
        latencies.append(r.elapsed_ms)
        for k in k_values:
            if k not in hit_rates:
                hit_rates[k] = 0.0
            hit_rates[k] += (1.0 if any(h <= k for h in r.hits) else 0.0)

    return EvalReport(
        total=n,
        hit_rate_at_1=hit_rates.get(1, 0.0) / n if n else 0.0,
        hit_rate_at_3=hit_rates.get(3, 0.0) / n if n else 0.0,
        hit_rate_at_5=hit_rates.get(5, 0.0) / n if n else 0.0,
        hit_rate_at_10=hit_rates.get(10, 0.0) / n if n else 0.0,
        mean_mrr=sum(mrrs) / n if n else 0.0,
        mean_ndcg=sum(ndcgs) / n if n else 0.0,
        avg_latency_ms=sum(latencies) / n if n else 0.0,
        total_latency_ms=sum(latencies),
        results=results,
        timestamp=timestamp,
    )


# ─── Retrieval pipeline ───────────────────────────────────────────────────────

async def run_retrieval(query: str, top_k: int = 20) -> tuple[list[dict], int]:
    """Run hybrid search and return (chunks, elapsed_ms)."""
    from app.services.retrieval.query_service import QueryService
    started = time.perf_counter()
    try:
        service = QueryService()
        chunks = await service.hybrid_search(query, top_k=top_k, skip_rerank=False)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return chunks, elapsed_ms
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        print(f"  [ERROR] Retrieval failed: {exc}", file=sys.stderr)
        return [], elapsed_ms


# ─── Dataset loading ────────────────────────────────────────────────────────────

def load_golden_dataset(path: Path) -> list[GoldenQuestion]:
    """Load golden dataset from JSON or JSONL file."""
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    # Try JSON first
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            if "questions" in data and isinstance(data["questions"], list):
                items = data["questions"]
            else:
                items = [data]
        else:
            items = data if isinstance(data, list) else [data]

        return [
            GoldenQuestion(
                question=item["question"],
                expected_source_contains=item.get("expected_sources", item.get("expected_source_contains", "")),
                metadata=item.get("metadata", {}),
            )
            for item in items
        ]
    except json.JSONDecodeError:
        pass

    # Try JSONL
    questions = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
            questions.append(GoldenQuestion(
                question=item["question"],
                expected_source_contains=item.get("expected_sources", item.get("expected_source_contains", "")),
                metadata=item.get("metadata", {}),
            ))
        except json.JSONDecodeError:
            continue
    return questions



# ─── Output ────────────────────────────────────────────────────────────────────

def format_report(report: EvalReport, verbose: bool = False) -> str:
    sep = "=" * 70
    parts = [
        "",
        sep,
        "  HistoriAI Retrieval Evaluation Report",
        f"  {report.timestamp}  |  {report.total} queries",
        sep,
        "",
        "  RETRIEVAL QUALITY",
        f"  {'Metric':<28} {'Value':>12}",
        f"  {'-'*28} {'-'*12}",
        f"  {'Hit Rate @ 1':<28} {report.hit_rate_at_1:>11.1%}",
        f"  {'Hit Rate @ 3':<28} {report.hit_rate_at_3:>11.1%}",
        f"  {'Hit Rate @ 5':<28} {report.hit_rate_at_5:>11.1%}",
        f"  {'Hit Rate @ 10':<28} {report.hit_rate_at_10:>11.1%}",
        f"  {'Mean MRR':<28} {report.mean_mrr:>11.3f}",
        f"  {'Mean NDCG':<28} {report.mean_ndcg:>11.3f}",
        "",
        "  PERFORMANCE",
        f"  {'Metric':<28} {'Value':>12}",
        f"  {'-'*28} {'-'*12}",
        f"  {'Avg latency / query':<28} {report.avg_latency_ms:>10.1f} ms",
        f"  {'Total latency':<28} {report.total_latency_ms:>10.0f} ms",
        "",
        sep,
    ]
    if verbose:
        parts.extend(["", "  PER-QUERY DETAIL", ""])
        for r in report.results:
            parts.append(f"  Q: {r.question[:68]}")
            parts.append(
                f"    MRR={r.mrr:.3f}  NDCG={r.ndcg:.3f}"
                f"  hits={str(r.hits) if r.hits else 'MISS':<12s}  {r.elapsed_ms}ms"
            )
            for idx, chunk in enumerate(r.chunks[:3], 1):
                title = str(chunk.get("document_title", "Unknown"))[:50]
                score = chunk.get("rerank_score", chunk.get("score", 0))
                parts.append(f"    [{idx}] score={score:.3f}  {title}")
            parts.append("")
    parts.append(sep)
    return "\n".join(parts)


def quality_gate(report: EvalReport, min_mrr: float, min_hit5: float) -> bool:
    return report.mean_mrr >= min_mrr and report.hit_rate_at_5 >= min_hit5


# ─── CLI ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="HistoriAI Retrieval Evaluation")
    p.add_argument("--dataset", "-d", type=Path,
                   default=PROJECT_ROOT / "evals" / "golden_dataset.json")
    p.add_argument("--k", "-k", type=int, nargs="+", default=[1, 3, 5, 10],
                   help="k values for Hit Rate (default: 1 3 5 10)")
    p.add_argument("--top-k", type=int, default=20,
                   help="Chunks to retrieve per query (default: 20)")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--output", "-o", type=Path, default=None)
    p.add_argument("--min-mrr", type=float, default=0.3)
    p.add_argument("--min-hit5", type=float, default=0.5)
    p.add_argument("--skip-init", action="store_true",
                   help="Query running API server instead of importing locally")
    p.add_argument("--api-url", default="http://localhost:8000")
    return p.parse_args()


def report_to_dict(report: EvalReport) -> dict:
    return {
        "timestamp": report.timestamp,
        "total": report.total,
        "metrics": {
            f"hit_rate_at_{k}": getattr(report, f"hit_rate_at_{k}")
            for k in [1, 3, 5, 10]
        },
        "mean_mrr": report.mean_mrr,
        "mean_ndcg": report.mean_ndcg,
        "avg_latency_ms": report.avg_latency_ms,
        "per_query": [
            {"question": r.question, "mrr": r.mrr, "ndcg": r.ndcg,
             "hits": r.hits, "elapsed_ms": r.elapsed_ms}
            for r in report.results
        ],
    }


async def run_local(args: argparse.Namespace) -> int:
    dataset_path = args.dataset
    if not dataset_path.exists():
        print(f"[ERROR] Dataset not found: {dataset_path}", file=sys.stderr)
        return 1

    questions = load_golden_dataset(dataset_path)
    if not questions:
        print("[ERROR] No questions found in dataset", file=sys.stderr)
        return 1

    print(f"[INFO] Loaded {len(questions)} questions from {dataset_path}")
    results: list[RetrievalResult] = []

    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q.question[:60]}...", end=" ", flush=True)
        chunks, elapsed = await run_retrieval(q.question, top_k=args.top_k)
        result = evaluate_single(q, chunks, elapsed, args.k)
        results.append(result)
        hit = "HIT" if result.hits else "MISS"
        print(f"{hit}  MRR={result.mrr:.3f}  NDCG={result.ndcg:.3f}  {elapsed}ms")

    report = aggregate_report(results, args.k, datetime.utcnow().isoformat())
    print(format_report(report, verbose=args.verbose))

    passed = quality_gate(report, args.min_mrr, args.min_hit5)
    print("[PASS] Quality gate passed" if passed else
          f"[WARN] Quality gate FAILED (MRR={report.mean_mrr:.3f} < {args.min_mrr} "
          f"or Hit@5={report.hit_rate_at_5:.1%} < {args.min_hit5:.1%})")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report_to_dict(report), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[INFO] Report written to {args.output}")

    return 0 if passed else 2


async def run_remote(args: argparse.Namespace) -> int:
    import httpx

    dataset_path = args.dataset
    if not dataset_path.exists():
        print(f"[ERROR] Dataset not found: {dataset_path}", file=sys.stderr)
        return 1

    questions = load_golden_dataset(dataset_path)
    if not questions:
        print("[ERROR] No questions found in dataset", file=sys.stderr)
        return 1

    print(f"[INFO] Loaded {len(questions)} questions from {dataset_path}")
    print(f"[INFO] Querying API at {args.api_url}")

    results: list[RetrievalResult] = []
    base_url = args.api_url.rstrip("/")

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, q in enumerate(questions, 1):
            print(f"[{i}/{len(questions)}] {q.question[:60]}...", end=" ", flush=True)
            started = time.perf_counter()
            try:
                resp = await client.post(
                    f"{base_url}/api/v1/query",
                    json={"query": q.question, "top_k": args.top_k},
                )
                resp.raise_for_status()
                data = resp.json()
                chunks = data.get("chunks", data.get("results", []))
            except Exception as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                chunks = []
            elapsed = int((time.perf_counter() - started) * 1000)
            result = evaluate_single(q, chunks, elapsed, args.k)
            results.append(result)
            hit = "HIT" if result.hits else "MISS"
            print(f"{hit}  MRR={result.mrr:.3f}  NDCG={result.ndcg:.3f}  {elapsed}ms")

    report = aggregate_report(results, args.k, datetime.utcnow().isoformat())
    print(format_report(report, verbose=args.verbose))

    passed = quality_gate(report, args.min_mrr, args.min_hit5)
    print("[PASS] Quality gate passed" if passed else
          f"[WARN] Quality gate FAILED")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report_to_dict(report), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[INFO] Report written to {args.output}")

    return 0 if passed else 2


def main() -> int:
    args = parse_args()
    return asyncio.run(run_remote(args) if args.skip_init else run_local(args))


if __name__ == "__main__":
    sys.exit(main())
