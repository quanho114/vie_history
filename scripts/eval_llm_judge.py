#!/usr/bin/env python3
"""
LLM-as-Judge evaluation for HistoriAI Agent answer quality.

Uses an LLM to judge:
  1. Faithfulness — does the answer match the retrieved evidence?
  2. Answer relevance — does the answer address the question?
  3. Citation accuracy — are the citations grounded in the evidence?

This complements the retrieval eval (which measures recall/MRR) with
generation-level quality assessment.

Usage:
    python scripts/eval_llm_judge.py

    python scripts/eval_llm_judge.py --golden-dataset evals/golden_dataset.json --verbose

    python scripts/eval_llm_judge.py --api-url http://localhost:12701 --verbose
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))


# ─── Judge prompts ────────────────────────────────────────────────────────────────

FAITHFULNESS_PROMPT = """Bạn là một chuyên gia kiểm tra chất lượng về lịch sử Việt Nam.
Nhiệm vụ: Đánh giá mức độ trung thực (faithfulness) của câu trả lời dựa trên bằng chứng được cung cấp.

**Câu hỏi gốc:** {question}
**Câu trả lời cần đánh giá:** {answer}
**Bằng chứng từ tài liệu:** {evidence}

Đánh giá TRUNG THỰC:
- Trung thực (faithful) = mọi claim trong câu trả lời đều có trong bằng chứng
- Không trung thực (unfaithful) = có claim không có trong bằng chứng hoặc mâu thuẫn với bằng chứng
- Không thể đánh giá = bằng chứng quá ít để kết luận

Hãy trả lời theo format JSON:
{{
  "score": 1-5,  // 1=hoàn toàn không trung thực, 5=hoàn toàn trung thực
  "reasoning": "giải thích ngắn gọn",
  "issues": ["danh sách các claim không có trong bằng chứng"]  // rỗng nếu không có
}}
"""

RELEVANCE_PROMPT = """Bạn là một chuyên gia kiểm tra chất lượng về lịch sử Việt Nam.
Nhiệm vụ: Đánh giá mức độ liên quan (relevance) của câu trả lời với câu hỏi.

**Câu hỏi gốc:** {question}
**Câu trả lời cần đánh giá:** {answer}

Đánh giá LIÊN QUAN:
- 5 (hoàn toàn liên quan) = câu trả lời trực tiếp và đầy đủ trả lời câu hỏi
- 4 (liên quan) = câu trả lời đúng trọng tâm, có thể thiếu chi tiết
- 3 (trung bình) = câu trả lời đề cập chủ đề nhưng không đầy đủ
- 2 (ít liên quan) = câu trả lời lạc đề
- 1 (không liên quan) = câu trả lời hoàn toàn không đúng câu hỏi

Hãy trả lời theo format JSON:
{{
  "score": 1-5,
  "reasoning": "giải thích ngắn gọn"
}}
"""

CITATION_PROMPT = """Bạn là một chuyên gia kiểm tra chất lượng về lịch sử Việt Nam.
Nhiệm vụ: Đánh giá độ chính xác của trích dẫn (citations).

**Câu hỏi gốc:** {question}
**Câu trả lời:** {answer}
**Bằng chứng:** {evidence}

Đánh giá CITATIONS:
- Tất cả citations phải tham chiếu đến thông tin CÓ TRONG bằng chứng
- Nếu câu trả lời không có citations: kiểm tra xem nó có hallucinate không

