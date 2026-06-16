"""Centralized circuit breaker registry for all external services."""
from __future__ import annotations


def get_circuit_breaker(name: str):
    """Get a circuit breaker for the named service.

    Registers the service if not already registered, with sensible defaults
    tuned for each service type.
    """
    from app.services.agent.safety.circuit_breaker import GracefulDegradation

    gd = GracefulDegradation()

    # Ensure the service is registered with appropriate thresholds
    if name == "qdrant":
        gd.register_circuit_breaker(name, threshold=5, window=60, recovery=30)
    elif name == "elasticsearch":
        gd.register_circuit_breaker(name, threshold=5, window=60, recovery=30)
    elif name == "redis":
        gd.register_circuit_breaker(name, threshold=5, window=30, recovery=15)

    return gd.get_circuit_breaker(name)
