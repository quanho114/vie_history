"""Safe Agent Graph - LangGraph with integrated safety checkpoints and monitoring.

This module wraps the agent_graph with production-grade safety features:
- Safety checkpoints before each node execution
- Runtime monitoring with anomaly detection
- Token budget enforcement
- Circuit breaker integration
- Graceful degradation

Usage:
    from app.services.agent.safety.safe_graph import create_safe_agent_graph
    
    safe_graph = create_safe_agent_graph()
    result = await safe_graph.ainvoke(initial_state)
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable

from langgraph.graph import END, StateGraph

from app.core.logging import get_logger
from app.services.agent.safety import (
    get_agent_safety,
    get_anomaly_detector,
    get_resilience,
    get_context_manager,
    get_tool_safety,
    AbortReason,
    AgentSafety,
    AnomalyDetector,
    GracefulDegradation,
    ContextManager,
    ToolSafety,
)
from app.services.agent.safety.context_manager import ContextManager as SafeContextManager

logger = get_logger("safe_agent_graph")


class SafeAgentState(dict):
    """Extended agent state with safety metadata."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._safety_metadata = {
            "can_checkpoint": True,
            "checkpoint_id": None,
            "node_start_time": None,
            "node_latency_ms": 0,
            "tokens_used": 0,
            "cost_usd": 0,
        }
    
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
    
    def __getitem__(self, key):
        return super().__getitem__(key)
    
    @property
    def safety(self):
        return self._safety_metadata


def create_safe_agent_graph():
    """
    Create a safety-wrapped version of the agent graph.
    
    Adds:
    - Pre-execution safety checks
    - Post-execution monitoring
    - Anomaly detection
    - Checkpointing
    - Token budget tracking
    """
    from app.agents.agent_graph import (
        AgentState,
        supervisor_node,
        retrieval_node,
        timeline_node,
        graph_node,
        world_model_node,
        reasoning_node,
        critic_node,
        memory_consolidation_node,
        router,
    )
    
    # Create the base graph
    builder = StateGraph(AgentState)
    
    # Add all nodes
    builder.add_node("supervisor", safe_supervisor_node)
    builder.add_node("retrieval", safe_retrieval_node)
    builder.add_node("timeline", safe_timeline_node)
    builder.add_node("graph", safe_graph_node)
    builder.add_node("world_model", safe_world_model_node)
    builder.add_node("reasoning", safe_reasoning_node)
    builder.add_node("critic", safe_critic_node)
    builder.add_node("memory", safe_memory_node)
    
    # Set entry point
    builder.set_entry_point("supervisor")
    
    # Add conditional edges with safety routing
    builder.add_conditional_edges(
        "supervisor",
        safe_router,
    )
    
    # Add edges from other nodes back to supervisor for review
    builder.add_edge("retrieval", "supervisor")
    builder.add_edge("timeline", "supervisor")
    builder.add_edge("graph", "supervisor")
    builder.add_edge("world_model", "supervisor")
    builder.add_edge("reasoning", END)
    builder.add_edge("critic", "supervisor")
    builder.add_edge("memory", END)
    
    return builder.compile()


# ─── Safe Node Wrappers ────────────────────────────────────────────────────────


async def safe_supervisor_node(state: AgentState) -> dict[str, Any]:
    """Supervisor with safety checks."""
    safety = get_agent_safety()
    detector = get_anomaly_detector()
    
    session_id = state.get("session_id") or "unknown"
    
    # Check if session is aborted
    if await safety.is_aborted(session_id):
        logger.warning("supervisor_aborted_session", session_id=session_id)
        return {"answer": "Session was aborted.", "agent_trace": []}
    
    # Check can continue
    can_continue, reason = await safety.can_continue(session_id)
    if not can_continue:
        logger.warning("supervisor_blocked", session_id=session_id, reason=reason)
        return {"answer": f"Execution blocked: {reason}", "agent_trace": []}
    
    # Record step start
    state.safety["node_start_time"] = time.time()
    
    # Run supervisor
    result = await supervisor_node(state)
    
    # Record step completion
    await _record_step_completion(
        session_id,
        "supervisor",
        state,
        result
    )
    
    return result


