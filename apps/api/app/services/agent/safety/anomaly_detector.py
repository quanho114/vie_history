"""Anomaly Detection for Agentic AI - Runaway Loop Prevention and Behavioral Analysis.

This module provides production-grade anomaly detection:
- Runaway loop detection and prevention
- Behavioral pattern analysis
- Latency anomaly detection
- Cost anomaly detection
- Output quality monitoring
- Automatic response to anomalies

Usage:
    from app.services.agent.safety import AnomalyDetector, get_anomaly_detector
    
    detector = get_anomaly_detector()
    
    # Record agent behavior
    await detector.record_step(session_id, node="retrieval", latency_ms=150)
    
    # Check for anomalies
    anomaly = await detector.check_anomalies(session_id)
    if anomaly:
        await detector.respond_to_anomaly(anomaly)
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.cache import cache
from app.core.logging import get_logger

logger = get_logger("anomaly_detector")


class AnomalyType(Enum):
    """Types of anomalies that can be detected."""
    RUNAWAY_LOOP = "runaway_loop"
    EXCESSIVE_LATENCY = "excessive_latency"
    COST_SPIKE = "cost_spike"
    QUALITY_DROPOFF = "quality_dropoff"
    OUTPUT_REPETITION = "output_repetition"
    MEMORY_LEAK = "memory_leak"
    TOKEN_EXPLOSION = "token_explosion"
    STUCK_STATE = "stuck_state"
    UNUSUAL_PATTERN = "unusual_pattern"


class AnomalySeverity(Enum):
    """Severity levels for anomalies."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AnomalyConfig:
    """Configuration for anomaly detection."""
    # Loop detection
    max_loop_iterations: int = 5
    loop_similarity_threshold: float = 0.85
    
    # Latency thresholds (ms)
    max_single_step_latency_ms: int = 30000  # 30 seconds
    max_average_latency_ms: int = 15000  # 15 seconds average
    latency_std_dev_multiplier: float = 3.0  # 3 standard deviations
    
    # Cost thresholds (USD)
    max_cost_per_step: float = 0.50
    max_cost_per_session: float = 2.00
    cost_spike_threshold: float = 2.0  # 2x normal
    
    # Output quality
    min_quality_score: float = 0.3
    quality_dropoff_threshold: float = 0.4  # 40% drop from baseline
    
    # Memory monitoring
    max_memory_growth_mb: int = 500  # 500 MB
    memory_growth_rate_threshold: float = 1.5  # 50% growth per step
    
    # Token limits
    max_tokens_per_step: int = 2000
    max_total_tokens: int = 10000
    
    # Behavioral
    max_repeated_output_chars: int = 500  # Repeated output threshold
    repetition_threshold: float = 0.7  # 70% repetition
    
    # Response thresholds
    auto_respond_threshold: AnomalySeverity = AnomalySeverity.ERROR


@dataclass
class Anomaly:
    """Detected anomaly."""
    id: str
    type: AnomalyType
    severity: AnomalySeverity
    session_id: str
    message: str
    details: dict
    detected_at: float
    response_taken: str | None = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "severity": self.severity.value,
            "session_id": self.session_id,
            "message": self.message,
            "details": self.details,
            "detected_at": self.detected_at,
            "response_taken": self.response_taken,
        }


@dataclass
class SessionMetrics:
    """Metrics tracked for a session."""
    session_id: str
    started_at: float = field(default_factory=time.time)
    
    # Step tracking
    steps: list[dict] = field(default_factory=list)
    node_visits: dict[str, int] = field(default_factory=dict)
    
    # Latency tracking
    latency_history: list[float] = field(default_factory=list)  # ms
    
    # Cost tracking
    cost_history: list[float] = field(default_factory=list)  # USD
    
    # Token tracking
    token_usage: list[int] = field(default_factory=list)
    
    # Quality tracking
    quality_scores: list[float] = field(default_factory=list)
    
    # Output tracking
    output_hashes: list[str] = field(default_factory=list)
    
    # Memory tracking
    memory_usage_mb: list[float] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "total_steps": len(self.steps),
            "node_visits": self.node_visits,
            "avg_latency_ms": sum(self.latency_history) / max(len(self.latency_history), 1),
            "total_cost_usd": sum(self.cost_history),
            "total_tokens": sum(self.token_usage),
            "avg_quality": sum(self.quality_scores) / max(len(self.quality_scores), 1),
        }


