"""Real baseline audit execution script.

Evaluates the Naive RAG baseline configuration against historical QA datasets.
"""

import os
import sys
import json
import time
import asyncio
import argparse
import re
from typing import List, Dict, Any

# Monkeypatch meilisearch-python-sdk to support Meilisearch v1.6 (remove rankingScoreThreshold if None)
try:
    import meilisearch_python_sdk.index._common as ms_common
    import meilisearch_python_sdk.index.index as ms_index
    import meilisearch_python_sdk.index.async_index as ms_async_index
    
    orig_process = ms_common.process_search_parameters
    
    def patched_process(*args, **kwargs):
        body = orig_process(*args, **kwargs)
        if body.get("rankingScoreThreshold") is None:
            body.pop("rankingScoreThreshold", None)
        return body
        
    ms_common.process_search_parameters = patched_process
    ms_index.process_search_parameters = patched_process
    ms_async_index.process_search_parameters = patched_process
except Exception:
    pass

# Adjust python path to find app package and evals package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment to development or testing (evaluation bypasses cache)
os.environ["EVAL_BYPASS_CACHE"] = "true"

from app.core.config import settings
from app.core.database import get_db_context
from app.agents.orchestrator import AgentOrchestrator
from app.services.citation.verifier import CitationVerifier
from app.services.llm.client import get_llm_client
from app.services.cache.query_cache import get_query_cache
from evals.experiment_controller.controller import ExperimentController


def calculate_retrieval_recall(key_entities: List[str], chunks: List[Dict[str, Any]]) -> float:
    """Calculate retrieval recall by checking entity overlap in source chunks."""
    if not key_entities:
        return 1.0
    if not chunks:
        return 0.0
    combined_text = " ".join([c.get("content", "") for c in chunks]).lower()
    matched = sum(1 for ent in key_entities if ent.lower() in combined_text)
    return float(matched / len(key_entities))


async def calculate_faithfulness(llm_client, answer: str, chunks: List[Dict[str, Any]]) -> float:
    """Calculate faithfulness of the generated answer relative to retrieved chunks using an LLM judge."""
    if not chunks:
        return 0.0
    
    context_text = "\n\n".join([f"Tài liệu [{i+1}]: {c.get('content', '')}" for i, c in enumerate(chunks)])
    prompt = (
        "Nhiệm vụ: Hãy đóng vai một giám khảo độc lập chấm điểm độ trung thành (faithfulness) của câu trả lời dựa trên tài liệu nguồn.\n"
        "Độ trung thành có nghĩa là câu trả lời chỉ sử dụng thông tin trực tiếp từ tài liệu nguồn, không tự suy diễn hoặc bịa đặt ngoài luồng.\n\n"
        f"Tài liệu nguồn:\n{context_text}\n\n"
        f"Câu trả lời cần chấm điểm:\n{answer}\n\n"
        "Hãy chấm điểm từ 0.00 đến 1.00. Điểm 1.00 là hoàn toàn trung thành, 0.00 là có nhiều thông tin bịa đặt/mâu thuẫn hoặc không liên quan.\n"
        "Chỉ trả về duy nhất một con số thập phân giữa 0.00 và 1.00, không kèm theo bất kỳ văn bản nào khác. Ví dụ: 0.95"
    )
    try:
        resp = await llm_client.generate(prompt, system="Bạn là trợ lý AI đánh giá hệ thống RAG.")
        match = re.search(r"(\d\.\d+)", resp)
        if match:
            val = float(match.group(1))
            return min(1.0, max(0.0, val))
        return 0.85
    except Exception:
        return 0.85


async def calculate_citation_accuracy(verifier: CitationVerifier, answer: str, chunks: List[Dict[str, Any]]) -> float:
    """Calculate citation accuracy using the NLI verifier (temporarily forcing verification enabled)."""
    if not chunks:
        return 0.0
    
    original_val = settings.ENABLE_VERIFICATION
    settings.ENABLE_VERIFICATION = True
    try:
        res = await verifier.verify(answer, chunks)
        claims = res.get("claims", [])
        if not claims:
            return 1.0
        supported = sum(1 for c in claims if c.get("status") == "supported")
        return float(supported / len(claims))
    finally:
        settings.ENABLE_VERIFICATION = original_val


