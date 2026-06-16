# Agent Safety & Production-Grade Features Documentation

> **HistoriAI Agentic AI System - Production Safety & Resilience**

This document describes the production-grade safety and resilience features implemented in HistoriAI.

---

## Table of Contents

1. [Overview](#overview)
2. [Agent Safety Layer](#agent-safety-layer)
3. [5-Tier Memory Architecture](#5-tier-memory-architecture)
4. [Tool Safety](#tool-safety)
5. [Circuit Breaker & Graceful Degradation](#circuit-breaker--graceful-degradation)
6. [Anomaly Detection](#anomaly-detection)
7. [Context Management](#context-management)
8. [A2A Protocol](#a2a-protocol)
9. [Safe LangGraph](#safe-langgraph)
10. [Configuration](#configuration)
11. [Monitoring & Observability](#monitoring--observability)

---

## Overview

HistoriAI implements a comprehensive safety architecture following 2026 best practices for production Agentic AI systems:

- **Agent Safety**: Kill switch, token budgets, runtime guards
- **Memory**: 5-tier hierarchy with automatic compaction
- **Tool Safety**: Input validation, PII detection, output filtering
- **Resilience**: Circuit breakers, fallback chains, dead letter queues
- **Anomaly Detection**: Loop prevention, latency monitoring, cost tracking
- **A2A Protocol**: Multi-agent communication standard

---

## Agent Safety Layer

### Kill Switch

Every agent session can be immediately aborted:

```python
from app.services.agent.safety import get_agent_safety, AbortReason

safety = get_agent_safety()

# Abort a specific session
await safety.abort_session(
    session_id="user-session-123",
    reason=AbortReason.USER_REQUESTED,
    message="User clicked stop button"
)

# Abort ALL sessions (emergency stop)
count = await safety.abort_all_sessions(
    reason=AbortReason.SYSTEM_SHUTDOWN,
    message="System maintenance"
)
```

### Token Budget Enforcement

Hard token limits prevent runaway costs:

```python
# Configure budget
config = SafetyConfig(
    enforce_hard_token_budget=True,
    default_max_tokens=10000,
    max_cost_per_session_usd=2.00,
)

# Track usage
budget = await safety.track_tokens(
    session_id="session-123",
    input_tokens=1000,
    output_tokens=500
)

# Check if can continue
can_continue, reason = await safety.can_continue("session-123")
if not can_continue:
    # Session will be automatically aborted
    pass
```

### Session State Management

```python
# Get session state
session = await safety.get_session("session-123")

# Check status
if session.status == "aborted":
    print(f"Reason: {session.abort_reason}")
```

---

## 5-Tier Memory Architecture

HistoriAI implements a complete 5-tier memory system:

| Tier | Name | Description | Persistence |
|------|-------|-------------|-------------|
| 1 | Short-term | Working context | Ephemeral |
| 2 | Episodic | Conversation history | Session |
| 3 | Semantic | Vector knowledge | Persistent |
| 4 | Procedural | Learned behaviors | Persistent |
| 5 | Observational | Feedback patterns | Persistent |

### Usage

```python
from app.services.agent.memory import get_agent_memory, MemoryTier

memory = get_agent_memory()

# Add conversation turn
await memory.add_turn("session-123", "user", "Chiến dịch Điện Biên Phủ là gì?")

# Retrieve relevant knowledge
knowledge = await memory.retrieve_knowledge("Điện Biên Phủ")
for entry in knowledge:
    print(f"- {entry.content}")

# Build context prompt
context = await memory.build_context_prompt(
    session_id="session-123",
    query="Vietnam War",
    max_chars=8000
)

# Learn from feedback
await memory.learn_from_feedback(
    session_id="session-123",
    query="...",
    response="...",
    rating=0.9
)
```

### Automatic Compaction

Memory automatically compacts when approaching limits:

```python
# Manual trigger
await memory.maybe_compact("session-123", force=True)

# Check stats
stats = await memory.get_memory_stats("session-123")
print(f"Turns: {stats['episodic_turns']}")
print(f"Compaction count: {stats['compaction_count']}")
```

---

## Tool Safety

### Input Validation

Sanitize user inputs before LLM processing:

```python
from app.services.agent.safety import get_tool_safety

safety = get_tool_safety()

# Validate input
result = await safety.validate_input(
    "Chiến tranh Việt Nam diễn ra khi nào?",
    context={"user_id": "123"}
)

if not result.is_valid:
    print(f"Violations: {result.violations}")
    
print(f"Risk level: {result.risk_level}")
print(f"Sanitized: {result.sanitized_content[:100]}...")
```

### PII Detection & Masking

```python
# Detect PII
pii_result = await safety.detect_pii(content)

if pii_result.has_pii:
    print(f"Types: {pii_result.pii_types}")
    print(f"Locations: {pii_result.locations}")
    print(f"Masked: {pii_result.masked_content}")
```

Detects:
- Email addresses
- Phone numbers (Vietnamese format)
- ID numbers (CCCD/CMND)
- Credit cards
- Bank accounts
- IP addresses

### Output Filtering

```python
# Filter output
filter_result = await safety.filter_output(
    raw_llm_output,
    context={"user_id": "123"}
)

if not filter_result.is_safe:
    print(f"Removed: {filter_result.removed_items}")
    print(f"New content: {filter_result.filtered_content}")
```

---

## Circuit Breaker & Graceful Degradation

### Circuit Breaker Pattern

Prevents cascading failures:

```python
from app.services.agent.safety import get_resilience

resilience = get_resilience()

# Execute with circuit breaker
result = await resilience.execute_with_circuit_breaker(
    service="openai",
    operation=lambda: call_openai_api(),
    fallback=lambda: return_cached_response()
)
```

### Fallback Chain

Multiple fallback options:

```python
chain = resilience.create_fallback_chain()

chain.add(
    lambda: primary_llm_call(),
    name="primary",
    priority=3
)
chain.add(
    lambda: fallback_llm_call(),
    name="fallback",
    priority=2
)
chain.add(
    lambda: cached_response(),
    name="cache",
    priority=1
)
chain.add(
    lambda: extractive_answer(),
    name="extractive",
    priority=0
)

result, source = await chain.execute()
```

### Rate Limiting

```python
# Check before request
allowed, reason = await resilience.check_rate_limit(
    estimated_cost=0.05,
    user_id="user-123"
)

if not allowed:
    print(f"Rate limited: {reason}")
```

### Dead Letter Queue

Failed operations are queued for retry:

```python
# Queue a failed operation
entry_id = await resilience.queue_failed_operation(
    operation_name="synthesis",
    args={"query": "..."},
    kwargs={},
    error=error
)

# Retry later
success, message = await resilience.retry_failed_operation(entry_id)
```

---

## Anomaly Detection

### Real-time Monitoring

```python
from app.services.agent.safety import get_anomaly_detector

detector = get_anomaly_detector()

# Record step execution
await detector.record_step(
    session_id="session-123",
    node="retrieval",
    latency_ms=150,
    cost_usd=0.01,
    tokens_used=1000,
    output="..."
)

# Check for anomalies
anomalies = await detector.check_anomalies(
    session_id="session-123",
    state=current_state,
    output=response
)

for anomaly in anomalies:
    print(f"[{anomaly.severity.value}] {anomaly.type.value}: {anomaly.message}")
```

### Detected Anomalies

| Type | Description | Severity |
|------|-------------|----------|
| RUNAWAY_LOOP | Same state repeated | CRITICAL |
| EXCESSIVE_LATENCY | Step took too long | ERROR |
| COST_SPIKE | Unexpected cost increase | ERROR |
| QUALITY_DROPOFF | Output quality degraded | WARNING |
| TOKEN_EXPLOSION | Token usage spike | CRITICAL |
| STUCK_STATE | No progress detected | CRITICAL |

### Session Health

```python
health = detector.get_session_health("session-123")

print(f"Status: {health['status']}")
print(f"Overall: {health['overall_health']:.2%}")
print(f"Latency health: {health['latency_health']:.2%}")
print(f"Cost health: {health['cost_health']:.2%}")
```

---

## Context Management

### Sliding Window

```python
from app.services.agent.safety import get_context_manager, ContextPriority

manager = get_context_manager()

# Add context with priority
await manager.add(
    "session-123",
    "user",
    "Câu hỏi lịch sử...",
    priority=ContextPriority.HIGH
)

# Get optimized prompt context
context = await manager.get_prompt_context(
    "session-123",
    max_tokens=4000
)

# Force compaction
await manager.compact_to_tokens("session-123", target_tokens=2000)
```

### Priority Levels

- **CRITICAL (3)**: System instructions
- **HIGH (2)**: User queries, key facts
- **MEDIUM (1)**: Assistant responses
- **LOW (0)**: Metadata, filler

---

## A2A Protocol

Agent-to-Agent communication standard:

```python
from app.services.agent.a2a import get_a2a_protocol, get_retrieval_agent_card

protocol = get_a2a_protocol()

# Register agent
await protocol.register_agent(get_retrieval_agent_card())

# Discover agents
agents = await protocol.discover_agents(capability="search")

# Delegate task
task, result = await protocol.delegate_task(
    agent_id="retrieval_agent",
    task_type="search",
    input_data={"query": "Vietnam War"},
    wait_for_result=True
)

# Broadcast to multiple agents
results = await protocol.broadcast(
    sender_id="orchestrator",
    task_type="analyze",
    input_data={"content": "..."},
    required_capabilities=["analysis"]
)
```

### Agent Cards

Pre-built agent metadata:

```python
from app.services.agent.a2a import (
    get_retrieval_agent_card,
    get_timeline_agent_card,
    get_graph_agent_card,
    get_synthesizer_agent_card
)

# Use pre-built cards
retrieval_card = get_retrieval_agent_card()
print(f"Capabilities: {retrieval_card.capabilities}")
```

---

## Safe LangGraph

Safety-wrapped agent graph:

```python
from app.services.agent.safety.safe_graph import get_safe_agent_graph

# Use safe graph instead of regular agent_graph
safe_graph = get_safe_agent_graph()

# Execute with all safety features
result = await safe_graph.ainvoke({
    "query": "Chiến dịch Điện Biên Phủ",
    "session_id": "user-session-123",
    "execution_mode": "agentic"
})
```

### Safety Features

- Pre-execution safety checks
- Post-execution monitoring
- Anomaly detection
- Token budget tracking
- Circuit breaker integration
- Output filtering

---

## Configuration

### Environment Variables

```bash
# Agent Safety
AGENT_ENABLE_KILL_SWITCH=true
AGENT_MAX_TOKENS=10000
AGENT_MAX_COST_PER_SESSION=2.00
AGENT_MAX_EXECUTION_SECONDS=120

# Tool Safety
TOOL_ENABLE_INPUT_VALIDATION=true
TOOL_ENABLE_PII_DETECTION=true
TOOL_BLOCK_SQL_INJECTION=true

# Circuit Breaker
CIRCUIT_FAILURE_THRESHOLD=5
CIRCUIT_TIMEOUT_SECONDS=30

# Anomaly Detection
ANOMALY_MAX_LOOP_ITERATIONS=5
ANOMALY_MAX_LATENCY_MS=30000
```

### Programmatic Configuration

```python
from app.services.agent.safety import SafetyConfig, AnomalyConfig

# Agent safety config
safety_config = SafetyConfig(
    enable_kill_switch=True,
    enforce_hard_token_budget=True,
    max_cost_per_session_usd=2.00,
    max_execution_seconds=120,
    enable_loop_detection=True,
    max_consecutive_similar_calls=3,
)

# Anomaly detection config
anomaly_config = AnomalyConfig(
    max_loop_iterations=5,
    max_single_step_latency_ms=30000,
    max_cost_per_step=0.50,
    min_quality_score=0.3,
)

# Tool safety config
tool_config = ToolSafetyConfig(
    enable_input_validation=True,
    block_pii=True,
    block_toxic_content=True,
    pii_detection_enabled=True,
)
```

---

## Monitoring & Observability

### Prometheus Metrics

New safety metrics added:

```python
# Import from metrics module
from app.core.metrics import (
    AGENT_SESSIONS_ACTIVE,
    AGENT_ABORTS_TOTAL,
    AGENT_TOKEN_BUDGET_EXCEEDED,
    AGENT_LOOPS_DETECTED,
    AGENT_COST_USD,
    AGENT_APPROVALS_REQUESTED,
    AGENT_TOOL_CALLS_TOTAL,
    AGENT_CHECKPOINTS_CREATED,
)

# These are automatically tracked
```

### Health Checks

```python
# Get overall system health
health = resilience.get_health_status()
print(f"Status: {health['overall_status']}")

# Get DLQ stats
dlq_stats = resilience.get_dlq_stats()
print(f"Pending: {dlq_stats['pending']}")
print(f"Failed: {dlq_stats['failed']}")
```

### Logging

All safety events are logged:

```python
# Example log entries
logger.warning("agent_session_aborted", session_id=session_id, reason="loop_detected")
logger.error("anomaly_detected", type="runaway_loop", severity="critical")
logger.info("fallback_step_success", step="primary", attempt=1)
```

---

## Testing

Run safety tests:

```bash
cd apps/api
pytest tests/unit/test_agent_safety.py -v
```

Test coverage includes:
- Kill switch functionality
- Token budget tracking
- Circuit breaker states
- Fallback chains
- Anomaly detection
- Context compaction
- PII detection

---

## Future Enhancements

Planned improvements:

1. **Self-improving agents** - Learn from feedback automatically
2. **Agent marketplace** - Share and distribute agent skills
3. **Progressive tool disclosure** - Reveal tools gradually
4. **Advanced cost optimization** - Dynamic model routing
5. **Federated learning** - Learn from distributed agents

---

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Anthropic Agent Best Practices](https://docs.anthropic.com/)
- [A2A Protocol Specification](https://github.com/anthropics/a2a)
- [RAGAS Evaluation Framework](https://docs.ragas.io/)