class LoopDetector:
    """
    Detects runaway loops in agent execution.
    
    Uses multiple strategies:
    - State hash tracking
    - Output similarity
    - Node visit frequency
    - Tool call patterns
    """
    
    def __init__(self, config: AnomalyConfig):
        self.config = config
        self._state_hashes: dict[str, list[str]] = {}
    
    def _compute_state_hash(self, state: dict) -> str:
        """Compute hash of agent state."""
        # Extract relevant parts for hashing
        relevant = {
            "query": state.get("query", ""),
            "plan": tuple(state.get("plan", [])),
            "retrieved_chunks": len(state.get("retrieved_chunks", [])),
            "current_step": state.get("current_step", 0),
        }
        
        state_str = str(relevant)
        return hashlib.sha256(state_str.encode()).hexdigest()[:16]
    
    def _compute_output_similarity(self, outputs: list[str]) -> float:
        """Compute similarity between recent outputs."""
        if len(outputs) < 2:
            return 0.0
        
        # Simple character n-gram similarity
        def get_ngrams(s: str, n: int = 5) -> set:
            s = s.lower()
            return set(s[i:i+n] for i in range(max(0, len(s) - n + 1)))
        
        # Compare last two outputs
        last = get_ngrams(outputs[-1])
        second_last = get_ngrams(outputs[-2]) if len(outputs) > 1 else set()
        
        if not last or not second_last:
            return 0.0
        
        intersection = len(last & second_last)
        union = len(last | second_last)
        
        return intersection / union if union > 0 else 0.0
    
    def check_loop(
        self,
        session_id: str,
        state: dict,
        output: str | None = None,
    ) -> Anomaly | None:
        """Check if agent is in a loop."""
        # Initialize session tracking
        if session_id not in self._state_hashes:
            self._state_hashes[session_id] = []
        
        # Compute current state hash
        current_hash = self._compute_state_hash(state)
        state_hashes = self._state_hashes[session_id]
        
        # Count occurrences of current hash
        hash_count = sum(1 for h in state_hashes if h == current_hash)
        
        # Check if we've seen this state before
        if hash_count >= self.config.max_loop_iterations - 1:
            # Potential loop detected
            recent_hashes = state_hashes[-self.config.max_loop_iterations:]
            if len(set(recent_hashes)) <= 2:
                return Anomaly(
                    id=hashlib.md5(f"{session_id}:loop:{time.time()}".encode()).hexdigest()[:16],
                    type=AnomalyType.RUNAWAY_LOOP,
                    severity=AnomalySeverity.CRITICAL,
                    session_id=session_id,
                    message=f"Runaway loop detected: same state repeated {hash_count + 1} times",
                    details={
                        "state_hash": current_hash,
                        "repeat_count": hash_count + 1,
                        "recent_states": len(set(recent_hashes)),
                    },
                    detected_at=time.time(),
                )
        
        # Update state hashes
        state_hashes.append(current_hash)
        
        # Keep only recent hashes
        max_history = self.config.max_loop_iterations * 2
        self._state_hashes[session_id] = state_hashes[-max_history:]
        
        # Check output repetition
        if output:
            # Compute output hash
            output_hash = hashlib.sha256(output.encode()).hexdigest()[:16]
            metrics = self._get_metrics(session_id)
            metrics.output_hashes.append(output_hash)
            
            # Check for repetition
            if len(metrics.output_hashes) >= 3:
                similarity = self._compute_output_similarity(
                    [h[:8] for h in metrics.output_hashes[-3:]]
                )
                
                if similarity >= self.config.repetition_threshold:
                    return Anomaly(
                        id=hashlib.md5(f"{session_id}:repetition:{time.time()}".encode()).hexdigest()[:16],
                        type=AnomalyType.OUTPUT_REPETITION,
                        severity=AnomalySeverity.WARNING,
                        session_id=session_id,
                        message=f"Output repetition detected: {similarity:.1%} similarity",
                        details={
                            "similarity": similarity,
                            "recent_outputs": len(metrics.output_hashes),
                        },
                        detected_at=time.time(),
                    )
        
        return None
    
    def _get_metrics(self, session_id: str) -> SessionMetrics:
        """Get or create metrics for session."""
        # This would be managed by AnomalyDetector
        return SessionMetrics(session_id=session_id)