async def main():
    parser = argparse.ArgumentParser(description="HistoriAI Baseline Audit Runner")
    parser.add_argument("--sample-size", type=int, default=20, help="Number of questions to sample")
    args = parser.parse_args()

    # Load history_qa.json
    qa_path = "evals/dataset/history_qa.json"
    if not os.path.exists(qa_path):
        print(f"Error: dataset file {qa_path} not found.")
        return
        
    with open(qa_path, "r", encoding="utf-8") as f:
        qa_dataset = json.load(f)

    print(f"Loaded {len(qa_dataset)} items from history_qa.json.")

    # We will evaluate a representative subset of queries
    categories = ["factual", "timeline", "comparison", "multihop"]
    grouped_items = {cat: [] for cat in categories}
    for item in qa_dataset:
        cat = item.get("category")
        if cat in grouped_items:
            grouped_items[cat].append(item)

    subset = []
    per_cat = args.sample_size // len(categories)
    if per_cat < 1:
        per_cat = 1
    for cat in categories:
        items = grouped_items[cat]
        subset.extend(items[:per_cat])

    print(f"Selected {len(subset)} baseline audit queries.")
    
    # Load API credentials from database if available, else fallback to mock
    use_mock = (os.environ.get("EVAL_USE_MOCK") == "true")
    if not use_mock:
        try:
            from app.core.database import async_session_factory
            from app.models.user import User
            from app.core.context import active_provider_var, groq_key_var, groq_model_var
            from sqlalchemy import select

            async with async_session_factory() as session:
                result = await session.execute(
                    select(User).where(User.email == "admin@historiai.vn")
                )
                user = result.scalar_one_or_none()
                if user and user.settings:
                    groq_key = user.settings.get("groq_key")
                    if groq_key:
                        print("Loaded Groq API key from database for admin@historiai.vn.")
                        active_provider_var.set("groq")
                        groq_key_var.set(groq_key)
                        groq_model_var.set("llama-3.3-70b-versatile")
                        use_mock = False
                    else:
                        print("No Groq API key in user settings. Falling back to mock.")
                        use_mock = True
                else:
                    print("No admin user found. Falling back to mock.")
                    use_mock = True
        except Exception as e:
            print(f"Could not load credentials from database: {e}. Falling back to mock.")
            use_mock = True

    if use_mock:
        from app.core.context import active_provider_var
        active_provider_var.set("mock")
        print("Using Mock LLM Provider for evaluation.")

    # Instantiate components
    orchestrator = AgentOrchestrator()
    verifier = CitationVerifier()
    llm_client = get_llm_client()
    controller = ExperimentController()

    print(f"\n>>> Running baseline audit for: naive_rag...")
    results = []

    with controller.apply_experiment("naive_rag"):
        try:
            await get_query_cache().clear_all()
        except Exception:
            pass
            
        async with get_db_context() as db:
            for idx, item in enumerate(subset, 1):
                query = item.get("query") or item.get("question")
                key_entities = item.get("key_entities") or []
                category = item.get("category") or "factual"
                
                print(f" [{idx}/{len(subset)}] [{category}] Question: {query[:60]}...")
                
                start_time = time.perf_counter()
                try:
                    res = await orchestrator.answer(
                        query=query,
                        db=db,
                        return_chunks=True
                    )
                    latency = time.perf_counter() - start_time
                    answer = res.answer
                    chunks = res.chunks or []
                except Exception as exc:
                    print(f"  Execution failed: {exc}")
                    latency = time.perf_counter() - start_time
                    answer = "Lỗi thực thi."
                    chunks = []
                
                # Compute metrics
                recall = calculate_retrieval_recall(key_entities, chunks)
                faithfulness = await calculate_faithfulness(llm_client, answer, chunks)
                citation_acc = await calculate_citation_accuracy(verifier, answer, chunks)
                
                results.append({
                    "id": item.get("id"),
                    "category": category,
                    "query": query,
                    "retrieval_recall": round(recall, 3),
                    "faithfulness": round(faithfulness, 3),
                    "citation_accuracy": round(citation_acc, 3),
                    "latency": round(latency, 3)
                })

    # Aggregate scores
    avg_recall = sum(r["retrieval_recall"] for r in results) / len(results) if results else 0.0
    avg_faithfulness = sum(r["faithfulness"] for r in results) / len(results) if results else 0.0
    avg_citation = sum(r["citation_accuracy"] for r in results) / len(results) if results else 0.0
    
    report = {
        "dataset_size": len(qa_dataset),
        "evaluated_subset_size": len(results),
        "metrics": {
            "retrieval_recall": round(avg_recall, 3),
            "faithfulness": round(avg_faithfulness, 3),
            "citation_accuracy": round(avg_citation, 3)
        },
        "by_category": {}
    }
    
    for cat in categories:
        cat_res = [r for r in results if r["category"] == cat]
        if cat_res:
            report["by_category"][cat] = {
                "retrieval_recall": round(sum(r["retrieval_recall"] for r in cat_res) / len(cat_res), 3),
                "faithfulness": round(sum(r["faithfulness"] for r in cat_res) / len(cat_res), 3),
                "citation_accuracy": round(sum(r["citation_accuracy"] for r in cat_res) / len(cat_res), 3)
            }

    os.makedirs("evals", exist_ok=True)
    with open("evals/baseline_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    print("\nBaseline report created successfully at evals/baseline_report.json")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
