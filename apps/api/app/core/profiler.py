"""Production performance profiling utilities.

Tools:
- SQLAlchemy query profiler for slow query detection
- cProfile wrapper for function-level analysis
"""

from __future__ import annotations

import cProfile
import io
import pstats
import time
from contextlib import contextmanager
from functools import wraps

from app.core.logging import get_logger

logger = get_logger("profiler")


@contextmanager
def profile_function(name: str | None = None):
    """Context manager for profiling a function."""
    profiler = cProfile.Profile()
    profiler.enable()
    start = time.perf_counter()

    try:
        yield profiler
    finally:
        profiler.disable()
        elapsed = time.perf_counter() - start
        s = io.StringIO()
        stats = pstats.Stats(profiler, stream=s)
        stats.sort_stats("cumulative")
        stats.print_stats(15)
        logger.info(
            "profile_complete",
            name=name,
            elapsed_ms=round(elapsed * 1000, 2),
            top_functions=s.getvalue()[:1500],
        )


def profiled(func):
    """Decorator to profile an async function."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        with profile_function(f"{func.__module__}.{func.__name__}"):
            return await func(*args, **kwargs)
    return wrapper


# ─── SQLAlchemy Query Profiler ───────────────────────────────────────────────


class SQLAlchemyProfiler:
    """
    Profile SQLAlchemy queries using event listeners.

    Usage:
        from sqlalchemy import event
        profiler = SQLAlchemyProfiler(threshold_ms=50.0)
        event.listen(engine, "before_cursor_execute", profiler.before_cursor_execute)
        event.listen(engine, "after_cursor_execute", profiler.after_cursor_execute)
    """

    def __init__(self, threshold_ms: float = 50.0):
        self.threshold_ms = threshold_ms
        self.queries: list[dict] = []
        self._start_times: dict[int, float] = {}

    def before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.perf_counter())

    def after_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        total = time.perf_counter() - conn.info["query_start_time"].pop()
        duration_ms = round(total * 1000, 2)

        if duration_ms > self.threshold_ms:
            logger.warning(
                "slow_query",
                duration_ms=duration_ms,
                statement=statement[:200],
                params=str(parameters)[:200],
            )
            self.queries.append({
                "duration_ms": duration_ms,
                "statement": statement,
                "parameters": str(parameters)[:200],
            })