class LatencyAnalyzer:
    """
    Analyzes latency patterns to detect anomalies.
    
    Detects:
    - Single step timeout
    - Sustained high latency
    - Sudden latency spikes
    """
    
    def __init__(self, config: AnomalyConfig):
        self.config = config
        self._baseline_latency: dict[str, float] = {}
    
    def analyze_latency(
        self,
        session_id: str,
        step_latency_ms: float,
        node_name: str | None = None,
    ) -> Anomaly | None:
        """Analyze latency for anomalies."""
        # Check single step timeout
        if step_latency_ms > self.config.max_single_step_latency_ms:
            return Anomaly(
                id=hashlib.md5(f"{session_id}:latency:{time.time()}".encode()).hexdigest()[:16],
                type=AnomalyType.EXCESSIVE_LATENCY,
                severity=AnomalySeverity.ERROR,
                session_id=session_id,
                message=f"Step took {step_latency_ms:.0f}ms (max: {self.config.max_single_step_latency_ms}ms)",
                details={
                    "step_latency_ms": step_latency_ms,
                    "node": node_name,
                    "threshold_ms": self.config.max_single_step_latency_ms,
                },
                detected_at=time.time(),
            )
        
        # Update baseline (exponential moving average)
        if session_id in self._baseline_latency:
            alpha = 0.2
            self._baseline_latency[session_id] = (
                alpha * step_latency_ms +
                (1 - alpha) * self._baseline_latency[session_id]
            )
        else:
            self._baseline_latency[session_id] = step_latency_ms
        
        # Check for spike (2x baseline)
        if step_latency_ms > self._baseline_latency[session_id] * self.config.cost_spike_threshold:
            return Anomaly(
                id=hashlib.md5(f"{session_id}:spike:{time.time()}".encode()).hexdigest()[:16],
                type=AnomalyType.EXCESSIVE_LATENCY,
                severity=AnomalySeverity.WARNING,
                session_id=session_id,
                message=f"Latency spike: {step_latency_ms:.0f}ms (baseline: {self._baseline_latency[session_id]:.0f}ms)",
                details={
                    "step_latency_ms": step_latency_ms,
                    "baseline_ms": self._baseline_latency[session_id],
                    "spike_ratio": step_latency_ms / self._baseline_latency[session_id],
                    "node": node_name,
                },
                detected_at=time.time(),
            )
        
        return None


class CostAnalyzer:
    """
    Analyzes cost patterns to detect anomalies.
    
    Detects:
    - Cost spikes
    - Excessive spending
    - Budget overruns
    """
    
    def __init__(self, config: AnomalyConfig):
        self.config = config
        self._baseline_cost: dict[str, float] = {}
    
    def analyze_cost(
        self,
        session_id: str,
        step_cost: float,
        total_cost: float,
    ) -> Anomaly | None:
        """Analyze cost for anomalies."""
        # Check single step cost
        if step_cost > self.config.max_cost_per_step:
            return Anomaly(
                id=hashlib.md5(f"{session_id}:cost:{time.time()}".encode()).hexdigest()[:16],
                type=AnomalyType.COST_SPIKE,
                severity=AnomalySeverity.ERROR,
                session_id=session_id,
                message=f"Step cost ${step_cost:.4f} exceeds max ${self.config.max_cost_per_step:.4f}",
                details={
                    "step_cost": step_cost,
                    "total_cost": total_cost,
                    "threshold": self.config.max_cost_per_step,
                },
                detected_at=time.time(),
            )
        
        # Check total cost
        if total_cost > self.config.max_cost_per_session:
            return Anomaly(
                id=hashlib.md5(f"{session_id}:budget:{time.time()}".encode()).hexdigest()[:16],
                type=AnomalyType.COST_SPIKE,
                severity=AnomalySeverity.CRITICAL,
                session_id=session_id,
                message=f"Session cost ${total_cost:.4f} exceeds budget ${self.config.max_cost_per_session:.4f}",
                details={
                    "total_cost": total_cost,
                    "budget": self.config.max_cost_per_session,
                },
                detected_at=time.time(),
            )
        
        # Update baseline
        if session_id in self._baseline_cost:
            alpha = 0.2
            self._baseline_cost[session_id] = (
                alpha * step_cost +
                (1 - alpha) * self._baseline_cost[session_id]
            )
        else:
            self._baseline_cost[session_id] = step_cost
        
        # Check for spike
        if step_cost > self._baseline_cost[session_id] * 3:
            return Anomaly(
                id=hashlib.md5(f"{session_id}:costspike:{time.time()}".encode()).hexdigest()[:16],
                type=AnomalyType.COST_SPIKE,
                severity=AnomalySeverity.WARNING,
                session_id=session_id,
                message=f"Cost spike: ${step_cost:.4f} (baseline: ${self._baseline_cost[session_id]:.4f})",
                details={
                    "step_cost": step_cost,
                    "baseline_cost": self._baseline_cost[session_id],
                },
                detected_at=time.time(),
            )
        
        return None


