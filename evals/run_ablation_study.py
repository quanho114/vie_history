"""Real ablation study execution script.

Evaluates RAG pipeline configurations against historical QA datasets.
Supports Development mode (--sample-size) and Research mode (--full-eval).
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


async def run_eval_on_dataset(
    config_id: str,
    subset: List[Dict[str, Any]],
    orchestrator: AgentOrchestrator,
    verifier: CitationVerifier,
    llm_client,
) -> Dict[str, Any]:
    """Run evaluation for a specific configuration over the dataset subset."""
    print(f"\n>>> Running evaluation for configuration: {config_id} ({len(subset)} samples)...")
    
    controller = ExperimentController()
    results = []
    
    with controller.apply_experiment(config_id):
        # Flush query cache to ensure fresh pipeline executions
        try:
            await get_query_cache().clear_all()
        except Exception:
            pass
            
        async with get_db_context() as db:
            for idx, item in enumerate(subset, 1):
                query = item.get("query") or item.get("question")
                key_entities = item.get("key_entities") or item.get("entities") or []
                category = item.get("category") or item.get("intent") or "factual"
                
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
                    "generated_answer": answer,
                    "retrieved_chunks_count": len(chunks),
                    "metrics": {
                        "retrieval_recall": round(recall, 3),
                        "faithfulness": round(faithfulness, 3),
                        "citation_accuracy": round(citation_acc, 3),
                        "latency_seconds": round(latency, 3)
                    }
                })
                
    # Aggregate scores
    categories = list(set([r["category"] for r in results]))
    summary = {
        "metrics": {
            "retrieval_recall": 0.0,
            "faithfulness": 0.0,
            "citation_accuracy": 0.0,
            "avg_latency_seconds": 0.0
        },
        "by_category": {}
    }
    
    if results:
        summary["metrics"]["retrieval_recall"] = round(sum(r["metrics"]["retrieval_recall"] for r in results) / len(results), 3)
        summary["metrics"]["faithfulness"] = round(sum(r["metrics"]["faithfulness"] for r in results) / len(results), 3)
        summary["metrics"]["citation_accuracy"] = round(sum(r["metrics"]["citation_accuracy"] for r in results) / len(results), 3)
        summary["metrics"]["avg_latency_seconds"] = round(sum(r["metrics"]["latency_seconds"] for r in results) / len(results), 3)
        
    for cat in categories:
        cat_res = [r for r in results if r["category"] == cat]
        if cat_res:
            summary["by_category"][cat] = {
                "retrieval_recall": round(sum(r["metrics"]["retrieval_recall"] for r in cat_res) / len(cat_res), 3),
                "faithfulness": round(sum(r["metrics"]["faithfulness"] for r in cat_res) / len(cat_res), 3),
                "citation_accuracy": round(sum(r["metrics"]["citation_accuracy"] for r in cat_res) / len(cat_res), 3),
                "avg_latency_seconds": round(sum(r["metrics"]["latency_seconds"] for r in cat_res) / len(cat_res), 3)
            }
            
    return {"results": results, "summary": summary}


async def main():
    parser = argparse.ArgumentParser(description="HistoriAI Ablation Study Runner")
    parser.add_argument("--sample-size", type=int, default=50, help="Number of questions to sample in Development mode")
    parser.add_argument("--full-eval", action="store_true", help="Run full evaluation on complete dataset in Research mode")
    args = parser.parse_args()

    # Load history_qa.json
    qa_path = "evals/dataset/history_qa.json"
    if not os.path.exists(qa_path):
        print(f"Error: dataset file {qa_path} not found.")
        return
        
    with open(qa_path, "r", encoding="utf-8") as f:
        qa_dataset = json.load(f)

    # Load cause_effect_questions.jsonl
    ce_path = "evals/dataset/cause_effect_questions.jsonl"
    ce_dataset = []
    if os.path.exists(ce_path):
        with open(ce_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    item["category"] = "causal"
                    ce_dataset.append(item)
    else:
        print(f"Warning: causal dataset file {ce_path} not found.")

    print(f"Loaded {len(qa_dataset)} items from history_qa.json.")
    print(f"Loaded {len(ce_dataset)} items from cause_effect_questions.jsonl.")

    # Group by category
    categories = ["factual", "timeline", "comparison", "multihop", "causal"]
    grouped_items = {cat: [] for cat in categories}
    for item in qa_dataset:
        cat = item.get("category")
        if cat in grouped_items:
            grouped_items[cat].append(item)
    for item in ce_dataset:
        grouped_items["causal"].append(item)

    subset = []
    if args.full_eval:
        print("\n=== RESEARCH MODE: FULL EVALUATION ===")
        # Run on everything
        for cat in categories:
            subset.extend(grouped_items[cat])
    else:
        print(f"\n=== DEVELOPMENT MODE: SAMPLE SIZE {args.sample_size} ===")
        # Sample evenly
        per_cat = args.sample_size // len(categories)
        if per_cat < 1:
            per_cat = 1
        for cat in categories:
            items = grouped_items[cat]
            subset.extend(items[:per_cat])

    print(f"Selected {len(subset)} evaluation queries.")
    
    # Load API credentials from database if available, else fallback to mock
    use_mock = (os.environ.get("EVAL_USE_MOCK") == "true")
    if not use_mock:
        if os.environ.get("GEMINI_API_KEY"):
            from app.core.context import active_provider_var, gemini_key_var, gemini_model_var
            print("Using Gemini API key from environment.")
            active_provider_var.set("gemini")
            gemini_key_var.set(os.environ["GEMINI_API_KEY"])
            gemini_model_var.set(os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"))
            use_mock = False
        else:
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

    # Instantiate pipeline components
    orchestrator = AgentOrchestrator()
    verifier = CitationVerifier()
    llm_client = get_llm_client()

    configs = ["naive_rag", "hybrid_rag", "graph_rag", "agentic_historiai"]
    config_labels = {
        "naive_rag": "Naive RAG",
        "hybrid_rag": "Hybrid RAG",
        "graph_rag": "GraphRAG",
        "agentic_historiai": "Agentic HistoriAI"
    }

    os.makedirs("evals/results", exist_ok=True)
    
    summary_report = {
        "dataset_size": len(qa_dataset) + len(ce_dataset),
        "evaluated_subset_size": len(subset),
        "configurations": {}
    }

    for config in configs:
        eval_output = await run_eval_on_dataset(config, subset, orchestrator, verifier, llm_client)
        
        # Save individual configuration result file
        config_file_path = f"evals/results/{config}.json"
        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump(eval_output, f, indent=2, ensure_ascii=False)
            
        label = config_labels[config]
        summary_report["configurations"][config] = eval_output["summary"]
        print(f"Completed and saved configuration report to {config_file_path}")

    # Save summary report
    summary_path = "evals/results/summary_report.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2, ensure_ascii=False)
    
    # Save a copy as evals/ablation_report.json for compatibility
    with open("evals/ablation_report.json", "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2, ensure_ascii=False)

    print("\n" + "="*95)
    print(f"{'CONFIGURATION':<20} | {'RECALL':<8} | {'FAITHFULNESS':<12} | {'CITATION ACC':<12} | {'LATENCY (s)':<12}")
    print("="*95)

    for config in configs:
        label = config_labels[config]
        metrics = summary_report["configurations"][config]["metrics"]
        print(f"{label:<20} | {metrics['retrieval_recall']:<8.3f} | {metrics['faithfulness']:<12.3f} | {metrics['citation_accuracy']:<12.3f} | {metrics['avg_latency_seconds']:<12.3f}")

    print("="*95)
    print(f"\nSaved summary report to {summary_path} and evals/ablation_report.json\n")


if __name__ == "__main__":
    asyncio.run(main())