async def safe_retrieval_node(state: AgentState) -> dict[str, Any]:
    """Retrieval with circuit breaker and safety."""
    safety = get_agent_safety()
    resilience = get_resilience()
    detector = get_anomaly_detector()
    
    session_id = state.get("session_id") or "unknown"
    state.safety["node_start_time"] = time.time()
    
    # Execute with circuit breaker
    try:
        result = await resilience.execute_with_circuit_breaker(
            service="retrieval",
            operation=lambda: retrieval_node(state),
            fallback=lambda: _retrieval_fallback(state)
        )
        
        await _record_step_completion(
            session_id,
            "retrieval",
            state,
            result
        )
        
        return result
        
    except Exception as e:
        logger.error("retrieval_safe_execution_failed", error=str(e))
        return await _retrieval_fallback(state)


async def _retrieval_fallback(state: AgentState) -> dict[str, Any]:
    """Fallback for retrieval node."""
    logger.info("using_retrieval_fallback")
    return {
        "retrieved_chunks": [],
        "agent_trace": state.get("agent_trace", []) + [
            {"agent": "Retrieval Fallback", "action": "Retrieval failed, returning empty results", "status": "warning"}
        ],
    }


async def safe_timeline_node(state: AgentState) -> dict[str, Any]:
    """Timeline with circuit breaker and safety."""
    resilience = get_resilience()
    detector = get_anomaly_detector()
    
    session_id = state.get("session_id") or "unknown"
    state.safety["node_start_time"] = time.time()
    
    try:
        result = await resilience.execute_with_circuit_breaker(
            service="timeline",
            operation=lambda: timeline_node(state),
            fallback=lambda: _timeline_fallback(state)
        )
        
        await _record_step_completion(
            session_id,
            "timeline",
            state,
            result
        )
        
        return result
        
    except Exception as e:
        logger.error("timeline_safe_execution_failed", error=str(e))
        return await _timeline_fallback(state)


async def _timeline_fallback(state: AgentState) -> dict[str, Any]:
    """Fallback for timeline node."""
    return {
        "timeline_events": [],
        "agent_trace": state.get("agent_trace", []) + [
            {"agent": "Timeline Fallback", "action": "Timeline lookup failed", "status": "warning"}
        ],
    }


async def safe_graph_node(state: AgentState) -> dict[str, Any]:
    """Graph with circuit breaker and safety."""
    resilience = get_resilience()
    
    session_id = state.get("session_id") or "unknown"
    state.safety["node_start_time"] = time.time()
    
    try:
        result = await resilience.execute_with_circuit_breaker(
            service="graph",
            operation=lambda: graph_node(state),
            fallback=lambda: _graph_fallback(state)
        )
        
        await _record_step_completion(
            session_id,
            "graph",
            state,
            result
        )
        
        return result
        
    except Exception as e:
        logger.error("graph_safe_execution_failed", error=str(e))
        return await _graph_fallback(state)


async def _graph_fallback(state: AgentState) -> dict[str, Any]:
    """Fallback for graph node."""
    return {
        "graph_entities": [],
        "agent_trace": state.get("agent_trace", []) + [
            {"agent": "Graph Fallback", "action": "Graph traversal failed", "status": "warning"}
        ],
    }