class QualityMonitor:
    """
    Monitors output quality for anomalies.
    
    Detects:
    - Quality dropoff
    - Repeated low-quality outputs
    - Hallucination indicators
    """
    
    def __init__(self, config: AnomalyConfig):
        self.config = config
        self._baseline_quality: dict[str, float] = {}
    
    def analyze_quality(
        self,
        session_id: str,
        quality_score: float,
        output: str | None = None,
    ) -> Anomaly | None:
        """Analyze quality for anomalies."""
        # Initialize baseline
        if session_id not in self._baseline_quality:
            self._baseline_quality[session_id] = quality_score
        
        # Check absolute minimum
        if quality_score < self.config.min_quality_score:
            return Anomaly(
                id=hashlib.md5(f"{session_id}:quality:{time.time()}".encode()).hexdigest()[:16],
                type=AnomalyType.QUALITY_DROPOFF,
                severity=AnomalySeverity.ERROR,
                session_id=session_id,
                message=f"Quality score {quality_score:.2f} below minimum {self.config.min_quality_score:.2f}",
                details={
                    "quality_score": quality_score,
                    "baseline": self._baseline_quality[session_id],
                    "threshold": self.config.min_quality_score,
                },
                detected_at=time.time(),
            )
        
        # Check relative dropoff
        baseline = self._baseline_quality[session_id]
        if baseline > 0 and quality_score < baseline * (1 - self.config.quality_dropoff_threshold):
            return Anomaly(
                id=hashlib.md5(f"{session_id}:dropoff:{time.time()}".encode()).hexdigest()[:16],
                type=AnomalyType.QUALITY_DROPOFF,
                severity=AnomalySeverity.WARNING,
                session_id=session_id,
                message=f"Quality dropoff: {quality_score:.2f} vs baseline {baseline:.2f}",
                details={
                    "quality_score": quality_score,
                    "baseline": baseline,
                    "dropoff_ratio": quality_score / baseline if baseline > 0 else 0,
                },
                detected_at=time.time(),
            )
        
        # Update baseline (slow EMA)
        alpha = 0.05
        self._baseline_quality[session_id] = (
            alpha * quality_score +
            (1 - alpha) * self._baseline_quality[session_id]
        )
        
        return None


