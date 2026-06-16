"""Agent Safety Layer - Kill switch, token budget, and runtime guards.

This module provides production-grade safety mechanisms for the agent system:
- Kill switch: Immediate abort of runaway or problematic agent sessions
- Token budget: Hard enforcement of token usage limits
- Runtime guards: Protection against loops, excessive API calls, cost overruns
- Human-in-the-loop: Approval gates for critical actions

Usage:
    from app.services.agent.safety import AgentSafety, get_agent_safety
    
    safety = get_agent_safety()
    
    # Check if agent can continue
    can_continue = await safety.can_continue(session_id)
    
    # Abort a runaway session
    await safety.abort_session(session_id, reason="user_requested")
    
    # Track token usage
    await safety.track_tokens(session_id, input_tokens=100, output_tokens=50)
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.cache import cache
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("agent_safety")


class AbortReason(Enum):
    """Reasons for agent session abortion."""
    USER_REQUESTED = "user_requested"
    TIMEOUT = "timeout"
    TOKEN_BUDGET_EXCEEDED = "token_budget_exceeded"
    LOOP_DETECTED = "loop_detected"
    COST_THRESHOLD_EXCEEDED = "cost_threshold_exceeded"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    ANOMALY_DETECTED = "anomaly_detected"
    SYSTEM_SHUTDOWN = "system_shutdown"
    HUMAN_APPROVAL_DENIED = "human_approval_denied"


@dataclass
class TokenBudget:
    """Token budget configuration and tracking."""
    max_input_tokens: int = 8000
    max_output_tokens: int = 2000
    max_total_tokens: int = 10000
    
    # Token prices (USD per 1M tokens) - approximate
    input_price_per_m: float = 2.50   # GPT-4o input
    output_price_per_m: float = 10.00  # GPT-4o output
    
    # Accumulated usage
    input_tokens_used: int = 0
    output_tokens_used: int = 0
    
    @property
    def total_tokens_used(self) -> int:
        return self.input_tokens_used + self.output_tokens_used
    
    @property
    def estimated_cost_usd(self) -> float:
        """Calculate estimated cost in USD."""
        input_cost = (self.input_tokens_used / 1_000_000) * self.input_price_per_m
        output_cost = (self.output_tokens_used / 1_000_000) * self.output_price_per_m
        return input_cost + output_cost
    
    def can_continue(self) -> tuple[bool, str]:
        """Check if agent can continue within budget."""
        if self.total_tokens_used >= self.max_total_tokens:
            return False, f"Total token limit exceeded: {self.total_tokens_used}/{self.max_total_tokens}"
        if self.input_tokens_used >= self.max_input_tokens:
            return False, f"Input token limit exceeded: {self.input_tokens_used}/{self.max_input_tokens}"
        if self.output_tokens_used >= self.max_output_tokens:
            return False, f"Output token limit exceeded: {self.output_tokens_used}/{self.max_output_tokens}"
        return True, "OK"
    
    def add_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Add token usage."""
        self.input_tokens_used += input_tokens
        self.output_tokens_used += output_tokens


@dataclass
class SafetyConfig:
    """Safety configuration for agent execution."""
    # Kill switch
    enable_kill_switch: bool = True
    
    # Token budget
    enforce_hard_token_budget: bool = True
    default_max_tokens: int = 10000
    
    # Timeout
    max_execution_seconds: int = 120
    max_node_execution_seconds: int = 30
    
    # Loop detection
    enable_loop_detection: bool = True
    max_consecutive_similar_calls: int = 3
    similarity_threshold: float = 0.85
    
    # Cost controls
    max_cost_per_session_usd: float = 2.00
    max_cost_per_day_usd: float = 50.00
    
    # Rate limiting
    max_requests_per_minute: int = 30
    max_tool_calls_per_session: int = 50
    
    # Human-in-the-loop
    enable_human_approval: bool = False
    approval_threshold: float = 0.8  # Confidence threshold for auto-approve