async def safe_world_model_node(state: AgentState) -> dict[str, Any]:
    """World model with token budget and safety."""
    safety = get_agent_safety()
    resilience = get_resilience()
    
    session_id = state.get("session_id") or "unknown"
    state.safety["node_start_time"] = time.time()
    
    # Check token budget before LLM call
    budget = await safety.get_token_budget(session_id)
    if budget.total_tokens_used + 1024 > budget.max_total_tokens:
        logger.warning("world_model_skipped_token_limit", tokens_used=budget.total_tokens_used)
        return {
            "world_model_analysis": None,
            "agent_trace": state.get("agent_trace", []) + [
                {"agent": "World Model (Skipped)", "action": "Skipped due to token budget", "status": "info"}
            ],
        }
    
    try:
        result = await resilience.execute_with_circuit_breaker(
            service="world_model",
            operation=lambda: world_model_node(state),
            fallback=lambda: {"world_model_analysis": None, "agent_trace": []}
        )
        
        await _record_step_completion(
            session_id,
            "world_model",
            state,
            result
        )
        
        return result
        
    except Exception as e:
        logger.error("world_model_safe_execution_failed", error=str(e))
        return {"world_model_analysis": None, "agent_trace": []}


async def safe_reasoning_node(state: AgentState) -> dict[str, Any]:
    """Reasoning with safety and output filtering."""
    safety = get_agent_safety()
    tool_safety = get_tool_safety()
    resilience = get_resilience()
    
    session_id = state.get("session_id") or "unknown"
    state.safety["node_start_time"] = time.time()
    
    try:
        result = await resilience.execute_with_circuit_breaker(
            service="reasoning",
            operation=lambda: reasoning_node(state),
            fallback=lambda: _reasoning_fallback(state)
        )
        
        # Filter output before returning
        answer = result.get("answer", "")
        if answer:
            filter_result = await tool_safety.filter_output(answer)
            if not filter_result.is_safe:
                logger.warning(
                    "output_filtered",
                    session_id=session_id,
                    risk_level=filter_result.risk_level.value,
                    removed_items=filter_result.removed_items,
                )
            result["answer"] = filter_result.filtered_content
        
        await _record_step_completion(
            session_id,
            "reasoning",
            state,
            result
        )
        
        return result
        
    except Exception as e:
        logger.error("reasoning_safe_execution_failed", error=str(e))
        return await _reasoning_fallback(state)


async def _reasoning_fallback(state: AgentState) -> dict[str, Any]:
    """Fallback for reasoning node."""
    # Try extractive fallback
    chunks = state.get("retrieved_chunks", [])
    if chunks:
        excerpts = [f"[S{i+1}] {c.get('content', '')[:200]}..." for i, c in enumerate(chunks[:3])]
        answer = "Dựa trên tư liệu tìm được, câu trả lời có thể tóm lược như sau:\n\n" + "\n\n".join(excerpts)
        return {
            "answer": answer,
            "citations": [
                {
                    "document_id": c.get("document_id", ""),
                    "document_title": c.get("document_title", "Unknown"),
                    "excerpt": c.get("content", "")[:120] + "...",
                }
                for c in chunks[:3]
            ],
            "agent_trace": state.get("agent_trace", []) + [
                {"agent": "Reasoning Fallback (Extractive)", "action": "LLM synthesis failed, using extractive answer", "status": "warning"}
            ],
        }
    
    return {
        "answer": "Xin lỗi, không thể tạo câu trả lời do lỗi kỹ thuật. Vui lòng thử lại sau.",
        "citations": [],
        "agent_trace": state.get("agent_trace", []) + [
            {"agent": "Reasoning Fallback", "action": "All synthesis methods failed", "status": "error"}
        ],
    }


