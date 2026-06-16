"""Agent services package - exports all agent components including safety.

Usage:
    # Import safety components
    from app.services.agent import AgentSafety, get_agent_safety
    from app.services.agent import ToolSafety, get_tool_safety
    from app.services.agent import AnomalyDetector, get_anomaly_detector
    from app.services.agent import GracefulDegradation, get_resilience
    from app.services.agent import ContextManager, get_context_manager
    from app.services.agent import A2AProtocol, get_a2a_protocol
    
    # Use safety features
    safety = get_agent_safety()
    await safety.abort_session(session_id, reason="user_requested")
"""

from __future__ import annotations

# Re-export safety components
from app.services.agent.safety import (
    # Core safety
    AgentSafety,
    SafetyConfig,
    SessionState,
    TokenBudget,
    AbortReason,
    get_agent_safety,
    reset_agent_safety,
    
    # Tool safety
    ToolSafety,
    ToolSafetyConfig,
    InputValidator,
    PIIDetector,
    OutputFilter,
    get_tool_safety,
    reset_tool_safety,
    
    # Resilience
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    GracefulDegradation,
    RateLimiter,
    DeadLetterQueue,
    get_resilience,
    get_circuit_breaker,
    reset_resilience,
    
    # Anomaly detection
    AnomalyDetector,
    AnomalyConfig,
    Anomaly,
    AnomalyType,
    AnomalySeverity,
    get_anomaly_detector,
    reset_anomaly_detector,
)

# Re-export memory
from app.services.agent.memory import (
    AgentMemory,
    MemoryConfig,
    MemoryTier,
    MemoryEntry,
    Turn,
    get_agent_memory,
    reset_agent_memory,
)

# Re-export context manager
from app.services.agent.safety.context_manager import (
    ContextManager,
    ContextConfig,
    ContextItem,
    ContextPriority,
    get_context_manager,
    reset_context_manager,
)

# Re-export A2A protocol
from app.services.agent.a2a import (
    A2AProtocol,
    A2AClient,
    AgentCard,
    AgentSkill,
    Capability,
    Task,
    Message,
    TaskStatus,
    MessageType,
    get_a2a_protocol,
    init_a2a_protocol,
    shutdown_a2a_protocol,
    get_retrieval_agent_card,
    get_timeline_agent_card,
    get_graph_agent_card,
    get_synthesizer_agent_card,
)

__all__ = [
    # Core safety
    "AgentSafety",
    "SafetyConfig",
    "SessionState",
    "TokenBudget",
    "AbortReason",
    "get_agent_safety",
    "reset_agent_safety",
    
    # Tool safety
    "ToolSafety",
    "ToolSafetyConfig",
    "InputValidator",
    "PIIDetector",
    "OutputFilter",
    "get_tool_safety",
    "reset_tool_safety",
    
    # Resilience
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerOpenError",
    "GracefulDegradation",
    "RateLimiter",
    "DeadLetterQueue",
    "get_resilience",
    "get_circuit_breaker",
    "reset_resilience",
    
    # Anomaly detection
    "AnomalyDetector",
    "AnomalyConfig",
    "Anomaly",
    "AnomalyType",
    "AnomalySeverity",
    "get_anomaly_detector",
    "reset_anomaly_detector",
    
    # Memory
    "AgentMemory",
    "MemoryConfig",
    "MemoryTier",
    "MemoryEntry",
    "Turn",
    "get_agent_memory",
    "reset_agent_memory",
    
    # Context manager
    "ContextManager",
    "ContextConfig",
    "ContextItem",
    "ContextPriority",
    "get_context_manager",
    "reset_context_manager",
    
    # A2A
    "A2AProtocol",
    "A2AClient",
    "AgentCard",
    "AgentSkill",
    "Capability",
    "Task",
    "Message",
    "TaskStatus",
    "MessageType",
    "get_a2a_protocol",
    "init_a2a_protocol",
    "shutdown_a2a_protocol",
    "get_retrieval_agent_card",
    "get_timeline_agent_card",
    "get_graph_agent_card",
    "get_synthesizer_agent_card",
]