@dataclass
class SessionState:
    """Runtime state of an agent session."""
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    status: str = "active"  # active, paused, aborted, completed
    abort_reason: AbortReason | None = None
    
    # Execution tracking
    current_node: str | None = None
    execution_count: int = 0
    tool_call_count: int = 0
    
    # Token budget
    token_budget: TokenBudget = field(default_factory=TokenBudget)
    
    # Loop detection
    recent_calls: list[dict] = field(default_factory=list)
    consecutive_similar: int = 0
    
    # Approval state
    pending_approval: bool = False
    approval_requested_at: float | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "status": self.status,
            "abort_reason": self.abort_reason.value if self.abort_reason else None,
            "current_node": self.current_node,
            "execution_count": self.execution_count,
            "tool_call_count": self.tool_call_count,
            "token_budget": {
                "input_tokens_used": self.token_budget.input_tokens_used,
                "output_tokens_used": self.token_budget.output_tokens_used,
                "total_tokens_used": self.token_budget.total_tokens_used,
                "estimated_cost_usd": self.token_budget.estimated_cost_usd,
            },
            "consecutive_similar": self.consecutive_similar,
            "pending_approval": self.pending_approval,
        }


class AgentSafety:
    """
    Production-grade safety layer for agent execution.
    
    Provides:
    - Kill switch with immediate abort capability
    - Hard token budget enforcement
    - Loop detection and prevention
    - Cost tracking and limits
    - Runtime guards and checkpoints
    - Human-in-the-loop approval flow
    """
    
    def __init__(self, config: SafetyConfig | None = None):
        self.config = config or SafetyConfig()
        self._sessions: dict[str, SessionState] = {}
        self._global_abort: bool = False
        self._abort_lock = asyncio.Lock()
        
        # Cost tracking
        self._daily_cost_cache: dict[str, float] = {}
        self._daily_cost_date: str = ""
    
    async def get_session(self, session_id: str) -> SessionState | None:
        """Get or create session state."""
        if session_id not in self._sessions:
            # Try to load from cache
            cached = await cache.get(f"safety:session:{session_id}")
            if cached:
                if cached.get("abort_reason"):
                    cached["abort_reason"] = AbortReason(cached["abort_reason"])
                if cached.get("token_budget") and isinstance(cached["token_budget"], dict):
                    budget_dict = cached["token_budget"]
                    budget = TokenBudget()
                    budget.input_tokens_used = budget_dict.get("input_tokens_used", 0)
                    budget.output_tokens_used = budget_dict.get("output_tokens_used", 0)
                    cached["token_budget"] = budget
                session = SessionState(**cached)
                self._sessions[session_id] = session
            else:
                session = SessionState(session_id=session_id)
                self._sessions[session_id] = session
        
        return self._sessions.get(session_id)
    
    async def _persist_session(self, session: SessionState) -> None:
        """Persist session state to cache."""
        session.last_activity = time.time()
        await cache.set(
            f"safety:session:{session.session_id}",
            session.to_dict(),
            ttl=3600  # 1 hour TTL
        )
    
    # ─── Kill Switch ───────────────────────────────────────────────────────────
    
    async def abort_session(
        self,
        session_id: str,
        reason: AbortReason,
        message: str = ""
    ) -> bool:
        """
        Immediately abort an agent session.
        
        This is the kill switch - it stops all agent execution for the session.
        """
        async with self._abort_lock:
            session = await self.get_session(session_id)
            if not session:
                logger.warning("abort_session_not_found", session_id=session_id)
                return False
            
            session.status = "aborted"
            session.abort_reason = reason
            
            # Persist state
            await self._persist_session(session)
            
            # Remove from active sessions
            if session_id in self._sessions:
                del self._sessions[session_id]
            
            logger.warning(
                "agent_session_aborted",
                session_id=session_id,
                reason=reason.value,
                message=message,
            )
            
            return True
    
    async def abort_all_sessions(self, reason: AbortReason, message: str = "") -> int:
        """
        Abort all active agent sessions.
        
        Use for system-wide shutdown or emergency stop.
        """
        async with self._abort_lock:
            count = 0
            for session_id in list(self._sessions.keys()):
                session = self._sessions[session_id]
                if session.status == "active":
                    session.status = "aborted"
                    session.abort_reason = reason
                    await self._persist_session(session)
                    count += 1
            
            self._sessions.clear()
            self._global_abort = True
            
            logger.warning(
                "all_agent_sessions_aborted",
                count=count,
                reason=reason.value,
                message=message,
            )
            
            return count
    
    async def is_aborted(self, session_id: str) -> bool:
        """Check if a session has been aborted."""
        if self._global_abort:
            return True
        
        session = await self.get_session(session_id)
        if not session:
            return False
        
        return session.status == "aborted"
    
    async def can_continue(self, session_id: str) -> tuple[bool, str]:
        """
        Check if an agent can continue execution.
        
        Returns (can_continue, reason)
        """
        if self._global_abort:
            return False, "System-wide abort is active"
        
        session = await self.get_session(session_id)
        if not session:
            return False, "Session not found"
        
        if session.status == "aborted":
            return False, f"Session aborted: {session.abort_reason.value}"
        
        if session.status == "completed":
            return False, "Session already completed"
        
        # Check execution time
        elapsed = time.time() - session.created_at
        if elapsed > self.config.max_execution_seconds:
            await self.abort_session(session_id, AbortReason.TIMEOUT, "Execution timeout")
            return False, "Execution timeout exceeded"
        
        # Check token budget
        if self.config.enforce_hard_token_budget:
            can_cont, budget_reason = session.token_budget.can_continue()
            if not can_cont:
                await self.abort_session(
                    session_id,
                    AbortReason.TOKEN_BUDGET_EXCEEDED,
                    budget_reason
                )
                return False, budget_reason
        
        # Check cost limits
        estimated_cost = session.token_budget.estimated_cost_usd
        if estimated_cost > self.config.max_cost_per_session_usd:
            await self.abort_session(
                session_id,
                AbortReason.COST_THRESHOLD_EXCEEDED,
                f"Cost limit exceeded: ${estimated_cost:.4f}"
            )
            return False, f"Cost limit exceeded: ${estimated_cost:.4f}"
        
        # Check tool call limits
        if session.tool_call_count >= self.config.max_tool_calls_per_session:
            return False, f"Tool call limit exceeded: {session.tool_call_count}"
        
        return True, "OK"
    
    # ─── Token Budget ─────────────────────────────────────────────────────────
    
    async def track_tokens(
        self,
        session_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> TokenBudget:
        """
        Track token usage for a session.
        
        Returns updated token budget.
        """
        session = await self.get_session(session_id)
        if session:
            session.token_budget.add_usage(input_tokens, output_tokens)
            await self._persist_session(session)
            
            # Update Prometheus metrics
            try:
                from app.core.metrics import (
                    QUERY_INPUT_TOKENS, QUERY_OUTPUT_TOKENS, AGENT_COST_USD
                )
                model = settings.OPENAI_MODEL if settings.LLM_PROVIDER == "openai" else "claude"
                QUERY_INPUT_TOKENS.labels(model=model).observe(input_tokens)
                QUERY_OUTPUT_TOKENS.labels(model=model).observe(output_tokens)
                AGENT_COST_USD.labels(session_id=session_id).inc(session.token_budget.estimated_cost_usd)
            except ImportError:
                pass
        
        return session.token_budget if session else TokenBudget()
    
    async def get_token_budget(self, session_id: str) -> TokenBudget:
        """Get current token budget for a session."""
        session = await self.get_session(session_id)
        return session.token_budget if session else TokenBudget()
    
    # ─── Loop Detection ───────────────────────────────────────────────────────
    
    def _compute_similarity(self, call1: dict, call2: dict) -> float:
        """Compute similarity between two agent calls."""
        # Hash-based similarity for tool calls
        if call1.get("tool_name") != call2.get("tool_name"):
            return 0.0
        
        # Compare arguments
        args1 = str(call1.get("arguments", {}))
        args2 = str(call2.get("arguments", {}))
        
        # Simple Jaccard similarity on character n-grams
        def get_ngrams(s: str, n: int = 3) -> set:
            return set(s[i:i+n] for i in range(len(s) - n + 1))
        
        ngrams1 = get_ngrams(args1)
        ngrams2 = get_ngrams(args2)
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = len(ngrams1 & ngrams2)
        union = len(ngrams1 | ngrams2)
        
        return intersection / union if union > 0 else 0.0
    
    async def check_loop(
        self,
        session_id: str,
        tool_name: str,
        arguments: dict,
    ) -> tuple[bool, str]:
        """
        Check if the agent is entering a loop.
        
        Returns (is_loop, reason)
        """
        if not self.config.enable_loop_detection:
            return False, ""
        
        session = await self.get_session(session_id)
        if not session:
            return False, ""
        
        current_call = {
            "tool_name": tool_name,
            "arguments": arguments,
            "timestamp": time.time(),
        }
        
        # Add to recent calls (keep last 10)
        session.recent_calls.append(current_call)
        session.recent_calls = session.recent_calls[-10:]
        
        # Check for similar recent calls
        similar_count = 0
        for recent in session.recent_calls[:-1]:
            if self._compute_similarity(current_call, recent) >= self.config.similarity_threshold:
                similar_count += 1
        
        session.consecutive_similar = similar_count
        
        if similar_count >= self.config.max_consecutive_similar_calls:
            await self.abort_session(
                session_id,
                AbortReason.LOOP_DETECTED,
                f"Loop detected: {tool_name} called {similar_count + 1} times with similar args"
            )
            return True, f"Loop detected: {tool_name} called too many times with similar arguments"
        
        return False, ""
    
    # ─── Tool Call Tracking ───────────────────────────────────────────────────
    
    async def track_tool_call(
        self,
        session_id: str,
        tool_name: str,
        arguments: dict | None = None,
    ) -> tuple[bool, str]:
        """
        Track a tool call and check limits.
        
        Returns (allowed, reason)
        """
        session = await self.get_session(session_id)
        if not session:
            return True, ""
        
        session.tool_call_count += 1
        await self._persist_session(session)
        
        # Check loop
        if arguments:
            is_loop, loop_reason = await self.check_loop(session_id, tool_name, arguments)
            if is_loop:
                return False, loop_reason
        
        # Check tool call limit
        if session.tool_call_count >= self.config.max_tool_calls_per_session:
            return False, f"Tool call limit exceeded: {session.tool_call_count}"
        
        return True, "OK"
    
    # ─── Human-in-the-Loop ───────────────────────────────────────────────────
    
    async def request_approval(
        self,
        session_id: str,
        action: str,
        details: dict,
        confidence: float = 1.0,
    ) -> str:
        """
        Request human approval for an action.
        
        Returns approval token if auto-approved or approval request created.
        """
        session = await self.get_session(session_id)
        if not session:
            return ""
        
        # Auto-approve if confidence above threshold and feature enabled
        if (self.config.enable_human_approval and 
            confidence >= self.config.approval_threshold):
            logger.info(
                "action_auto_approved",
                session_id=session_id,
                action=action,
                confidence=confidence,
            )
            return "auto_approved"
        
        # Create approval request
        approval_token = hashlib.sha256(
            f"{session_id}:{action}:{time.time()}".encode()
        ).hexdigest()[:16]
        
        session.pending_approval = True
        session.approval_requested_at = time.time()
        await self._persist_session(session)
        
        # Store approval request
        await cache.set(
            f"approval:{approval_token}",
            {
                "session_id": session_id,
                "action": action,
                "details": details,
                "confidence": confidence,
                "requested_at": time.time(),
                "status": "pending",
            },
            ttl=300  # 5 minutes TTL
        )
        
        logger.info(
            "approval_requested",
            session_id=session_id,
            action=action,
            approval_token=approval_token,
        )
        
        return approval_token
    
    async def approve_action(
        self,
        approval_token: str,
        approver_id: str,
        approved: bool,
        comments: str = "",
    ) -> tuple[bool, str]:
        """
        Process human approval decision.
        
        Returns (success, message)
        """
        request = await cache.get(f"approval:{approval_token}")
        if not request:
            return False, "Approval request not found"
        
        if request["status"] != "pending":
            return False, f"Request already processed: {request['status']}"
        
        if approved:
            request["status"] = "approved"
            request["approved_by"] = approver_id
            request["approved_at"] = time.time()
            request["comments"] = comments
            
            # Update session
            session = await self.get_session(request["session_id"])
            if session:
                session.pending_approval = False
                await self._persist_session(session)
            
            logger.info(
                "action_approved",
                approval_token=approval_token,
                approver_id=approver_id,
            )
            
            return True, "Action approved"
        else:
            # Deny the action
            request["status"] = "denied"
            request["denied_by"] = approver_id
            request["denied_at"] = time.time()
            request["comments"] = comments
            
            # Abort session
            session = await self.get_session(request["session_id"])
            if session:
                await self.abort_session(
                    session.session_id,
                    AbortReason.HUMAN_APPROVAL_DENIED,
                    f"Denied by {approver_id}: {comments}"
                )
            
            logger.warning(
                "action_denied",
                approval_token=approval_token,
                denied_by=approver_id,
                comments=comments,
            )
            
            return True, "Action denied and session aborted"
    
    async def get_pending_approvals(self, approver_id: str | None = None) -> list[dict]:
        """Get list of pending approval requests."""
        keys = await cache.keys("approval:*")
        pending = []
        
        for key in keys:
            request = await cache.get(key)
            if request and request.get("status") == "pending":
                pending.append({
                    "token": key.replace("approval:", ""),
                    **request
                })
        
        return pending
    
    # ─── Cost Tracking ────────────────────────────────────────────────────────
    
    async def track_cost(
        self,
        session_id: str,
        cost_usd: float,
    ) -> tuple[bool, str]:
        """
        Track cost for a session and check daily limit.
        
        Returns (allowed, reason)
        """
        # Update daily cost cache
        today = time.strftime("%Y-%m-%d")
        
        if today != self._daily_cost_date:
            self._daily_cost_cache = {}
            self._daily_cost_date = today
        
        self._daily_cost_cache[session_id] = (
            self._daily_cost_cache.get(session_id, 0) + cost_usd
        )
        
        # Check daily limit
        total_today = sum(self._daily_cost_cache.values())
        if total_today > self.config.max_cost_per_day_usd:
            logger.error(
                "daily_cost_limit_exceeded",
                total_usd=total_today,
                limit_usd=self.config.max_cost_per_day_usd,
            )
            return False, f"Daily cost limit exceeded: ${total_today:.2f}"
        
        return True, "OK"
    
    # ─── Node Checkpoint ──────────────────────────────────────────────────────
    
    async def checkpoint(
        self,
        session_id: str,
        node_name: str,
        state_snapshot: dict,
    ) -> str:
        """
        Create a checkpoint for node execution.
        
        Allows recovery from partial execution.
        """
        checkpoint_id = hashlib.sha256(
            f"{session_id}:{node_name}:{time.time()}".encode()
        ).hexdigest()[:16]
        
        await cache.set(
            f"checkpoint:{checkpoint_id}",
            {
                "session_id": session_id,
                "node_name": node_name,
                "state_snapshot": state_snapshot,
                "created_at": time.time(),
            },
            ttl=1800  # 30 minutes
        )
        
        session = await self.get_session(session_id)
        if session:
            session.current_node = node_name
            session.execution_count += 1
            await self._persist_session(session)
        
        return checkpoint_id
    
    async def get_checkpoint(self, checkpoint_id: str) -> dict | None:
        """Get a checkpoint by ID."""
        return await cache.get(f"checkpoint:{checkpoint_id}")
    
    # ─── Status & Health ─────────────────────────────────────────────────────
    
    async def get_active_sessions(self) -> list[dict]:
        """Get all active session states."""
        return [s.to_dict() for s in self._sessions.values() if s.status == "active"]
    
    async def get_session_status(self, session_id: str) -> dict | None:
        """Get detailed status of a session."""
        session = await self.get_session(session_id)
        return session.to_dict() if session else None


# ─── Global Instance ─────────────────────────────────────────────────────────

_safety_instance: AgentSafety | None = None


def get_agent_safety() -> AgentSafety:
    """Get the global AgentSafety instance."""
    global _safety_instance
    if _safety_instance is None:
        _safety_instance = AgentSafety()
    return _safety_instance


def reset_agent_safety() -> None:
    """Reset the global instance (for testing)."""
    global _safety_instance
    _safety_instance = None


# ─── Import Tool Safety Components ─────────────────────────────────────────────

from app.services.agent.safety.tool_safety import (
    ToolSafety,
    ToolSafetyConfig,
    InputValidator,
    PIIDetector,
    OutputFilter,
    get_tool_safety,
    reset_tool_safety,
)

# ─── Import Resilience Components ──────────────────────────────────────────────

from app.services.agent.safety.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    GracefulDegradation,
    RateLimiter,
    DeadLetterQueue,
    FallbackChain,
    get_resilience,
    get_circuit_breaker,
    reset_resilience,
)

# ─── Import Anomaly Detection Components ───────────────────────────────────────

from app.services.agent.safety.anomaly_detector import (
    AnomalyDetector,
    AnomalyConfig,
    Anomaly,
    AnomalyType,
    AnomalySeverity,
    get_anomaly_detector,
    reset_anomaly_detector,
)