async def safe_critic_node(state: AgentState) -> dict[str, Any]:
    """Critic with anomaly detection."""
    detector = get_anomaly_detector()
    
    session_id = state.get("session_id") or "unknown"
    state.safety["node_start_time"] = time.time()
    
    result = await critic_node(state)
    
    # Check for anomalies
    anomalies = await detector.check_anomalies(
        session_id,
        state=state,
        output=state.get("answer")
    )
    
    if anomalies:
        logger.warning("anomalies_detected_in_critic", count=len(anomalies))
        
        # Add anomaly info to trace
        anomaly_trace = [
            {"agent": f"Anomaly Detector", "action": f"{a.type.value}: {a.message}", "status": "warning"}
            for a in anomalies
        ]
        result["agent_trace"] = (result.get("agent_trace", [])) + anomaly_trace
        
        # Auto-respond to critical anomalies
        for anomaly in anomalies:
            if anomaly.severity.value in ("error", "critical"):
                await detector.respond_to_anomaly(anomaly)
                
                # If loop detected, abort
                if anomaly.type.value == "runaway_loop":
                    safety = get_agent_safety()
                    await safety.abort_session(session_id, AbortReason.LOOP_DETECTED)
                    result["answer"] = "Session aborted due to detected loop."
    
    await _record_step_completion(session_id, "critic", state, result)
    
    return result


async def safe_memory_node(state: AgentState) -> dict[str, Any]:
    """Memory consolidation with context management."""
    context_manager = get_context_manager()
    safety = get_agent_safety()
    
    session_id = state.get("session_id") or "unknown"
    state.safety["node_start_time"] = time.time()
    
    # Run memory consolidation
    result = await memory_consolidation_node(state)
    
    # Update context manager
    turns = state.get("agent_trace", [])
    for turn in turns:
        if turn.get("agent"):
            await context_manager.add(
                session_id,
                role="system",
                content=f"[{turn['agent']}] {turn.get('action', '')}",
            )
    
    # Maybe compact if needed
    await context_manager.maybe_compact(session_id)
    
    await _record_step_completion(session_id, "memory", state, result)
    
    return result


# ─── Safe Router ──────────────────────────────────────────────────────────────


async def safe_router(state: AgentState) -> str:
    """Router with safety checks and anomaly detection."""
    safety = get_agent_safety()
    detector = get_anomaly_detector()
    
    session_id = state.get("session_id") or "unknown"
    
    # Check if aborted
    if await safety.is_aborted(session_id):
        return END
    
    # Check for anomalies
    anomalies = await detector.check_anomalies(session_id, state=state)
    
    # Handle critical anomalies
    for anomaly in anomalies:
        if anomaly.severity.value in ("error", "critical"):
            if anomaly.type.value == "runaway_loop":
                await safety.abort_session(session_id, AbortReason.LOOP_DETECTED)
                return END
            elif anomaly.type.value == "token_explosion":
                await safety.abort_session(session_id, AbortReason.TOKEN_BUDGET_EXCEEDED)
                return END
    
    # Check can continue
    can_continue, reason = await safety.can_continue(session_id)
    if not can_continue:
        logger.warning("router_blocked", session_id=session_id, reason=reason)
        return END
    
    # Use original router
    return router(state)


# ─── Helper Functions ────────────────────────────────────────────────────────


async def _record_step_completion(
    session_id: str,
    node_name: str,
    state: AgentState,
    result: dict
) -> None:
    """Record step completion for monitoring."""
    safety = get_agent_safety()
    detector = get_anomaly_detector()
    
    if not state.safety.get("node_start_time"):
        return
    
    # Calculate latency
    latency_ms = (time.time() - state.safety["node_start_time"]) * 1000
    
    # Record step
    await detector.record_step(
        session_id=session_id,
        node=node_name,
        latency_ms=latency_ms,
    )
    
    # Update safety session
    session = await safety.get_session(session_id)
    if session:
        session.execution_count += 1
        await safety._persist_session(session)
    
    logger.debug(
        "safe_node_completed",
        session_id=session_id,
        node=node_name,
        latency_ms=latency_ms,
    )


# ─── Safe Graph Instance ──────────────────────────────────────────────────────


_safe_graph = None


def get_safe_agent_graph():
    """Get or create the safe agent graph."""
    global _safe_graph
    if _safe_graph is None:
        _safe_graph = create_safe_agent_graph()
    return _safe_graph
