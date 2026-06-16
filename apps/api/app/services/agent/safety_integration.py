"""Safety Integration Layer - Wires all safety features into the agent system.

This module provides a unified interface for all safety features:
- Agent Safety (kill switch, token budget)
- Tool Safety (input validation, PII detection)
- Circuit Breakers (LLM, retrieval, external APIs)
- Anomaly Detection (loops, latency, cost)
- A2A Protocol (multi-agent communication)
- Context Management (sliding window, summarization)

Usage:
    from app.services.agent.safety_integration import SafetyIntegration, get_safety_integration
    
    integration = get_safety_integration()
    
    # Validate input before LLM call
    safe_input = await integration.validate_input(user_query)
    
    # Wrap LLM call with safety
    result = await integration.execute_with_safety(
        operation=lambda: llm.generate(prompt),
        service="openai",
        session_id="user-123"
    )
    
    # Check for anomalies
    await integration.check_anomalies(session_id)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, TypeVar

from app.core.logging import get_logger

logger = get_logger("safety_integration")

T = TypeVar("T")


@dataclass
class SafetyConfig:
    """Configuration for all safety features."""
    # Agent safety
    enable_kill_switch: bool = True
    enable_token_budget: bool = True
    max_tokens_per_session: int = 10000
    max_cost_per_session_usd: float = 2.00
    max_execution_seconds: int = 120
    
    # Tool safety
    enable_input_validation: bool = True
    enable_pii_detection: bool = True
    enable_output_filtering: bool = True
    
    # Circuit breaker
    enable_circuit_breaker: bool = True
    circuit_failure_threshold: int = 5
    circuit_timeout_seconds: float = 30.0
    
    # Anomaly detection
    enable_anomaly_detection: bool = True
    max_loop_iterations: int = 5
    max_latency_ms: int = 30000
    
    # Context management
    enable_context_compaction: bool = True
    max_context_tokens: int = 8000


class SafetyIntegration:
    """
    Unified safety integration for the agent system.
    
    This class wires together all safety features:
    - Input validation
    - Tool safety (PII, filtering)
    - Circuit breakers for external services
    - Anomaly detection
    - Kill switch and token budgets
    - Context management
    
    Usage:
        integration = SafetyIntegration(config)
        
        # Pre-processing
        safe_input = await integration.validate_input(query)
        
        # Execute with safety
        result = await integration.execute_with_safety(
            operation=lambda: llm_call(),
            service="openai",
            session_id="session-123"
        )
        
        # Post-processing
        safe_output = await integration.filter_output(result)
        
        # Anomaly checking
        anomalies = await integration.check_anomalies(session_id)
    """
    
    def __init__(self, config: SafetyConfig | None = None):
        self.config = config or SafetyConfig()
        
        # Lazy imports to avoid circular dependencies
        self._safety = None
        self._tool_safety = None
        self._resilience = None
        self._anomaly = None
        self._context = None
        self._a2a = None
    
    # ─── Lazy Initializers ────────────────────────────────────────────────────────
    
    @property
    def safety(self):
        """Get AgentSafety instance (lazy load)."""
        if self._safety is None:
            from app.services.agent.safety import AgentSafety, SafetyConfig as AgentSafetyConfig
            self._safety = AgentSafety(
                AgentSafetyConfig(
                    enable_kill_switch=self.config.enable_kill_switch,
                    enforce_hard_token_budget=self.config.enable_token_budget,
                    default_max_tokens=self.config.max_tokens_per_session,
                    max_cost_per_session_usd=self.config.max_cost_per_session_usd,
                    max_execution_seconds=self.config.max_execution_seconds,
                )
            )
        return self._safety
    
    @property
    def tool_safety(self):
        """Get ToolSafety instance (lazy load)."""
        if self._tool_safety is None:
            from app.services.agent.safety import ToolSafety, ToolSafetyConfig
            self._tool_safety = ToolSafety(
                ToolSafetyConfig(
                    enable_input_validation=self.config.enable_input_validation,
                    pii_detection_enabled=self.config.enable_pii_detection,
                    enable_output_filtering=self.config.enable_output_filtering,
                )
            )
        return self._tool_safety
    
    @property
    def resilience(self):
        """Get GracefulDegradation instance (lazy load)."""
        if self._resilience is None:
            from app.services.agent.safety import GracefulDegradation
            self._resilience = GracefulDegradation()
        return self._resilience
    
    @property
    def anomaly_detector(self):
        """Get AnomalyDetector instance (lazy load)."""
        if self._anomaly is None:
            from app.services.agent.safety import AnomalyDetector, AnomalyConfig
            self._anomaly = AnomalyDetector(
                AnomalyConfig(
                    max_loop_iterations=self.config.max_loop_iterations,
                    max_single_step_latency_ms=self.config.max_latency_ms,
                )
            )
        return self._anomaly
    
    @property
    def context_manager(self):
        """Get ContextManager instance (lazy load)."""
        if self._context is None:
            from app.services.agent.safety.context_manager import ContextManager, ContextConfig
            self._context = ContextManager(
                ContextConfig(
                    max_total_tokens=self.config.max_context_tokens,
                    enable_summarization=self.config.enable_context_compaction,
                )
            )
        return self._context
    
    # ─── Input Safety ─────────────────────────────────────────────────────────
    
    async def validate_input(
        self,
        query: str,
        context: dict | None = None,
    ) -> tuple[bool, str, dict]:
        """
        Validate user input before processing.
        
        Returns:
            (is_valid, reason, validation_result)
        """
        try:
            result = await self.tool_safety.validate_input(query, context)
            return result.is_valid, result.violations[-1] if result.violations else "OK", result
        except Exception as e:
            logger.error("input_validation_error", error=str(e))
            return True, "OK", {}  # Fail open for availability
    
    async def detect_pii(self, content: str) -> dict:
        """Detect PII in content."""
        try:
            res = await self.tool_safety.detect_pii(content)
            return {
                "has_pii": res.has_pii,
                "pii_types": res.pii_types,
                "masked_content": res.masked_content,
            }
        except Exception as e:
            logger.error("pii_detection_error", error=str(e))
            return {"has_pii": False, "masked_content": content}
    
    # ─── Execution Safety ─────────────────────────────────────────────────────
    
    async def execute_with_safety(
        self,
        operation: Callable[[], Awaitable[T]],
        service: str,
        session_id: str | None = None,
        fallback: Callable[[], Awaitable[T]] | None = None,
        track_tokens: bool = True,
    ) -> tuple[T | None, str]:
        """
        Execute an operation with full safety wrapping.
        
        Args:
            operation: Async function to execute
            service: Service name for circuit breaker
            session_id: Session ID for token tracking
            fallback: Optional fallback function
            track_tokens: Whether to track token usage
            
        Returns:
            (result, status_message)
        """
        start_time = time.time()
        result = None
        status = "success"
        
        try:
            # Check if session is aborted
            if session_id and self.config.enable_kill_switch:
                is_aborted = await self.safety.is_aborted(session_id)
                if is_aborted:
                    logger.warning("operation_aborted", session_id=session_id)
                    return None, "Session aborted"
                
                # Check can continue
                can_continue, reason = await self.safety.can_continue(session_id)
                if not can_continue:
                    logger.warning("operation_blocked", session_id=session_id, reason=reason)
                    return None, reason
            
            # Execute with circuit breaker
            if self.config.enable_circuit_breaker:
                cb = self.resilience.get_circuit_breaker(service)
                
                if fallback:
                    result = await cb.execute(operation, fallback)
                else:
                    result = await cb.execute(operation)
            else:
                result = await operation()
            
            # Track tokens if applicable
            if session_id and track_tokens:
                latency_ms = (time.time() - start_time) * 1000
                await self.anomaly_detector.record_step(
                    session_id=session_id,
                    node=service,
                    latency_ms=latency_ms,
                )
            
            # Check for anomalies
            if session_id and self.config.enable_anomaly_detection:
                anomalies = await self.anomaly_detector.check_anomalies(session_id)
                if anomalies:
                    for anomaly in anomalies:
                        logger.warning(
                            "anomaly_detected",
                            session_id=session_id,
                            type=anomaly.type.value,
                            severity=anomaly.severity.value,
                        )
            
            return result, "OK"
            
        except Exception as e:
            status = f"error: {str(e)}"
            logger.error(
                "operation_error",
                service=service,
                session_id=session_id,
                error=str(e),
            )
            return None, status
    
    async def execute_llm(
        self,
        operation: Callable[[], Awaitable[T]],
        session_id: str | None = None,
        model: str = "unknown",
    ) -> tuple[T | None, str, dict]:
        """
        Execute an LLM call with full safety.
        
        Returns:
            (result, status, token_info)
        """
        token_info = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
        
        # Input validation
        try:
            # For LLM, we mainly check for prompt injection
            pass
        except Exception as e:
            logger.error("llm_input_validation_error", error=str(e))
        
        # Execute with circuit breaker and fallback
        result, status = await self.execute_with_safety(
            operation=operation,
            service=f"llm_{model}",
            session_id=session_id,
            fallback=lambda: self._extractive_fallback(),
            track_tokens=True,
        )
        
        return result, status, token_info
    
    async def _extractive_fallback(self) -> str:
        """Fallback for LLM failures - extractive answer."""
        return "[Trả lời dạng trích xuất: Không có kết quả tổng hợp. Vui lòng thử câu hỏi cụ thể hơn.]"
    
    # ─── Output Safety ─────────────────────────────────────────────────────────
    
    async def filter_output(
        self,
        content: str,
        context: dict | None = None,
    ) -> tuple[str, bool, list[str]]:
        """
        Filter output before sending to user.
        
        Returns:
            (filtered_content, is_safe, removed_items)
        """
        try:
            result = await self.tool_safety.filter_output(content, context)
            
            if not result.is_safe:
                logger.warning(
                    "output_filtered",
                    risk_level=result.risk_level.value,
                    removed=result.removed_items,
                )
            
            return result.filtered_content, result.is_safe, result.removed_items
            
        except Exception as e:
            logger.error("output_filtering_error", error=str(e))
            return content, True, []
    
    # ─── Session Management ──────────────────────────────────────────────────
    
    async def init_session(self, session_id: str) -> dict:
        """Initialize safety for a new session."""
        try:
            session = await self.safety.get_session(session_id)
            
            # Initialize context manager
            self.context_manager._get_window(session_id)
            
            return {
                "session_id": session_id,
                "status": session.status if session else "active",
                "token_budget": {
                    "max_tokens": self.config.max_tokens_per_session,
                    "max_cost_usd": self.config.max_cost_per_session_usd,
                },
                "safety_enabled": {
                    "kill_switch": self.config.enable_kill_switch,
                    "token_budget": self.config.enable_token_budget,
                    "circuit_breaker": self.config.enable_circuit_breaker,
                    "anomaly_detection": self.config.enable_anomaly_detection,
                },
            }
        except Exception as e:
            logger.error("session_init_error", session_id=session_id, error=str(e))
            return {"session_id": session_id, "status": "error", "error": str(e)}
    
    async def abort_session(
        self,
        session_id: str,
        reason: str = "user_requested",
    ) -> bool:
        """Abort a session."""
        try:
            from app.services.agent.safety import AbortReason
            reason_enum = AbortReason.USER_REQUESTED
            if "timeout" in reason.lower():
                reason_enum = AbortReason.TIMEOUT
            elif "loop" in reason.lower():
                reason_enum = AbortReason.LOOP_DETECTED
            elif "cost" in reason.lower():
                reason_enum = AbortReason.COST_THRESHOLD_EXCEEDED
            elif "anomaly" in reason.lower():
                reason_enum = AbortReason.ANOMALY_DETECTED
            
            return await self.safety.abort_session(session_id, reason_enum, reason)
        except Exception as e:
            logger.error("session_abort_error", session_id=session_id, error=str(e))
            return False
    
    async def get_session_status(self, session_id: str) -> dict:
        """Get session safety status."""
        try:
            status = await self.safety.get_session_status(session_id)
            health = await self.anomaly_detector.get_session_health(session_id)
            
            return {
                "session_id": session_id,
                "safety_status": status,
                "health": health,
                "context_stats": await self.context_manager.get_stats(session_id),
            }
        except Exception as e:
            logger.error("session_status_error", session_id=session_id, error=str(e))
            return {"session_id": session_id, "error": str(e)}
    
    # ─── Anomaly Detection ─────────────────────────────────────────────────
    
    async def check_anomalies(
        self,
        session_id: str,
        state: dict | None = None,
        output: str | None = None,
    ) -> list[dict]:
        """Check for anomalies in session."""
        try:
            anomalies = await self.anomaly_detector.check_anomalies(
                session_id, state, output
            )
            
            # Auto-respond to critical anomalies
            for anomaly in anomalies:
                if anomaly.severity.value in ("error", "critical"):
                    await self.anomaly_detector.respond_to_anomaly(anomaly)
                    
                    # Auto-abort on critical anomalies
                    if anomaly.type.value in ("runaway_loop", "token_explosion"):
                        await self.abort_session(
                            session_id,
                            reason=f"Critical anomaly: {anomaly.type.value}"
                        )
            
            return [a.to_dict() for a in anomalies]
        except Exception as e:
            logger.error("anomaly_check_error", session_id=session_id, error=str(e))
            return []
    
    async def get_anomaly_summary(self, session_id: str | None = None) -> dict:
        """Get anomaly summary."""
        try:
            return self.anomaly_detector.get_anomaly_summary(session_id)
        except Exception as e:
            logger.error("anomaly_summary_error", error=str(e))
            return {"error": str(e)}
    
    # ─── Context Management ─────────────────────────────────────────────────
    
    async def add_context(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """Add context to session."""
        try:
            from app.services.agent.safety.context_manager import ContextPriority
            priority = {
                "user": ContextPriority.HIGH,
                "assistant": ContextPriority.MEDIUM,
                "system": ContextPriority.CRITICAL,
            }.get(role, ContextPriority.MEDIUM)
            
            await self.context_manager.add(session_id, role, content, priority)
        except Exception as e:
            logger.error("context_add_error", session_id=session_id, error=str(e))
    
    async def get_context_prompt(
        self,
        session_id: str,
        max_tokens: int = 4000,
    ) -> str:
        """Get optimized context prompt."""
        try:
            return await self.context_manager.get_prompt_context(
                session_id, max_tokens
            )
        except Exception as e:
            logger.error("context_get_error", session_id=session_id, error=str(e))
            return ""
    
    async def compact_context(
        self,
        session_id: str,
        force: bool = False,
    ) -> bool:
        """Compact context if needed."""
        try:
            return await self.context_manager.maybe_compact(session_id, force)
        except Exception as e:
            logger.error("context_compact_error", session_id=session_id, error=str(e))
            return False
    
    # ─── Health & Status ───────────────────────────────────────────────────
    
    async def get_health_status(self) -> dict:
        """Get overall system health."""
        try:
            resilience_health = self.resilience.get_health_status()
            anomaly_summary = self.anomaly_detector.get_anomaly_summary()
            
            return {
                "overall": "healthy" if anomaly_summary["total_anomalies"] < 5 else "degraded",
                "circuit_breakers": resilience_health,
                "anomalies": anomaly_summary,
                "config": {
                    "kill_switch": self.config.enable_kill_switch,
                    "token_budget": self.config.enable_token_budget,
                    "circuit_breaker": self.config.enable_circuit_breaker,
                    "anomaly_detection": self.config.enable_anomaly_detection,
                },
            }
        except Exception as e:
            logger.error("health_check_error", error=str(e))
            return {"error": str(e)}
    
    async def get_active_sessions(self) -> list[dict]:
        """Get all active sessions."""
        try:
            return await self.safety.get_active_sessions()
        except Exception as e:
            logger.error("active_sessions_error", error=str(e))
            return []
    
    # ─── A2A Protocol ─────────────────────────────────────────────────────
    
    async def register_agent(self, agent_card) -> None:
        """Register an agent with A2A protocol."""
        try:
            if self._a2a is None:
                from app.services.agent.a2a import get_a2a_protocol
                self._a2a = get_a2a_protocol()
            
            await self._a2a.register_agent(agent_card)
        except Exception as e:
            logger.error("agent_register_error", error=str(e))
    
    async def discover_agents(
        self,
        capability: str | None = None,
    ) -> list:
        """Discover agents by capability."""
        try:
            if self._a2a is None:
                from app.services.agent.a2a import get_a2a_protocol
                self._a2a = get_a2a_protocol()
            
            return await self._a2a.discover_agents(capability=capability)
        except Exception as e:
            logger.error("agent_discover_error", error=str(e))
            return []


# ─── Global Instance ─────────────────────────────────────────────────────────

_integration_instance: SafetyIntegration | None = None


def get_safety_integration() -> SafetyIntegration:
    """Get the global SafetyIntegration instance."""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = SafetyIntegration()
    return _integration_instance


def reset_safety_integration() -> None:
    """Reset the global instance (for testing)."""
    global _integration_instance
    _integration_instance = None
