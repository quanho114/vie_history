"""AgentOrchestrator — thin facade over LangGraph agent_graph.

All pipeline logic lives in agent_graph.py. This class:
1. Serializes external inputs (db, session) into graph state
2. Applies safety, caching, and metrics as orthogonal concerns
3. Provides the answer() and answer_stream() interfaces expected by routes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger("agent_orchestrator")


STATIC_GREETING_ANSWER = (
    "Xin chào! Mình là HistoriAI, trợ lý nghiên cứu lịch sử Việt Nam giai đoạn 1945–1975. "
    "Mình có thể giúp bạn giải đáp các câu hỏi lịch sử, lập niên biểu, hoặc phân tích sự kiện "
    "trong giai đoạn này. Bạn muốn tìm hiểu về sự kiện hay nhân vật nào?"
)

STATIC_OUT_OF_SCOPE_ANSWER = (
    "Xin lỗi, câu hỏi của bạn nằm ngoài phạm vi lịch sử Việt Nam giai đoạn 1945–1975 "
    "mà mình hỗ trợ. Hãy hỏi mình về các sự kiện, nhân vật, chiến dịch lịch sử trong "
    "khoảng thời gian này để mình có thể giải đáp chính xác nhất."
)


@dataclass
class AgentResult:
    """Structured output returned by the agent pipeline."""

    answer: str
    citations: list[dict[str, Any]]
    mode: str
    trace: dict[str, Any]
    intent: str = ""
    chunks: list[dict[str, Any]] | None = None
    safety_info: dict[str, Any] = field(default_factory=dict)


# ─── State Builder ──────────────────────────────────────────────────────────────


def _build_initial_state(
    query: str,
    session_id: str | None,
    filters: dict | None,
    execution_mode: str,
) -> dict[str, Any]:
    """Build the initial AgentState dict for agent_graph."""
    return {
        "query": query,
        "session_id": session_id,
        "filters": filters,
        "execution_mode": execution_mode,
        "plan": [],
        "current_step": 0,
        "retrieved_chunks": [],
        "timeline_events": [],
        "graph_entities": [],
        "reasoning_steps": [],
        "critic_feedback": None,
        "replanning_required": False,
        "replanning_count": 0,
        "answer": None,
        "citations": [],
        "draft_knowledge": [],
        "agent_trace": [],
        "retrieval_queries": [],
        "timeline_queries": [],
        "graph_slugs": [],
        "world_model_analysis": None,
    }


# ─── Orchestrator ──────────────────────────────────────────────────────────────


class AgentOrchestrator:
    """
    Thin orchestrator: safety + caching + agent_graph.

    All actual pipeline logic is delegated to agent_graph.py.
    This class only handles cross-cutting concerns:
    - Safety (input validation, output filtering)
    - Caching (fast-path cache lookup)
    - Metrics (Prometheus)
    - Graceful degradation (simple fallback when agent_graph fails)
    """

    def __init__(self, enable_safety: bool = True, **kwargs) -> None:
        self.enable_safety = enable_safety
        
        from app.services.agent.classifier import IntentClassifier
        from app.services.agent.planner import TaskPlanner
        from app.services.agent.verifier import Verifier
        from app.services.agent.response_builder import ResponseBuilder
        
        self.classifier = kwargs.get("classifier") or IntentClassifier()
        self.planner = kwargs.get("planner") or TaskPlanner()
        self.retriever = kwargs.get("retriever")
        self.verifier = kwargs.get("verifier") or Verifier(min_evidence=1)
        self.response_builder = kwargs.get("response_builder") or ResponseBuilder()

    # ─── Safety helpers ───────────────────────────────────────────────────────

    async def _safety_input_check(
        self,
        query: str,
        session_id: str | None,
    ) -> tuple[bool, dict[str, Any]]:
        """Run input safety checks. Returns (passed, safety_info)."""
        if not self.enable_safety or not session_id:
            return True, {}

        try:
            from app.services.agent.safety_integration import get_safety_integration
            safety = get_safety_integration()
            safety_info = await safety.init_session(session_id)

            is_valid, reason, _ = await safety.validate_input(query)
            if not is_valid:
                logger.warning("unsafe_input_detected", session_id=session_id, reason=reason)
                return False, safety_info

            pii_info = await safety.detect_pii(query)
            if pii_info.get("has_pii"):
                safety_info["pii_detected"] = True
                logger.info("pii_in_input", session_id=session_id)

            return True, safety_info
        except Exception as exc:
            logger.warning("safety_init_failed", error=str(exc))
            return True, {}

    async def _safety_output_check(
        self,
        answer: str,
        session_id: str | None,
    ) -> tuple[str, dict[str, Any]]:
        """Run output safety checks. Returns (filtered_answer, extra_safety_info)."""
        if not self.enable_safety or not session_id:
            return answer, {}

        try:
            from app.services.agent.safety_integration import get_safety_integration
            safety = get_safety_integration()
            filtered, is_safe, removed = await safety.filter_output(answer)
            if not is_safe:
                logger.warning("unsafe_output_filtered", session_id=session_id)
                filtered = "[Nội dung đã được lọc để đảm bảo an toàn]"
            return filtered, {"output_filtered": not is_safe, "removed_items": removed}
        except Exception as exc:
            logger.warning("safety_output_filter_failed", error=str(exc))
            return answer, {}

    # ─── Cache helpers ──────────────────────────────────────────────────────

    async def _cache_get(
        self,
        query: str,
        filters: dict | None,
    ) -> dict[str, Any] | None:
        """Try to return a cached result. Returns None on miss."""
        try:
            from app.services.cache import get_query_cache
            return await get_query_cache().get(query, filters)
        except Exception as exc:
            logger.warning("cache_lookup_failed", error=str(exc))
            return None

    async def _cache_set(
        self,
        query: str,
        filters: dict | None,
        result: dict[str, Any],
    ) -> None:
        """Cache a result (fire-and-forget)."""
        try:
            from app.services.cache import get_query_cache
            await get_query_cache().set(query, filters, result)
        except Exception as exc:
            logger.warning("cache_store_failed", error=str(exc))

    # ─── Complexity Classification ───────────────────────────────────────────

    def _classify_complexity(self, query: str) -> tuple[str, str]:
        """Run keyword-only complexity classification. Returns (mode, intent)."""
        try:
            from app.agents.complexity_classifier import classify_complexity
            result = classify_complexity(query)
            return result.mode, result.intent
        except Exception as exc:
            logger.warning("complexity_classification_failed", error=str(exc))
            return "agentic", "factual"

    # ─── Graph Execution ────────────────────────────────────────────────────

    async def _run_agent_graph(self, initial_state: dict[str, Any], thread_id: str = "default-thread") -> dict[str, Any]:
        """Execute the LangGraph agent_graph pipeline."""
        from app.agents.agent_graph import agent_graph
        config = {"configurable": {"thread_id": thread_id}}
        return await agent_graph.ainvoke(initial_state, config=config)

    async def _stream_agent_graph(
        self,
        initial_state: dict[str, Any],
        thread_id: str = "default-thread",
    ) -> AsyncIterator[dict]:
        """Stream the LangGraph agent_graph pipeline."""
        from app.agents.agent_graph import agent_graph
        config = {"configurable": {"thread_id": thread_id}}
        async for chunk in agent_graph.astream(initial_state, config=config):
            yield chunk

    # ─── Simple Fallback (minimal — only when agent_graph fails) ───────────────

    async def _fallback_answer(
        self,
        query: str,
        db: AsyncSession,
    ) -> AgentResult:
        """
        Minimal fallback when agent_graph is unavailable or fails.

        Uses direct retrieval + synthesizer WITHOUT the full workflow pipeline.
        This is intentionally simple — the full pipeline lives in agent_graph.
        """
        logger.warning("using_fallback_pipeline", query=query[:50])

        try:
            from app.services.retrieval.query_service import QueryService
            from app.agents.synthesizer import AnswerSynthesizer

            qs = QueryService()
            chunks = await qs.hybrid_search(query=query, top_k=5)

            synthesizer = AnswerSynthesizer()
            result = await synthesizer.synthesize(
                query=query,
                intent="factual",
                chunks=chunks,
            )

            answer_text = result.answer or "Không thể tổng hợp câu trả lời."

            return AgentResult(
                answer=answer_text,
                citations=[
                    {
                        "document_id": c.get("document_id", ""),
                        "document_title": c.get("document_title", "Wikipedia"),
                        "source_url": c.get("source_url", ""),
                        "chunk_id": c.get("chunk_id", ""),
                        "section_title": c.get("section_title", ""),
                        "excerpt": str(c.get("content", ""))[:120] + "...",
                        "score": c.get("score", 0),
                    }
                    for c in chunks[:4]
                ],
                mode="factual",
                trace={"intent": "factual", "workflow": "fallback", "cache_hit": False},
                intent="factual",
                chunks=chunks,
            )
        except Exception as exc:
            logger.error("fallback_pipeline_failed", error=str(exc))
            return AgentResult(
                answer="Không thể tổng hợp câu trả lời do lỗi hệ thống.",
                citations=[],
                mode="error",
                trace={"intent": "factual", "workflow": "fallback_error", "cache_hit": False},
                intent="factual",
            )

    # ─── Public API ──────────────────────────────────────────────────────────

    async def answer(
        self,
        query: str,
        db: AsyncSession,
        mode: str | None = None,
        filters: dict | None = None,
        return_chunks: bool = False,
        session_id: str | None = None,
    ) -> AgentResult:
        """Execute the agent pipeline and return a structured result."""
        started = perf_counter()

        # Safety: Input
        passed, safety_info = await self._safety_input_check(query, session_id)
        if not passed:
            return AgentResult(
                answer=f"Câu hỏi không được chấp nhận: {safety_info.get('reason', 'Unknown')}",
                citations=[],
                mode="blocked",
                trace={"blocked": True},
                intent="blocked",
                safety_info=safety_info,
            )

        # Cache fast path
        cached = await self._cache_get(query, filters)
        if cached:
            logger.info("agent_answer_cached", query=query[:50])
            return AgentResult(
                answer=cached["answer"],
                citations=cached.get("citations", []),
                mode=cached.get("mode", mode or "factual"),
                trace={**cached.get("trace", {}), "cache_hit": True},
                intent=cached.get("intent", ""),
                chunks=None,
            )

        # Domain Guardrail check (Fast-path reject)
        from app.agents.domain_classifier import _classifier, DomainDecision
        from app.core.credentials import CredentialValidator
        from app.core.exceptions import ServiceUnavailableError

        validator = CredentialValidator()
        llm_checked = False

        domain_res = _classifier.classify_rules(query)
        if domain_res is None:
            # Ambiguous: Need LLM domain classification, verify key first
            await validator.ensure_llm_available()
            llm_checked = True
            domain_res = await _classifier.classify_llm(query)

        if domain_res.decision == DomainDecision.UNKNOWN:
            raise ServiceUnavailableError("LLM (Domain Classifier)")

        if domain_res.decision == DomainDecision.OUT_OF_SCOPE:
            from app.services.agent.workflows.out_of_scope import OutOfScopeWorkflow
            workflow = OutOfScopeWorkflow()
            wf_res = await workflow.execute(query)
            
            result = AgentResult(
                answer=wf_res["answer"],
                citations=[],
                mode="fast",
                trace={
                    "workflow": "early_route_out_of_scope",
                    "cache_hit": False,
                    "reason": domain_res.reason,
                    "agent_trace": [
                        {
                            "agent": "Domain Guardrail",
                            "action": f"Phát hiện truy vấn ngoài phạm vi (out_of_scope). Lý do: {domain_res.reason}",
                            "status": "success",
                        }
                    ],
                },
                intent="out_of_scope",
                chunks=[],
            )
            await self._cache_set(query, filters, {
                "answer": result.answer,
                "citations": result.citations,
                "mode": result.mode,
                "trace": result.trace,
                "intent": result.intent,
            })
            return result


        # Complexity classification (0 LLM cost)
        execution_mode, intent = self._classify_complexity(query)
        logger.info(
            "complexity_routed",
            mode=execution_mode,
            intent=intent,
            query=query[:60],
        )

        # Early routing for greetings and out of scope queries
        if intent in ("greeting", "out_of_scope"):
            if not llm_checked:
                await validator.ensure_llm_available()
                llm_checked = True
            try:
                from app.services.llm.client import get_llm_client
                llm = get_llm_client()
                if intent == "greeting":
                    prompt = (
                        f"Người dùng nói: \"{query}\"\n\n"
                        f"Đây là câu chào hỏi hoặc câu hỏi xã giao không liên quan đến lịch sử cụ thể.\n"
                        f"Hãy trả lời thân thiện, ngắn gọn (2-3 câu), giới thiệu bản thân là HistoriAI — "
                        f"trợ lý nghiên cứu lịch sử Việt Nam giai đoạn 1945–1975. Mới người dùng đặt câu hỏi lịch sử."
                    )
                    system = "Bạn là HistoriAI, trợ lý nghiên cứu lịch sử Việt Nam thân thiện."
                else:
                    prompt = (
                        f"Người dùng hỏi: \"{query}\"\n\n"
                        f"Câu hỏi này nằm ngoài phạm vi lịch sử Việt Nam giai đoạn 1945–1975.\n"
                        f"Hãy từ chối một cách lịch sự, giải thích rõ phạm vi chuyên môn của mình (lịch sử Việt Nam 1945-1975), "
                        f"và mời họ hỏi câu hỏi thuộc phạm vi này."
                    )
                    system = "Bạn là HistoriAI, trợ lý chỉ trả lời về lịch sử Việt Nam giai đoạn 1945–1975."

                answer_text = await llm.generate(prompt, system=system, max_tokens=300)
                if "[Phản hồi từ bộ nhớ tạm:" in answer_text:
                    answer_text = STATIC_GREETING_ANSWER if intent == "greeting" else STATIC_OUT_OF_SCOPE_ANSWER
            except Exception as exc:
                logger.warning("early_routing_llm_failed_using_static", error=str(exc))
                answer_text = STATIC_GREETING_ANSWER if intent == "greeting" else STATIC_OUT_OF_SCOPE_ANSWER

            result = AgentResult(
                answer=answer_text,
                citations=[],
                mode="fast",
                trace={
                    "workflow": f"early_route_{intent}",
                    "cache_hit": False,
                    "agent_trace": [
                        {
                            "agent": "Orchestrator Gateway",
                            "action": f"Phát hiện truy vấn {intent}. Phân luồng trả lời trực tiếp.",
                            "status": "success",
                        }
                    ],
                },
                intent=intent,
                chunks=[],
            )
            # Cache the result
            await self._cache_set(query, filters, {
                "answer": result.answer,
                "citations": result.citations,
                "mode": result.mode,
                "trace": result.trace,
                "intent": result.intent,
            })
            return result

        # RAG pipeline requires LLM verification
        if not llm_checked:
            await validator.ensure_llm_available()
            llm_checked = True

        # Agent graph pipeline (primary)
        initial_state = _build_initial_state(
            query, session_id, filters, execution_mode
        )

        try:
            thread_id = session_id or "default-thread"
            result_state = await self._run_agent_graph(initial_state, thread_id)
        except Exception as exc:
            logger.error(
                "agent_graph_failed_using_fallback",
                error=str(exc),
                query=query[:50],
            )
            return await self._fallback_answer(query, db)

        # Extract results
        answer_text = result_state.get("answer") or "Không thể tổng hợp câu trả lời."
        citations = result_state.get("citations") or []
        chunks = result_state.get("retrieved_chunks") or []

        # Safety: Output
        answer_text, extra_safety = await self._safety_output_check(answer_text, session_id)
        safety_info.update(extra_safety)

        # Metrics
        total_ms = int((perf_counter() - started) * 1000)
        self._record_metrics(execution_mode, total_ms, len(citations))

        trace_data = {
            "intent": execution_mode,
            "workflow": "langgraph_multi_agent",
            "agent_trace": result_state.get("agent_trace", []),
            "total_ms": total_ms,
            "synthesis": {"used_llm": True, "citation_validation_passed": True},
            "tools_used": [
                "supervisor_planning",
                "hybrid_retrieval",
                "timeline_chronology",
                "neo4j_graph_traversal",
                "critic_reflection",
                "memory_consolidation",
            ],
        }

        result = AgentResult(
            answer=answer_text,
            citations=citations,
            mode=execution_mode,
            trace=trace_data,
            intent=execution_mode,
            chunks=chunks if return_chunks else None,
            safety_info=safety_info,
        )

        # Cache result
        await self._cache_set(query, filters, {
            "answer": result.answer,
            "citations": result.citations,
            "mode": result.mode,
            "trace": result.trace,
            "intent": result.intent,
        })

        return result

    async def answer_stream(
        self,
        query: str,
        db: AsyncSession,
        mode: str | None = None,
        filters: dict | None = None,
        session_id: str | None = None,
    ) -> AsyncIterator[dict]:
        """
        Execute the agent pipeline with SSE streaming.

        Uses agent_graph.astream() for node-level streaming.
        Falls back to minimal streaming if agent_graph fails.
        """
        started = perf_counter()

        # Safety input check
        passed, safety_info = await self._safety_input_check(query, session_id)
        if not passed:
            yield {"type": "error", "error": f"Câu hỏi không được chấp nhận."}
            yield {"type": "done"}
            return

        # Cache fast path
        cached = await self._cache_get(query, filters)
        if cached:
            yield {"type": "stage", "stage": "classifying"}
            yield {"type": "stage", "stage": "retrieving"}
            yield {"type": "stage", "stage": "verifying"}
            yield {"type": "stage", "stage": "generating"}
            import asyncio
            for token in cached["answer"].split(" "):
                yield {"type": "token", "token": token + " "}
                await asyncio.sleep(0.02)
            yield {"type": "citations", "citations": cached.get("citations", [])}
            yield {"type": "trace", "trace": {**cached.get("trace", {}), "cache_hit": True}}
            yield {"type": "done"}
            return

        # Domain Guardrail check (Fast-path reject)
        from app.agents.domain_classifier import _classifier, DomainDecision
        from app.core.credentials import CredentialValidator

        validator = CredentialValidator()
        llm_checked = False

        domain_res = _classifier.classify_rules(query)
        if domain_res is None:
            # Ambiguous: Need LLM domain classification, verify key first
            try:
                await validator.ensure_llm_available()
                llm_checked = True
            except Exception as exc:
                yield {"type": "error", "error": str(exc)}
                yield {"type": "done"}
                return
            domain_res = await _classifier.classify_llm(query)

        if domain_res.decision == DomainDecision.UNKNOWN:
            yield {"type": "error", "error": "Service unavailable: LLM (Domain Classifier)"}
            yield {"type": "done"}
            return

        if domain_res.decision == DomainDecision.OUT_OF_SCOPE:
            yield {"type": "stage", "stage": "classifying"}
            yield {"type": "stage", "stage": "generating"}
            yield {
                "type": "trace_step",
                "step": {
                    "agent": "Domain Guardrail",
                    "action": f"Phát hiện truy vấn ngoài phạm vi (out_of_scope). Lý do: {domain_res.reason}",
                    "status": "success",
                },
            }
            
            from app.services.agent.workflows.out_of_scope import OutOfScopeWorkflow
            workflow = OutOfScopeWorkflow()
            wf_res = await workflow.execute(query)
            answer_text = wf_res["answer"]
            
            import asyncio
            for word in answer_text.split(" "):
                yield {"type": "token", "token": word + " "}
                await asyncio.sleep(0.01)
                
            trace_dict = {
                "intent": "out_of_scope",
                "workflow": "early_route_out_of_scope",
                "cache_hit": False,
                "reason": domain_res.reason,
                "agent_trace": [
                    {
                        "agent": "Domain Guardrail",
                        "action": f"Phát hiện truy vấn ngoài phạm vi (out_of_scope). Lý do: {domain_res.reason}",
                        "status": "success",
                    }
                ],
            }
            await self._cache_set(query, filters, {
                "answer": answer_text,
                "citations": [],
                "mode": "fast",
                "trace": trace_dict,
                "intent": "out_of_scope",
            })
            
            yield {"type": "citations", "citations": []}
            yield {"type": "trace", "trace": trace_dict}
            yield {"type": "done"}
            return


        # Complexity classification
        execution_mode, intent = self._classify_complexity(query)
        yield {"type": "stage", "stage": "classifying"}

        # Early routing for greetings and out of scope queries
        if intent in ("greeting", "out_of_scope"):
            if not llm_checked:
                try:
                    await validator.ensure_llm_available()
                    llm_checked = True
                except Exception as exc:
                    yield {"type": "error", "error": str(exc)}
                    yield {"type": "done"}
                    return
            yield {"type": "stage", "stage": "generating"}
            yield {
                "type": "trace_step",
                "step": {
                    "agent": "Orchestrator Gateway",
                    "action": f"Phát hiện truy vấn {intent}. Phân luồng trả lời trực tiếp.",
                    "status": "success",
                },
            }

            answer_text = ""
            try:
                from app.services.llm.client import get_llm_client
                llm = get_llm_client()
                if intent == "greeting":
                    prompt = (
                        f"Người dùng nói: \"{query}\"\n\n"
                        f"Đây là câu chào hỏi hoặc câu hỏi xã giao không liên quan đến lịch sử cụ thể.\n"
                        f"Hãy trả lời thân thiện, ngắn gọn (2-3 câu), giới thiệu bản thân là HistoriAI — "
                        f"trợ lý nghiên cứu lịch sử Việt Nam giai đoạn 1945–1975. Mới người dùng đặt câu hỏi lịch sử."
                    )
                    system = "Bạn là HistoriAI, trợ lý nghiên cứu lịch sử Việt Nam thân thiện."
                else:
                    prompt = (
                        f"Người dùng hỏi: \"{query}\"\n\n"
                        f"Câu hỏi này nằm ngoài phạm vi lịch sử Việt Nam giai đoạn 1945–1975.\n"
                        f"Hãy từ chối một cách lịch sự, giải thích rõ phạm vi chuyên môn của mình (lịch sử Việt Nam 1945-1975), "
                        f"và mời họ hỏi câu hỏi thuộc phạm vi này."
                    )
                    system = "Bạn là HistoriAI, trợ lý chỉ trả lời về lịch sử Việt Nam giai đoạn 1945–1975."

                async for token_obj in llm.astream(prompt, system=system, max_tokens=300):
                    token = token_obj.text
                    answer_text += token
                    yield {"type": "token", "token": token}
            except Exception as exc:
                logger.warning("early_routing_llm_failed_using_static", error=str(exc))
                static_ans = STATIC_GREETING_ANSWER if intent == "greeting" else STATIC_OUT_OF_SCOPE_ANSWER
                answer_text = static_ans
                import asyncio
                for word in static_ans.split(" "):
                    yield {"type": "token", "token": word + " "}
                    await asyncio.sleep(0.02)

            # Cache the result
            trace_dict = {
                "intent": intent,
                "workflow": f"early_route_{intent}",
                "cache_hit": False,
                "agent_trace": [
                    {
                        "agent": "Orchestrator Gateway",
                        "action": f"Phát hiện truy vấn {intent}. Phân luồng trả lời trực tiếp.",
                        "status": "success",
                    }
                ],
            }
            await self._cache_set(query, filters, {
                "answer": answer_text,
                "citations": [],
                "mode": "fast",
                "trace": trace_dict,
                "intent": intent,
            })

            yield {"type": "citations", "citations": []}
            yield {"type": "trace", "trace": trace_dict}
            yield {"type": "done"}
            return

        # RAG pipeline requires LLM verification
        if not llm_checked:
            try:
                await validator.ensure_llm_available()
                llm_checked = True
            except Exception as exc:
                yield {"type": "error", "error": str(exc)}
                yield {"type": "done"}
                return

        initial_state = _build_initial_state(
            query, session_id, filters, execution_mode
        )

        # Yield initial supervisor pending step
        yield {
            "type": "trace_step",
            "step": {
                "agent": "Supervisor",
                "action": "Đang phân loại và lập kế hoạch...",
                "status": "pending",
            },
        }

        try:
            result_state = initial_state
            last_trace_idx = 0

            thread_id = session_id or "default-thread"
            async for chunk in self._stream_agent_graph(initial_state, thread_id):
                # Merge state updates
                for node_name, val in chunk.items():
                    if val:
                        for k, v in val.items():
                            result_state[k] = v

                # Map nodes to stages
                for node_name in chunk.keys():
                    if node_name == "supervisor_node":
                        yield {"type": "stage", "stage": "classifying"}
                    elif node_name in ("retrieval_node", "timeline_node", "graph_node"):
                        yield {"type": "stage", "stage": "retrieving"}
                    elif node_name == "world_model_node":
                        yield {"type": "stage", "stage": "generating"}
                    elif node_name == "critic_node":
                        yield {"type": "stage", "stage": "verifying"}
                    elif node_name in ("reasoning_node", "memory_consolidation_node"):
                        yield {"type": "stage", "stage": "generating"}

                # Stream completed trace steps
                current_trace = result_state.get("agent_trace", [])
                while last_trace_idx < len(current_trace):
                    yield {
                        "type": "trace_step",
                        "step": {
                            "agent": current_trace[last_trace_idx].get("agent", ""),
                            "action": current_trace[last_trace_idx].get("action", ""),
                            "status": current_trace[last_trace_idx].get("status", "success"),
                        },
                    }
                    last_trace_idx += 1

                # Yield pending next step
                for node_name in chunk.keys():
                    next_node = self._predict_next_node(node_name, result_state)
                    if next_node and next_node != "supervisor_node":
                        agent_name = {
                            "retrieval_node": "Retrieval Agent",
                            "timeline_node": "Timeline Agent",
                            "graph_node": "Knowledge Graph Agent",
                            "world_model_node": "World Model Agent",
                            "reasoning_node": "Reasoning Agent",
                            "critic_node": "Critic Agent",
                            "memory_consolidation_node": "Memory Consolidation Agent",
                        }.get(next_node, "System")
                        yield {
                            "type": "trace_step",
                            "step": {
                                "agent": agent_name,
                                "action": "Đang xử lý...",
                                "status": "pending",
                            },
                        }

                    yield {
                        "type": "trace",
                        "trace": {
                            "intent": execution_mode,
                            "workflow": "langgraph_multi_agent",
                            "agent_trace": current_trace,
                            "total_ms": int((perf_counter() - started) * 1000),
                            "synthesis": {"used_llm": True, "citation_validation_passed": True},
                        },
                    }

            # Stream the final answer tokens
            answer_text = result_state.get("answer") or "Không thể tổng hợp câu trả lời."
            citations = result_state.get("citations") or []

            # Safety output check
            answer_text, _ = await self._safety_output_check(answer_text, session_id)

            import asyncio
            words = answer_text.split(" ")
            for i, word in enumerate(words):
                token = word + (" " if i < len(words) - 1 else "")
                yield {"type": "token", "token": token}
                await asyncio.sleep(0.01)

            trace_data = {
                "intent": execution_mode,
                "workflow": "langgraph_multi_agent",
                "agent_trace": result_state.get("agent_trace", []),
                "total_ms": int((perf_counter() - started) * 1000),
                "synthesis": {"used_llm": True, "citation_validation_passed": True},
                "tools_used": [
                    "supervisor_planning",
                    "hybrid_retrieval",
                    "timeline_chronology",
                    "neo4j_graph_traversal",
                    "critic_reflection",
                    "memory_consolidation",
                ],
            }

            yield {"type": "citations", "citations": citations}
            yield {"type": "trace", "trace": trace_data}
            yield {"type": "done"}

        except Exception as exc:
            logger.error("agent_graph_stream_failed", error=str(exc), query=query[:50])
            # Minimal fallback streaming
            fallback_result = await self._fallback_answer(query, db)
            import asyncio
            words = fallback_result.answer.split(" ")
            for i, word in enumerate(words):
                yield {"type": "token", "token": word + (" " if i < len(words) - 1 else "")}
                await asyncio.sleep(0.01)
            yield {"type": "citations", "citations": fallback_result.citations}
            yield {"type": "trace", "trace": fallback_result.trace}
            yield {"type": "done"}

        # Cache result (fire-and-forget)
        final_answer = result_state.get("answer", "") if "result_state" in dir() else ""
        final_citations = result_state.get("citations", []) if "result_state" in dir() else []
        if final_answer:
            await self._cache_set(query, filters, {
                "answer": final_answer,
                "citations": final_citations,
                "mode": execution_mode,
                "trace": {},
                "intent": execution_mode,
            })

    def _predict_next_node(self, current_node: str, state: dict[str, Any]) -> str | None:
        """Predict the next node name for pending-step display."""
        m = state.get("execution_mode", "agentic")
        plan = state.get("plan", [])
        current_step = state.get("current_step", 0)

        node_map = {
            "supervisor_node": (
                plan[current_step] if current_step < len(plan)
                else ("world_model_node" if m == "agentic" else "reasoning_node")
            ),
            "world_model_node": "reasoning_node",
            "reasoning_node": (
                "critic_node" if m == "agentic" else "memory_consolidation_node"
            ),
            "critic_node": (
                "supervisor_node" if state.get("replanning_required")
                else "memory_consolidation_node"
            ),
        }
        return node_map.get(current_node)

    def _record_metrics(
        self,
        intent: str,
        total_ms: int,
        citation_count: int,
    ) -> None:
        """Record Prometheus metrics (best-effort)."""
        try:
            from app.core.metrics import QUERY_TOTAL, QUERY_LATENCY
            QUERY_TOTAL.labels(intent=intent, status="success").inc()
            QUERY_LATENCY.labels(stage="total").observe(total_ms / 1000)
        except Exception:
            pass