class TokenMonitor:
    """
    Monitors token usage for anomalies.
    
    Detects:
    - Token explosion
    - Excessive context growth
    """
    
    def __init__(self, config: AnomalyConfig):
        self.config = config
        self._baseline_tokens: dict[str, float] = {}
    
    def analyze_tokens(
        self,
        session_id: str,
        tokens_used: int,
        total_tokens: int,
    ) -> Anomaly | None:
        """Analyze token usage for anomalies."""
        # Check per-step limit
        if tokens_used > self.config.max_tokens_per_step:
            return Anomaly(
                id=hashlib.md5(f"{session_id}:tokens:{time.time()}".encode()).hexdigest()[:16],
                type=AnomalyType.TOKEN_EXPLOSION,
                severity=AnomalySeverity.ERROR,
                session_id=session_id,
                message=f"Step used {tokens_used} tokens (max: {self.config.max_tokens_per_step})",
                details={
                    "tokens_used": tokens_used,
                    "total_tokens": total_tokens,
                    "threshold": self.config.max_tokens_per_step,
                },
                detected_at=time.time(),
            )
        
        # Check total limit
        if total_tokens > self.config.max_total_tokens:
            return Anomaly(
                id=hashlib.md5(f"{session_id}:total_tokens:{time.time()}".encode()).hexdigest()[:16],
                type=AnomalyType.TOKEN_EXPLOSION,
                severity=AnomalySeverity.CRITICAL,
                session_id=session_id,
                message=f"Total tokens {total_tokens} exceeds limit {self.config.max_total_tokens}",
                details={
                    "total_tokens": total_tokens,
                    "threshold": self.config.max_total_tokens,
                },
                detected_at=time.time(),
            )
        
        # Check for explosion (growth rate)
        if session_id in self._baseline_tokens:
            growth_rate = tokens_used / max(self._baseline_tokens[session_id], 1)
            if growth_rate > 5:  # 5x previous step
                return Anomaly(
                    id=hashlib.md5(f"{session_id}:explosion:{time.time()}".encode()).hexdigest()[:16],
                    type=AnomalyType.TOKEN_EXPLOSION,
                    severity=AnomalySeverity.WARNING,
                    session_id=session_id,
                    message=f"Token growth rate: {growth_rate:.1f}x previous step",
                    details={
                        "tokens_used": tokens_used,
                        "previous_tokens": self._baseline_tokens[session_id],
                        "growth_rate": growth_rate,
                    },
                    detected_at=time.time(),
                )
        
        # Update baseline
        self._baseline_tokens[session_id] = tokens_used
        
        return None