Hãy trả lời theo format JSON:
{{
  "score": 1-5,  // 5=tất cả citations chính xác, 1=nhiều citations sai
  "reasoning": "giải thích",
  "citation_issues": ["citation sai hoặc không tìm thấy trong bằng chứng"]
}}
"""


# ─── Data structures ─────────────────────────────────────────────────────────────

@dataclass
class JudgeResult:
    faithfulness_score: float
    relevance_score: float
    citation_score: float
    overall_score: float
    reasoning: dict
    latency_ms: int


@dataclass
class LLMJudgeReport:
    total: int
    avg_faithfulness: float
    avg_relevance: float
    avg_citation: float
    avg_overall: float
    pass_count: int
    results: list[JudgeResult]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── LLM Client ────────────────────────────────────────────────────────────────

def _build_judge_prompt(system: str, question: str, answer: str, evidence: str) -> str:
    return system.format(question=question, answer=answer, evidence=evidence)


async def _call_llm(
    prompt: str,
    model: str,
    api_key: str,
    api_url: str | None = None,
) -> str:
    """Call LLM API (OpenAI-compatible) with the judge prompt."""
    import httpx

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 512,
    }
    url = (api_url.rstrip("/") if api_url else "https://api.openai.com/v1") + "/chat/completions"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def _parse_judge_response(content: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    text = content.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"score": 0, "reasoning": f"Parse error: {content[:200]}", "issues": []}


# ─── Judge pipeline ────────────────────────────────────────────────────────────

async def judge_single(
    question: str,
    answer: str,
    evidence_chunks: list[dict],
    model: str,
    api_key: str,
    api_url: str | None = None,
) -> JudgeResult:
    """Judge a single answer with all three criteria."""
    started = time.perf_counter()

    evidence = "\n\n".join(
        f"[{i+1}] {c.get('document_title', 'N/A')} | {c.get('section_title', '')}:\n{c.get('content', '')[:500]}"
        for i, c in enumerate(evidence_chunks[:5])
    ) or "Không có bằng chứng được truy xuất."

    # Run all three judges in parallel
    faithfulness_p = _call_llm(
        _build_judge_prompt(FAITHFULNESS_PROMPT, question, answer, evidence),
        model, api_key, api_url,
    )
    relevance_p = _call_llm(
        _build_judge_prompt(RELEVANCE_PROMPT, question, answer, evidence),
        model, api_key, api_url,
    )
    citation_p = _call_llm(
        _build_judge_prompt(CITATION_PROMPT, question, answer, evidence),
        model, api_key, api_url,
    )

    faithfulness_r, relevance_r, citation_r = await asyncio.gather(
        faithfulness_p, relevance_p, citation_p
    )

    faithful = _parse_judge_response(faithfulness_r)
    relevant = _parse_judge_response(relevance_r)
    citation = _parse_judge_response(citation_r)

    latency_ms = int((time.perf_counter() - started) * 1000)
    overall = (faithful.get("score", 0) + relevant.get("score", 0) + citation.get("score", 0)) / 3

    return JudgeResult(
        faithfulness_score=faithful.get("score", 0) / 5,
        relevance_score=relevant.get("score", 0) / 5,
        citation_score=citation.get("score", 0) / 5,
        overall_score=overall / 5,
        reasoning={"faithfulness": faithful, "relevance": relevant, "citations": citation},
        latency_ms=latency_ms,
    )


# ─── Full evaluation ────────────────────────────────────────────────────────────

async def evaluate_llm_judge(
    questions: list[dict],
    model: str,
    api_key: str,
    api_url: str | None = None,
    top_k: int = 5,
) -> LLMJudgeReport:
    """Run full LLM-as-judge evaluation across all questions."""
    results: list[JudgeResult] = []

    for item in questions:
        question = item["question"]
        answer = item.get("expected_answer", "[no reference answer — will retrieve from system]")
        chunks = item.get("evidence", [])

        # Retrieve evidence if not provided
        if not chunks:
            try:
                from app.services.retrieval.query_service import QueryService
                qs = QueryService()
                chunks = await qs.hybrid_search(question, top_k=top_k)
            except Exception:
                chunks = []

        result = await judge_single(
            question=question,
            answer=answer,
            evidence_chunks=chunks,
            model=model,
            api_key=api_key,
            api_url=api_url,
        )
        results.append(result)

    n = len(results)
    return LLMJudgeReport(
        total=n,
        avg_faithfulness=sum(r.faithfulness_score for r in results) / n if n else 0,
        avg_relevance=sum(r.relevance_score for r in results) / n if n else 0,
        avg_citation=sum(r.citation_score for r in results) / n if n else 0,
        avg_overall=sum(r.overall_score for r in results) / n if n else 0,
        pass_count=sum(1 for r in results if r.overall_score >= 0.7),
        results=results,
    )


# ─── Output ────────────────────────────────────────────────────────────────────

def format_judge_report(report: LLMJudgeReport, verbose: bool = False) -> str:
    sep = "=" * 70
    parts = [
        "",
        sep,
        "  HistoriAI LLM-as-Judge Evaluation Report",
        f"  {report.timestamp}  |  {report.total} questions",
        sep,
        "",
        "  ANSWER QUALITY",
        f"  {'Metric':<28} {'Score':>12}  {'Threshold':>12}",
        f"  {'-'*28} {'-'*12}  {'-'*12}",
        f"  {'Avg Faithfulness':<28} {report.avg_faithfulness:>11.1%}  {'≥ 0.85':>12s}",
        f"  {'Avg Relevance':<28} {report.avg_relevance:>11.1%}  {'≥ 0.80':>12s}",
        f"  {'Avg Citation Accuracy':<28} {report.avg_citation:>11.1%}  {'≥ 0.85':>12s}",
        f"  {'Avg Overall':<28} {report.avg_overall:>11.1%}  {'≥ 0.70':>12s}",
        "",
        f"  Passed (overall ≥ 0.70): {report.pass_count}/{report.total} ({report.pass_count/report.total:.0%})",
        "",
        sep,
    ]
    if verbose:
        parts.extend(["", "  PER-QUESTION DETAIL", ""])
        for i, r in enumerate(report.results, 1):
            parts.append(
                f"  Q{i}: Overall={r.overall_score:.1%}  "
                f"Faithful={r.faithfulness_score:.1%}  "
                f"Relevance={r.relevance_score:.1%}  "
                f"Citation={r.citation_score:.1%}"
            )
            for key, val in r.reasoning.items():
                score = val.get("score", 0)
                reasoning = str(val.get("reasoning", ""))[:80]
                parts.append(f"    [{key}] score={score} — {reasoning}")
            parts.append("")
    parts.append(sep)
    return "\n".join(parts)


def judge_quality_gate(report: LLMJudgeReport) -> bool:
    return (
        report.avg_faithfulness >= 0.85
        and report.avg_relevance >= 0.70
        and report.avg_overall >= 0.70
    )


# ─── CLI ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="HistoriAI LLM-as-Judge Evaluation")
    p.add_argument("--golden-dataset", "-d", type=Path,
                   default=PROJECT_ROOT / "evals" / "golden_dataset.json")
    p.add_argument("--model", "-m", default="gpt-4o-mini")
    p.add_argument("--api-key", "-k", default=None)
    p.add_argument("--api-url", type=str, default=None,
                   help="OpenAI-compatible API base URL (optional)")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--output", "-o", type=Path, default=None)
    return p.parse_args()


def load_questions(path: Path) -> list[dict]:
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []
    try:
        data = json.loads(content)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        return []


async def main() -> int:
    args = parse_args()

    if not args.api_key:
        import os
        args.api_key = os.environ.get("OPENAI_API_KEY")
        if not args.api_key:
            print("[ERROR] --api-key required or OPENAI_API_KEY env var", file=sys.stderr)
            return 1

    if not args.golden_dataset.exists():
        print(f"[ERROR] Dataset not found: {args.golden_dataset}", file=sys.stderr)
        return 1

    questions = load_questions(args.golden_dataset)
    if not questions:
        print("[ERROR] No questions found in dataset", file=sys.stderr)
        return 1

    print(f"[INFO] Loaded {len(questions)} questions")
    print(f"[INFO] Using model: {args.model}")

    report = await evaluate_llm_judge(
        questions=questions,
        model=args.model,
        api_key=args.api_key,
        api_url=args.api_url,
    )

    print(format_judge_report(report, verbose=args.verbose))

    passed = judge_quality_gate(report)
    print(
        "[PASS] Quality gate passed" if passed else
        f"[WARN] Quality gate FAILED — faithfulness={report.avg_faithfulness:.1%} "
        f"(target ≥85%), overall={report.avg_overall:.1%} (target ≥70%)"
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        report_dict = {
            "timestamp": report.timestamp,
            "total": report.total,
            "metrics": {
                "avg_faithfulness": report.avg_faithfulness,
                "avg_relevance": report.avg_relevance,
                "avg_citation": report.avg_citation,
                "avg_overall": report.avg_overall,
                "pass_count": report.pass_count,
            },
            "per_question": [
                {
                    "question": q.question,
                    "overall_score": r.overall_score,
                    "faithfulness": r.faithfulness_score,
                    "relevance": r.relevance_score,
                    "citation": r.citation_score,
                    "latency_ms": r.latency_ms,
                }
                for q, r in zip(questions, report.results)
            ],
        }
        args.output.write_text(json.dumps(report_dict, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[INFO] Report written to {args.output}")

    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
