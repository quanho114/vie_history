"""Circuit Breaker and Graceful Degradation for Agentic AI Systems.

This module provides production-grade resilience patterns:
- Circuit Breaker: Prevent cascading failures in external API calls
- Fallback Chain: Multiple fallback options when primary fails
- Rate Limiting: Prevent abuse and manage quota
- Dead Letter Queue: Store failed tasks for later retry

Usage:
    from app.services.agent.safety import CircuitBreaker, GracefulDegradation, get_resilience
    
    resilience = get_resilience()
    
    # Execute with circuit breaker
    result = await resilience.execute_with_circuit_breaker(
        service="openai",
        operation=lambda: call_api()
    )
    
    # Execute with fallback chain
    result = await resilience.execute_with_fallback(
        fallbacks=[
            lambda: primary_call(),
            lambda: secondary_call(),
            lambda: cached_response(),
        ]
    )
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable, TypeVar

from app.core.logging import get_logger

logger = get_logger("resilience")

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class ServiceStatus(Enum):
    """Health status of a service."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5        # Failures before opening
    success_threshold: int = 2        # Successes to close after half-open
    timeout_seconds: float = 30.0     # Time before trying half-open
    half_open_max_calls: int = 3     # Max calls in half-open state
    
    # Error classification
    retryable_errors: list[str] = field(default_factory=lambda: [
        "timeout", "connection", "503", "429", "rate_limit"
    ])
    fatal_errors: list[str] = field(default_factory=lambda: [
        "401", "403", "404", "invalid_request"
    ])


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker."""
    rotation_interval: int = 10000
    _call_count: int = field(default=0, repr=False)
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: float = 0
    last_success_time: float = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    average_latency_ms: float = 0
    total_latency_ms: float = 0

    def record_call(self, latency: float) -> None:
        """Record a call for metrics rotation tracking."""
        self.total_calls += 1
        self.total_latency_ms += latency
        self._call_count += 1
        if self._call_count >= self.rotation_interval:
            self._rotate()

    def _rotate(self) -> None:
        """Rotate metrics to prevent unbounded growth."""
        self.total_calls = 0
        self.total_latency_ms = 0.0
        self._call_count = 0


class CircuitBreaker:
    """
    Circuit Breaker implementation for external service calls.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is failing, requests are rejected immediately
    - HALF_OPEN: Testing if service has recovered
    
    Behavior:
    - After `failure_threshold` consecutive failures, opens the circuit
    - After `timeout_seconds` in open state, allows test requests (half-open)
    - After `success_threshold` successes in half-open, closes the circuit
    - After any failure in half-open, reopens the circuit
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()
        self._half_open_calls = 0
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        if self._state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if time.time() - self._metrics.last_failure_time >= self.config.timeout_seconds:
                return CircuitState.HALF_OPEN
        return self._state
    
    @property
    def is_available(self) -> bool:
        """Check if the circuit allows requests."""
        return self.state != CircuitState.OPEN
    
    async def can_execute(self) -> tuple[bool, str]:
        """Check if execution is allowed."""
        current_state = self.state
        
        if current_state == CircuitState.OPEN:
            return False, f"Circuit is OPEN, service unavailable"
        
        if current_state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.config.half_open_max_calls:
                return False, f"HALF_OPEN max calls reached"
        
        return True, "OK"
    
    async def execute(
        self,
        operation: Callable[[], Awaitable[T]],
        fallback: Callable[[], Awaitable[T]] | None = None,
    ) -> T:
        """
        Execute an operation with circuit breaker protection.
        
        Args:
            operation: The async operation to execute
            fallback: Optional fallback if operation fails
            
        Returns:
            Result of operation or fallback
        """
        can_exec, reason = await self.can_execute()
        
        if not can_exec:
            self._metrics.rejected_calls += 1
            logger.warning("circuit_breaker_rejected", service=self.name, reason=reason)
            
            if fallback:
                logger.info("circuit_breaker_using_fallback", service=self.name)
                return await fallback()
            
            raise CircuitBreakerOpenError(f"Circuit breaker is open: {reason}")
        
        # Track half-open calls
        if self.state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
        
        # Execute operation
        start_time = time.time()
        try:
            result = await operation()
            
            # Success
            await self._record_success(time.time() - start_time)
            return result
            
        except Exception as e:
            # Failure
            await self._record_failure(str(e), time.time() - start_time)
            
            if fallback:
                return await fallback()
            
            raise
    
    async def _record_success(self, latency: float) -> None:
        """Record a successful call."""
        async with self._lock:
            self._metrics.total_calls += 1
            self._metrics.successful_calls += 1
            self._metrics.consecutive_successes += 1
            self._metrics.consecutive_failures = 0
            self._metrics.last_success_time = time.time()
            self._metrics.total_latency_ms += latency * 1000
            self._metrics.average_latency_ms = (
                self._metrics.total_latency_ms / max(self._metrics.total_calls, 1)
            )
            
            # State transitions
            if self._state == CircuitState.HALF_OPEN:
                if self._metrics.consecutive_successes >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._metrics.consecutive_successes = 0
                    self._half_open_calls = 0
                    logger.info("circuit_breaker_closed", service=self.name)
            
            logger.debug(
                "circuit_breaker_success",
                service=self.name,
                state=self.state.value,
                latency_ms=latency * 1000,
            )
    
    async def _record_failure(self, error: str, latency: float) -> None:
        """Record a failed call."""
        async with self._lock:
            self._metrics.total_calls += 1
            self._metrics.failed_calls += 1
            self._metrics.consecutive_failures += 1
            self._metrics.consecutive_successes = 0
            self._metrics.last_failure_time = time.time()
            self._metrics.total_latency_ms += latency * 1000
            self._metrics.average_latency_ms = (
                self._metrics.total_latency_ms / max(self._metrics.total_calls, 1)
            )
            
            # Check if error is fatal
            is_fatal = any(fe in error for fe in self.config.fatal_errors)
            
            # State transitions
            if is_fatal:
                # Fatal errors open the circuit immediately
                self._state = CircuitState.OPEN
                logger.warning(
                    "circuit_breaker_opened_fatal",
                    service=self.name,
                    error=error,
                )
            elif self._metrics.consecutive_failures >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "circuit_breaker_opened",
                    service=self.name,
                    consecutive_failures=self._metrics.consecutive_failures,
                )
            elif self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens
                self._state = CircuitState.OPEN
                self._half_open_calls = 0
                logger.warning(
                    "circuit_breaker_reopened",
                    service=self.name,
                    error=error,
                )
            
            logger.warning(
                "circuit_breaker_failure",
                service=self.name,
                state=self.state.value,
                error=error,
                latency_ms=latency * 1000,
            )
    
    def get_metrics(self) -> CircuitBreakerMetrics:
        """Get circuit breaker metrics."""
        return self._metrics
    
    def reset(self) -> None:
        """Reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._metrics = CircuitBreakerMetrics()
        self._half_open_calls = 0
        logger.info("circuit_breaker_reset", service=self.name)


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


@dataclass
class FallbackConfig:
    """Configuration for fallback chain."""
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    exponential_backoff: bool = True
    max_delay_seconds: float = 30.0
    
    # Fallback availability
    fallback_timeout_seconds: float = 10.0


@dataclass
class FallbackStep:
    """A single fallback step."""
    name: str
    operation: Callable[[], Awaitable[T]]
    priority: int = 0
    enabled: bool = True
    max_attempts: int = 1


class FallbackChain:
    """
    Fallback Chain - tries multiple fallback options in sequence.
    
    Usage:
        chain = FallbackChain()
        chain.add(primary_llm_call, priority=1)
        chain.add(fallback_llm_call, priority=2)
        chain.add(cached_response, priority=3)
        chain.add(extractive_answer, priority=4)  # Last resort
        
        result = await chain.execute()
    """
    
    def __init__(self, config: FallbackConfig | None = None):
        self.config = config or FallbackConfig()
        self._steps: list[FallbackStep] = []
        self._lock = asyncio.Lock()
    
    def add(
        self,
        operation: Callable[[], Awaitable[T]],
        name: str = "",
        priority: int = 0,
        enabled: bool = True,
        max_attempts: int = 1,
    ) -> "FallbackChain":
        """Add a fallback step to the chain."""
        step = FallbackStep(
            name=name or f"step_{len(self._steps)}",
            operation=operation,
            priority=priority,
            enabled=enabled,
            max_attempts=max_attempts,
        )
        self._steps.append(step)
        
        # Sort by priority (higher = try first)
        self._steps.sort(key=lambda s: s.priority, reverse=True)
        
        return self
    
    def remove(self, name: str) -> bool:
        """Remove a step by name."""
        for i, step in enumerate(self._steps):
            if step.name == name:
                self._steps.pop(i)
                return True
        return False
    
    def disable(self, name: str) -> None:
        """Disable a fallback step."""
        for step in self._steps:
            if step.name == name:
                step.enabled = False
    
    def enable(self, name: str) -> None:
        """Enable a fallback step."""
        for step in self._steps:
            if step.name == name:
                step.enabled = True
    
    async def execute(self) -> tuple[T | None, str]:
        """
        Execute the fallback chain.
        
        Returns:
            (result, success_reason) - result is None if all fallbacks failed
        """
        last_error = ""
        
        for step in self._steps:
            if not step.enabled:
                continue
            
            for attempt in range(step.max_attempts):
                try:
                    # Calculate delay with exponential backoff
                    if attempt > 0 and self.config.exponential_backoff:
                        delay = min(
                            self.config.retry_delay_seconds * (2 ** (attempt - 1)),
                            self.config.max_delay_seconds
                        )
                        await asyncio.sleep(delay)
                    
                    # Execute with timeout
                    result = await asyncio.wait_for(
                        step.operation(),
                        timeout=self.config.fallback_timeout_seconds
                    )
                    
                    logger.info(
                        "fallback_step_success",
                        step=step.name,
                        attempt=attempt + 1,
                    )
                    
                    return result, step.name
                    
                except asyncio.TimeoutError:
                    last_error = f"{step.name}: Timeout after {self.config.fallback_timeout_seconds}s"
                    logger.warning(
                        "fallback_step_timeout",
                        step=step.name,
                        attempt=attempt + 1,
                    )
                    
                except Exception as e:
                    last_error = f"{step.name}: {str(e)}"
                    logger.warning(
                        "fallback_step_failed",
                        step=step.name,
                        attempt=attempt + 1,
                        error=str(e),
                    )
        
        logger.error(
            "fallback_chain_exhausted",
            total_steps=len(self._steps),
            last_error=last_error,
        )
        
        return None, f"All fallbacks failed: {last_error}"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    
    # Cost limits
    max_cost_per_request: float = 0.50
    max_cost_per_hour: float = 5.00


@dataclass
class RateLimitMetrics:
    """Rate limit tracking metrics."""
    requests_this_minute: int = 0
    requests_this_hour: int = 0
    total_cost: float = 0
    last_request_time: float = 0
    minute_reset_time: float = 0
    hour_reset_time: float = 0


class RateLimiter:
    """
    Token bucket rate limiter with cost tracking.
    
    Features:
    - Per-minute and per-hour limits
    - Cost-based limits
    - Burst allowance
    - Sliding window tracking
    """
    
    def __init__(self, config: RateLimitConfig | None = None):
        self.config = config or RateLimitConfig()
        self._metrics = RateLimitMetrics()
        self._lock = asyncio.Lock()
        self._minute_bucket = config.burst_size if config else 10
        self._hour_bucket = config.requests_per_hour if config else 1000
    
    async def acquire(
        self,
        estimated_cost: float = 0,
        user_id: str = "default",
    ) -> tuple[bool, str]:
        """
        Try to acquire permission to make a request.
        
        Returns:
            (allowed, reason)
        """
        async with self._lock:
            now = time.time()
            
            # Reset minute bucket if needed
            if now >= self._metrics.minute_reset_time:
                self._metrics.requests_this_minute = 0
                self._metrics.minute_reset_time = now + 60
                self._minute_bucket = self.config.burst_size
            
            # Reset hour bucket if needed
            if now >= self._metrics.hour_reset_time:
                self._metrics.requests_this_hour = 0
                self._metrics.hour_reset_time = now + 3600
            
            # Check cost limits
            if estimated_cost > self.config.max_cost_per_request:
                return False, f"Estimated cost ${estimated_cost:.2f} exceeds limit"
            
            if self._metrics.total_cost + estimated_cost > self.config.max_cost_per_hour:
                return False, f"Total cost limit exceeded: ${self._metrics.total_cost:.2f}"
            
            # Check rate limits
            if self._metrics.requests_this_minute >= self.config.requests_per_minute:
                wait_time = self._metrics.minute_reset_time - now
                return False, f"Rate limit exceeded, wait {wait_time:.1f}s"
            
            if self._metrics.requests_this_hour >= self.config.requests_per_hour:
                wait_time = self._metrics.hour_reset_time - now
                return False, f"Hourly limit exceeded, wait {wait_time:.1f}s"
            
            # Consume from bucket
            self._metrics.requests_this_minute += 1
            self._metrics.requests_this_hour += 1
            self._metrics.total_cost += estimated_cost
            self._metrics.last_request_time = now
            
            # Consume burst tokens
            self._minute_bucket = max(0, self._minute_bucket - 1)
            
            return True, "OK"
    
    async def record_usage(self, actual_cost: float = 0) -> None:
        """Record actual cost after request completes."""
        async with self._lock:
            self._metrics.total_cost += actual_cost
    
    def get_metrics(self) -> RateLimitMetrics:
        """Get current rate limit metrics."""
        return self._metrics
    
    def get_remaining(self) -> dict:
        """Get remaining quota."""
        now = time.time()
        return {
            "requests_this_minute": self.config.requests_per_minute - self._metrics.requests_this_minute,
            "requests_this_hour": self.config.requests_per_hour - self._metrics.requests_this_hour,
            "cost_remaining": self.config.max_cost_per_hour - self._metrics.total_cost,
            "minute_resets_in": max(0, self._metrics.minute_reset_time - now),
            "hour_resets_in": max(0, self._metrics.hour_reset_time - now),
        }


@dataclass
class DeadLetterQueueEntry:
    """Entry in the dead letter queue."""
    id: str
    operation_name: str
    args: dict
    kwargs: dict
    error: str
    error_type: str
    attempts: int
    created_at: float
    last_attempt_at: float
    status: str  # pending, retrying, failed, completed
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "operation_name": self.operation_name,
            "args": self.args,
            "kwargs": self.kwargs,
            "error": self.error,
            "error_type": self.error_type,
            "attempts": self.attempts,
            "created_at": self.created_at,
            "last_attempt_at": self.last_attempt_at,
            "status": self.status,
        }


class DeadLetterQueue:
    """
    Dead Letter Queue for failed agent operations.
    
    Features:
    - Store failed operations for later retry
    - Track retry attempts
    - Expose failed operations for debugging
    - Automatic cleanup of old entries
    - Background periodic cleanup thread
    """
    
    def __init__(self, max_age_hours: int = 24, max_entries: int = 1000):
        self._queue: dict[str, DeadLetterQueueEntry] = {}
        self._max_age_hours = max_age_hours
        self._max_entries = max_entries
        self._lock = asyncio.Lock()
        self._cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self._cleanup_thread.start()

    def _periodic_cleanup(self) -> None:
        import logging
        while True:
            time.sleep(3600)  # every hour
            try:
                # Run cleanup in the async event loop if available
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.cleanup_expired())
                else:
                    loop.run_until_complete(self.cleanup_expired())
            except Exception as e:
                logging.getLogger("dlq").error(f"DLQ cleanup failed: {e}")
    
    async def add(
        self,
        operation_name: str,
        args: dict,
        kwargs: dict,
        error: Exception,
    ) -> str:
        """Add a failed operation to the queue."""
        import hashlib
        
        entry_id = hashlib.md5(
            f"{operation_name}:{str(args)}:{time.time()}".encode()
        ).hexdigest()[:16]
        
        entry = DeadLetterQueueEntry(
            id=entry_id,
            operation_name=operation_name,
            args=args,
            kwargs=kwargs,
            error=str(error),
            error_type=type(error).__name__,
            attempts=0,
            created_at=time.time(),
            last_attempt_at=time.time(),
            status="pending",
        )
        
        async with self._lock:
            # Enforce max entries
            if len(self._queue) >= self._max_entries:
                await self._cleanup_oldest()
            
            self._queue[entry_id] = entry
        
        logger.warning(
            "dlq_entry_added",
            entry_id=entry_id,
            operation=operation_name,
            error_type=type(error).__name__,
        )
        
        return entry_id
    
    async def mark_retrying(self, entry_id: str) -> None:
        """Mark an entry as retrying."""
        async with self._lock:
            if entry_id in self._queue:
                self._queue[entry_id].status = "retrying"
                self._queue[entry_id].attempts += 1
                self._queue[entry_id].last_attempt_at = time.time()
    
    async def mark_completed(self, entry_id: str) -> None:
        """Mark an entry as completed."""
        async with self._lock:
            if entry_id in self._queue:
                self._queue[entry_id].status = "completed"
                logger.info("dlq_entry_completed", entry_id=entry_id)
    
    async def mark_failed(self, entry_id: str, error: str) -> None:
        """Mark an entry as permanently failed."""
        async with self._lock:
            if entry_id in self._queue:
                self._queue[entry_id].status = "failed"
                self._queue[entry_id].error = error
                logger.error("dlq_entry_failed", entry_id=entry_id, error=error)
    
    async def get_pending(self) -> list[DeadLetterQueueEntry]:
        """Get all pending entries."""
        async with self._lock:
            return [
                e for e in self._queue.values()
                if e.status in ("pending", "retrying")
            ]
    
    async def get_failed(self) -> list[DeadLetterQueueEntry]:
        """Get all failed entries."""
        async with self._lock:
            return [e for e in self._queue.values() if e.status == "failed"]
    
    async def get_by_id(self, entry_id: str) -> DeadLetterQueueEntry | None:
        """Get entry by ID."""
        async with self._lock:
            return self._queue.get(entry_id)
    
    async def retry_entry(self, entry_id: str) -> tuple[bool, Any]:
        """
        Retry a failed entry.
        
        Returns:
            (success, result_or_error)
        """
        entry = await self.get_by_id(entry_id)
        if not entry:
            return False, "Entry not found"
        
        if entry.status == "completed":
            return True, "Already completed"
        
        if entry.attempts >= 5:
            await self.mark_failed(entry_id, "Max retry attempts exceeded")
            return False, "Max retry attempts exceeded"
        
        await self.mark_retrying(entry_id)
        
        # Note: Actual retry logic should be implemented by caller
        # This just tracks the attempt
        
        return True, "Retry scheduled"
    
    async def _cleanup_oldest(self) -> int:
        """Remove oldest completed entries."""
        completed = [
            (eid, e) for eid, e in self._queue.items()
            if e.status == "completed"
        ]
        
        # Sort by last_attempt_at
        completed.sort(key=lambda x: x[1].last_attempt_at)
        
        # Remove oldest half
        to_remove = completed[:len(completed) // 2]
        for eid, _ in to_remove:
            del self._queue[eid]
        
        return len(to_remove)
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        cutoff = time.time() - (self._max_age_hours * 3600)
        removed = 0
        
        async with self._lock:
            expired = [
                eid for eid, e in self._queue.items()
                if e.created_at < cutoff and e.status in ("completed", "failed")
            ]
            
            for eid in expired:
                del self._queue[eid]
                removed += 1
        
        if removed:
            logger.info("dlq_cleanup_expired", removed=removed)
        
        return removed
    
    def get_stats(self) -> dict:
        """Get queue statistics."""
        return {
            "total_entries": len(self._queue),
            "pending": sum(1 for e in self._queue.values() if e.status == "pending"),
            "retrying": sum(1 for e in self._queue.values() if e.status == "retrying"),
            "completed": sum(1 for e in self._queue.values() if e.status == "completed"),
            "failed": sum(1 for e in self._queue.values() if e.status == "failed"),
        }


class GracefulDegradation:
    """
    Complete Graceful Degradation System.
    
    Integrates:
    - Circuit breakers for each service
    - Fallback chains
    - Rate limiting
    - Dead letter queue
    
    Provides production-grade resilience.
    """
    
    def __init__(self):
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._rate_limiter = RateLimiter()
        self._dlq = DeadLetterQueue()
        self._lock = asyncio.Lock()
        self.register_circuit_breaker("qdrant", threshold=5, window=60, recovery=30)
        self.register_circuit_breaker("elasticsearch", threshold=5, window=60, recovery=30)
        self.register_circuit_breaker("redis", threshold=5, window=30, recovery=15)

    def register_circuit_breaker(self, name: str, threshold: int = 5, window: int = 60, recovery: int = 30) -> None:
        """Register a named circuit breaker with custom config."""
        if name not in self._circuit_breakers:
            config = CircuitBreakerConfig(
                failure_threshold=threshold,
                timeout_seconds=float(recovery),
            )
            self._circuit_breakers[name] = CircuitBreaker(name, config)
    
    # ─── Circuit Breaker Management ─────────────────────────────────────────
    
    def get_circuit_breaker(self, service: str) -> CircuitBreaker:
        """Get or create circuit breaker for a service."""
        if service not in self._circuit_breakers:
            self._circuit_breakers[service] = CircuitBreaker(service)
        return self._circuit_breakers[service]
    
    async def execute_with_circuit_breaker(
        self,
        service: str,
        operation: Callable[[], Awaitable[T]],
        fallback: Callable[[], Awaitable[T]] | None = None,
    ) -> T:
        """Execute an operation with circuit breaker protection."""
        cb = self.get_circuit_breaker(service)
        return await cb.execute(operation, fallback)
    
    # ─── Fallback Chain ─────────────────────────────────────────────────────
    
    def create_fallback_chain(self) -> FallbackChain:
        """Create a new fallback chain."""
        return FallbackChain()
    
    async def execute_with_fallback(
        self,
        fallbacks: list[Callable[[], Awaitable[T]]],
        names: list[str] | None = None,
    ) -> tuple[T | None, str]:
        """Execute operations with fallback chain."""
        chain = FallbackChain()
        
        for i, operation in enumerate(fallbacks):
            name = names[i] if names and i < len(names) else f"fallback_{i}"
            chain.add(operation, name=name, priority=len(fallbacks) - i)
        
        return await chain.execute()
    
    # ─── Rate Limiting ──────────────────────────────────────────────────────
    
    async def check_rate_limit(
        self,
        estimated_cost: float = 0,
        user_id: str = "default",
    ) -> tuple[bool, str]:
        """Check if request is within rate limits."""
        return await self._rate_limiter.acquire(estimated_cost, user_id)
    
    def get_rate_limit_status(self) -> dict:
        """Get current rate limit status."""
        return self._rate_limiter.get_remaining()
    
    # ─── Dead Letter Queue ──────────────────────────────────────────────────
    
    async def queue_failed_operation(
        self,
        operation_name: str,
        args: dict,
        kwargs: dict,
        error: Exception,
    ) -> str:
        """Queue a failed operation for later retry."""
        return await self._dlq.add(operation_name, args, kwargs, error)
    
    async def retry_failed_operation(self, entry_id: str) -> tuple[bool, str]:
        """Retry a failed operation."""
        return await self._dlq.retry_entry(entry_id)
    
    def get_dlq_stats(self) -> dict:
        """Get dead letter queue statistics."""
        return self._dlq.get_stats()
    
    # ─── Composite Operations ──────────────────────────────────────────────
    
    async def execute_resilient(
        self,
        service: str,
        operation: Callable[[], Awaitable[T]],
        fallback_chain: list[Callable[[], Awaitable[T]]] | None = None,
        estimated_cost: float = 0,
        user_id: str = "default",
        queue_on_failure: bool = True,
    ) -> tuple[T | None, str, str]:
        """
        Execute an operation with full resilience features.
        
        Returns:
            (result, status, message)
            status: "success", "fallback", "queued", "failed"
        """
        # Check rate limit first
        allowed, reason = await self.check_rate_limit(estimated_cost, user_id)
        if not allowed:
            return None, "rate_limited", reason
        
        try:
            # Execute with circuit breaker and fallback
            if fallback_chain:
                result, fallback_reason = await self.execute_with_fallback(
                    [operation] + fallback_chain
                )
                if result is not None:
                    status = "success" if fallback_reason == "fallback_0" else "fallback"
                    return result, status, fallback_reason
            
            # Execute with just circuit breaker
            cb = self.get_circuit_breaker(service)
            result = await cb.execute(operation)
            return result, "success", "OK"
            
        except CircuitBreakerOpenError as e:
            if fallback_chain:
                result, reason = await self.execute_with_fallback(fallback_chain)
                if result is not None:
                    return result, "circuit_fallback", reason
            
            if queue_on_failure:
                entry_id = await self.queue_failed_operation(
                    service, {}, {}, e
                )
                return None, "queued", f"Queued as {entry_id}"
            
            return None, "failed", str(e)
            
        except Exception as e:
            if queue_on_failure:
                entry_id = await self.queue_failed_operation(
                    service, {}, {}, e
                )
                return None, "queued", f"Queued as {entry_id}"
            
            return None, "failed", str(e)
    
    # ─── Health ────────────────────────────────────────────────────────────
    
    def get_health_status(self) -> dict:
        """Get overall health status of all services."""
        circuit_breaker_states = {
            name: cb.state.value
            for name, cb in self._circuit_breakers.items()
        }
        
        # Determine overall status
        if any(state == "open" for state in circuit_breaker_states.values()):
            overall = ServiceStatus.DEGRADED
        elif any(state == "half_open" for state in circuit_breaker_states.values()):
            overall = ServiceStatus.DEGRADED
        else:
            overall = ServiceStatus.HEALTHY
        
        return {
            "overall_status": overall.value,
            "circuit_breakers": circuit_breaker_states,
            "rate_limit": self.get_rate_limit_status(),
            "dlq": self.get_dlq_stats(),
        }


# ─── Global Instance ─────────────────────────────────────────────────────────

_resilience_instance: GracefulDegradation | None = None


def get_resilience() -> GracefulDegradation:
    """Get the global GracefulDegradation instance."""
    global _resilience_instance
    if _resilience_instance is None:
        _resilience_instance = GracefulDegradation()
    return _resilience_instance


def get_circuit_breaker(service: str) -> CircuitBreaker:
    """Get circuit breaker for a specific service."""
    return get_resilience().get_circuit_breaker(service)


def reset_resilience() -> None:
    """Reset the global instance (for testing)."""
    global _resilience_instance
    _resilience_instance = None
