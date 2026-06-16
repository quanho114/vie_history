#!/usr/bin/env python3
"""
Latency and TTFB (Time-To-First-Token) Benchmarking for HistoriAI.

Sends streaming queries to the backend and measures exact response timings.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT / "apps" / "api"))

# Generate bypass authorization headers
HEADERS = {}
try:
    from app.core.security import create_access_token
    auth_token = create_access_token(
        user_id="00000000-0000-0000-0000-000000000000",
        email="admin@historiai.vn",
        role="admin"
    )
    HEADERS = {"Authorization": f"Bearer {auth_token}"}
except Exception as exc:
    print(f"Warning: could not generate bypass auth token: {exc}")

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:12701")
QUERIES = [
    "Diễn biến chính của Cách mạng tháng Tám 1945 là gì?",
    "Ý nghĩa lịch sử của chiến dịch Điện Biên Phủ năm 1954 là gì?",
    "Những điều khoản chính của Hiệp định Paris 1973 là gì?"
]


async def benchmark_query(query: str, idx: int) -> dict:
    """Benchmark a single query's TTFB and Total Latency."""
    print(f"[{idx}] Querying: '{query}'")
    
    url = f"{API_BASE}/api/v1/query/stream"
    payload = {"query": query, "stream": True}
    
    start_time = time.monotonic()
    ttfb = None
    total_latency = None
    char_count = 0
    chunks_received = 0
    first_token_text = ""
    full_answer = []

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                url,
                json=payload,
                headers=HEADERS,
            ) as stream:
                # Connected to stream
                async for line in stream.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line.removeprefix("data: ").strip()
                        if data_str and data_str != "[DONE]":
                            try:
                                data = json.loads(data_str)
                                chunks_received += 1
                                
                                # Check if it's actual text content
                                if data.get("type") == "token":
                                    content = data.get("token", "")
                                    full_answer.append(content)
                                    char_count += len(content)
                                    
                                    # If this is the first token, record TTFB
                                    if ttfb is None and len(content.strip()) > 0:
                                        ttfb = time.monotonic() - start_time
                                        first_token_text = content.strip()
                                        print(f"  → TTFB: {ttfb:.3f}s (token: '{first_token_text}')")
                            except json.JSONDecodeError:
                                pass
                
                total_latency = time.monotonic() - start_time
                print(f"  → Total Latency: {total_latency:.3f}s (chars: {char_count}, chunks: {chunks_received})")
                
                return {
                    "query": query,
                    "success": True,
                    "ttfb_seconds": round(ttfb, 4) if ttfb else None,
                    "total_latency_seconds": round(total_latency, 4),
                    "char_count": char_count,
                    "chunks_count": chunks_received,
                    "speed_chars_per_sec": round(char_count / total_latency, 2) if total_latency else 0
                }
    except Exception as exc:
        print(f"  ❌ Query failed: {exc}")
        return {
            "query": query,
            "success": False,
            "error": str(exc)
        }


async def main():
    print("=" * 60)
    print("HistoriAI Latency & TTFB Benchmarking")
    print("=" * 60)
    print(f"Target API: {API_BASE}")
    print(f"Queries count: {len(QUERIES)}")
    print("-" * 60)

    results = []
    for idx, q in enumerate(QUERIES, 1):
        res = await benchmark_query(q, idx)
        results.append(res)
        await asyncio.sleep(1.0)  # cooling time between requests

    # Calculate aggregate metrics
    successful = [r for r in results if r.get("success")]
    ttfbs = [r["ttfb_seconds"] for r in successful if r.get("ttfb_seconds") is not None]
    latencies = [r["total_latency_seconds"] for r in successful]

    avg_ttfb = sum(ttfbs) / len(ttfbs) if ttfbs else 0.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    print("\n" + "=" * 60)
    print("BENCHMARK REPORT SUMMARY")
    print("=" * 60)
    print(f"Successful Queries:  {len(successful)} / {len(results)}")
    print(f"Average TTFB:        {avg_ttfb:.3f}s (Target: < 0.800s)")
    print(f"Average Total Time:  {avg_latency:.3f}s")
    
    status = "✅ OPTIMIZED" if avg_ttfb < 0.800 else "⚠️ DEGRADED"
    print(f"TTFB Health Status:   {status}")
    print("=" * 60)

    # Save benchmark report
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_api": API_BASE,
        "average_ttfb_seconds": round(avg_ttfb, 4),
        "average_total_latency_seconds": round(avg_latency, 4),
        "status": status,
        "details": results
    }

    report_path = ROOT / "evals" / "latency_benchmark.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Benchmark results saved to {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