class AnomalyDetector:
    """
    Complete Anomaly Detection System for Agentic AI.
    
    Integrates:
    - Loop detection
    - Latency analysis
    - Cost analysis
    - Quality monitoring
    - Token monitoring
    - Behavioral analysis
    
    Features:
    - Real-time anomaly detection
    - Automatic response
    - Anomaly history
    - Pattern learning
    """
    
    def __init__(self, config: AnomalyConfig | None = None):
        self.config = config or AnomalyConfig()
        
        # Initialize analyzers
        self.loop_detector = LoopDetector(self.config)
        self.latency_analyzer = LatencyAnalyzer(self.config)
        self.cost_analyzer = CostAnalyzer(self.config)
        self.quality_monitor = QualityMonitor(self.config)
        self.token_monitor = TokenMonitor(self.config)
        
        # Session metrics
        self._session_metrics: dict[str, SessionMetrics] = {}
        
        # Anomaly history
        self._anomaly_history: list[Anomaly] = []
        
        # Response handlers
        self._response_handlers: dict[AnomalyType, callable] = {}
        
        # Load config from settings
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from settings."""
        try:
            from app.core.config import settings
            
            # Update token limits from settings
            if hasattr(settings, 'CHUNK_SIZE_TOKENS'):
                self.config.max_tokens_per_step = settings.CHUNK_SIZE_TOKENS * 2
            
            # Update cost limits
            if hasattr(settings, 'LLM_PROVIDER'):
                # Adjust based on provider
                if settings.LLM_PROVIDER == "anthropic":
                    self.config.max_cost_per_step = 0.10
                    self.config.max_cost_per_session = 1.00
        except Exception:
            pass
    
    # ─── Session Management ───────────────────────────────────────────────────
    
    def get_session_metrics(self, session_id: str) -> SessionMetrics:
        """Get or create session metrics."""
        if session_id not in self._session_metrics:
            self._session_metrics[session_id] = SessionMetrics(session_id=session_id)
        return self._session_metrics[session_id]
    
    async def clear_session(self, session_id: str) -> None:
        """Clear metrics for a session."""
        if session_id in self._session_metrics:
            del self._session_metrics[session_id]
        await cache.delete(f"anomaly:session:{session_id}")
    
    # ─── Recording ─────────────────────────────────────────────────────────
    
    async def record_step(
        self,
        session_id: str,
        node: str,
        latency_ms: float,
        cost_usd: float | None = None,
        tokens_used: int | None = None,
        output: str | None = None,
        state: dict | None = None,
        quality_score: float | None = None,
    ) -> None:
        """Record a step execution for analysis."""
        metrics = self.get_session_metrics(session_id)
        
        # Record step
        step_record = {
            "node": node,
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
            "tokens_used": tokens_used,
            "timestamp": time.time(),
        }
        metrics.steps.append(step_record)
        
        # Track node visits
        metrics.node_visits[node] = metrics.node_visits.get(node, 0) + 1
        
        # Track latency
        metrics.latency_history.append(latency_ms)
        
        # Track cost
        if cost_usd is not None:
            metrics.cost_history.append(cost_usd)
        
        # Track tokens
        if tokens_used is not None:
            metrics.token_usage.append(tokens_used)
        
        # Track quality
        if quality_score is not None:
            metrics.quality_scores.append(quality_score)
        
        # Persist to cache
        await self._persist_metrics(session_id, metrics)
    
    async def _persist_metrics(self, session_id: str, metrics: SessionMetrics) -> None:
        """Persist metrics to cache."""
        await cache.set(
            f"anomaly:session:{session_id}",
            metrics.to_dict(),
            ttl=3600  # 1 hour
        )
    
    # ─── Anomaly Detection ─────────────────────────────────────────────────
    
    async def check_anomalies(
        self,
        session_id: str,
        state: dict | None = None,
        output: str | None = None,
    ) -> list[Anomaly]:
        """
        Check for all types of anomalies.
        
        Returns list of detected anomalies.
        """
        anomalies: list[Anomaly] = []
        metrics = self.get_session_metrics(session_id)
        
        # Check for loops
        if state:
            loop_anomaly = self.loop_detector.check_loop(session_id, state, output)
            if loop_anomaly:
                anomalies.append(loop_anomaly)
        
        # Check latency
        if metrics.latency_history:
            last_latency = metrics.latency_history[-1]
            latency_anomaly = self.latency_analyzer.analyze_latency(
                session_id,
                last_latency,
                state.get("current_node") if state else None
            )
            if latency_anomaly:
                anomalies.append(latency_anomaly)
        
        # Check cost
        if metrics.cost_history:
            last_cost = metrics.cost_history[-1]
            total_cost = sum(metrics.cost_history)
            cost_anomaly = self.cost_analyzer.analyze_cost(session_id, last_cost, total_cost)
            if cost_anomaly:
                anomalies.append(cost_anomaly)
        
        # Check quality
        if metrics.quality_scores and output:
            last_quality = metrics.quality_scores[-1]
            quality_anomaly = self.quality_monitor.analyze_quality(
                session_id, last_quality, output
            )
            if quality_anomaly:
                anomalies.append(quality_anomaly)
        
        # Check tokens
        if metrics.token_usage:
            last_tokens = metrics.token_usage[-1]
            total_tokens = sum(metrics.token_usage)
            token_anomaly = self.token_monitor.analyze_tokens(
                session_id, last_tokens, total_tokens
            )
            if token_anomaly:
                anomalies.append(token_anomaly)
        
        # Check for stuck state (no progress for too long)
        stuck_anomaly = self._check_stuck_state(session_id, metrics)
        if stuck_anomaly:
            anomalies.append(stuck_anomaly)
        
        # Record anomalies
        self._anomaly_history.extend(anomalies)
        
        # Keep anomaly history limited
        if len(self._anomaly_history) > 1000:
            self._anomaly_history = self._anomaly_history[-500:]
        
        return anomalies
    
    def _check_stuck_state(
        self,
        session_id: str,
        metrics: SessionMetrics,
    ) -> Anomaly | None:
        """Check if agent is stuck in a state."""
        if not metrics.steps:
            return None
        
        # Check if last step took too long
        last_step = metrics.steps[-1]
        if last_step.get("latency_ms", 0) > self.config.max_single_step_latency_ms * 2:
            return Anomaly(
                id=hashlib.md5(f"{session_id}:stuck:{time.time()}".encode()).hexdigest()[:16],
                type=AnomalyType.STUCK_STATE,
                severity=AnomalySeverity.CRITICAL,
                session_id=session_id,
                message="Agent appears stuck - no progress for extended period",
                details={
                    "last_latency_ms": last_step.get("latency_ms"),
                    "total_steps": len(metrics.steps),
                    "last_node": last_step.get("node"),
                },
                detected_at=time.time(),
            )
        
        return None
    
    # ─── Response Handling ──────────────────────────────────────────────────
    
    def register_response_handler(self, anomaly_type: AnomalyType, handler: callable) -> None:
        """Register a handler for a specific anomaly type."""
        self._response_handlers[anomaly_type] = handler
    
    async def respond_to_anomaly(self, anomaly: Anomaly) -> str:
        """
        Respond to a detected anomaly.
        
        Returns description of response taken.
        """
        response = f"No automatic response for {anomaly.type.value}"
        
        # Call registered handler
        if anomaly.type in self._response_handlers:
            try:
                result = self._response_handlers[anomaly.type](anomaly)
                if asyncio.iscoroutine(result):
                    result = await result
                response = result
            except Exception as e:
                logger.error("anomaly_handler_error", type=anomaly.type.value, error=str(e))
                response = f"Handler error: {str(e)}"
        
        # Default responses based on severity
        elif anomaly.severity in (AnomalySeverity.ERROR, AnomalySeverity.CRITICAL):
            # Log critical anomalies
            logger.error(
                "anomaly_detected",
                **anomaly.to_dict()
            )
            response = "Critical anomaly logged - manual intervention may be required"
        
        anomaly.response_taken = response
        
        # Update anomaly history
        for i, a in enumerate(self._anomaly_history):
            if a.id == anomaly.id:
                self._anomaly_history[i] = anomaly
                break
        
        return response
    
    async def respond_to_anomalies(self, anomalies: list[Anomaly]) -> list[str]:
        """Respond to multiple anomalies."""
        responses = []
        for anomaly in anomalies:
            response = await self.respond_to_anomaly(anomaly)
            responses.append(response)
        return responses
    
    # ─── Reporting ─────────────────────────────────────────────────────────
    
    def get_anomaly_summary(self, session_id: str | None = None) -> dict:
        """Get summary of anomalies."""
        if session_id:
            anomalies = [a for a in self._anomaly_history if a.session_id == session_id]
        else:
            anomalies = self._anomaly_history
        
        if not anomalies:
            return {
                "total_anomalies": 0,
                "by_type": {},
                "by_severity": {},
                "recent": [],
            }
        
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        
        for a in anomalies:
            by_type[a.type.value] = by_type.get(a.type.value, 0) + 1
            by_severity[a.severity.value] = by_severity.get(a.severity.value, 0) + 1
        
        return {
            "total_anomalies": len(anomalies),
            "by_type": by_type,
            "by_severity": by_severity,
            "recent": [a.to_dict() for a in anomalies[-10:]],
        }
    
    def get_session_health(self, session_id: str) -> dict:
        """Get health status of a session."""
        metrics = self.get_session_metrics(session_id)
        
        if not metrics.steps:
            return {"status": "no_data"}
        
        # Calculate health scores
        latency_health = 1.0
        if metrics.latency_history:
            avg_latency = sum(metrics.latency_history) / len(metrics.latency_history)
            latency_health = 1.0 - min(1.0, avg_latency / self.config.max_average_latency_ms)
        
        cost_health = 1.0
        if metrics.cost_history:
            total_cost = sum(metrics.cost_history)
            cost_health = 1.0 - min(1.0, total_cost / self.config.max_cost_per_session)
        
        quality_health = 1.0
        if metrics.quality_scores:
            avg_quality = sum(metrics.quality_scores) / len(metrics.quality_scores)
            quality_health = avg_quality
        
        # Overall health
        overall = (latency_health + cost_health + quality_health) / 3
        
        status = "healthy"
        if overall < 0.5:
            status = "degraded"
        if overall < 0.3:
            status = "unhealthy"
        
        return {
            "status": status,
            "overall_health": overall,
            "latency_health": latency_health,
            "cost_health": cost_health,
            "quality_health": quality_health,
            "metrics": metrics.to_dict(),
        }
    
    # ─── Utility ─────────────────────────────────────────────────────────
    
    def reset_session(self, session_id: str) -> None:
        """Reset detection state for a session."""
        if session_id in self._session_metrics:
            self._session_metrics[session_id] = SessionMetrics(session_id=session_id)
        
        # Clear loop detector state
        if session_id in self.loop_detector._state_hashes:
            del self.loop_detector._state_hashes[session_id]


# ─── Global Instance ─────────────────────────────────────────────────────────

_detector_instance: AnomalyDetector | None = None


def get_anomaly_detector() -> AnomalyDetector:
    """Get the global AnomalyDetector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = AnomalyDetector()
    return _detector_instance


def reset_anomaly_detector() -> None:
    """Reset the global instance (for testing)."""
    global _detector_instance
    _detector_instance = None
