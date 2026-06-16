"""Agent-to-Agent (A2A) Protocol Implementation for Multi-Agent Systems.

This module implements the A2A protocol for inter-agent communication:
- Agent discovery and capability advertisement
- Task delegation and routing
- Message passing between agents
- Response aggregation
- Protocol standards compliance

Usage:
    from app.services.agent.a2a import A2AProtocol, AgentCard, AgentClient
    
    # Create agent card
    card = AgentCard(
        name="retrieval_agent",
        capabilities=["search", "embed"],
        endpoint="/agents/retrieval"
    )
    
    # Register agent
    protocol.register_agent(card)
    
    # Send task to agent
    result = await protocol.send_task("retrieval_agent", task)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from uuid import UUID, uuid4

from app.core.logging import get_logger

logger = get_logger("a2a_protocol")


class TaskStatus(Enum):
    """Status of an A2A task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(Enum):
    """A2A message types."""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    TASK_CANCEL = "task_cancel"
    AGENT_DISCOVERY = "agent_discovery"
    AGENT_REGISTER = "agent_register"
    HEARTBEAT = "heartbeat"


@dataclass
class Capability:
    """Agent capability description."""
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    examples: list[dict] = field(default_factory=list)


@dataclass
class AgentCard:
    """Agent Card - metadata about an agent for discovery."""
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    capabilities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    endpoint: str = ""
    supported_protocols: list[str] = field(default_factory=lambda: ["a2a-v1"])
    
    # Provider info
    provider: str = "historiai"
    organization: str = ""
    
    # Capabilities (detailed)
    detailed_capabilities: list[Capability] = field(default_factory=list)
    
    # Metadata
    metadata: dict = field(default_factory=dict)
    
    def matches_capability(self, capability: str) -> bool:
        """Check if agent supports a capability."""
        return capability in self.capabilities
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": self.capabilities,
            "tags": self.tags,
            "endpoint": self.endpoint,
            "supported_protocols": self.supported_protocols,
            "provider": self.provider,
            "organization": self.organization,
            "detailed_capabilities": [
                {
                    "name": c.name,
                    "description": c.description,
                    "input_schema": c.input_schema,
                    "output_schema": c.output_schema,
                }
                for c in self.detailed_capabilities
            ],
            "metadata": self.metadata,
        }


@dataclass
class Task:
    """A2A Task - work to be done by an agent."""
    id: str
    type: str
    agent_id: str  # Target agent
    status: TaskStatus = TaskStatus.PENDING
    
    # Task data
    input_data: dict = field(default_factory=dict)
    output_data: dict | None = None
    
    # Routing
    priority: int = 0  # Higher = more priority
    timeout_seconds: float = 60.0
    
    # Tracing
    parent_task_id: str | None = None
    correlation_id: str | None = None
    
    # Timing
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    
    # Error handling
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
            "parent_task_id": self.parent_task_id,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "retry_count": self.retry_count,
        }


@dataclass
class Message:
    """A2A Message between agents."""
    id: str
    type: MessageType
    sender_id: str
    receiver_id: str | None = None
    
    # Payload
    payload: dict = field(default_factory=dict)
    
    # Routing
    reply_to: str | None = None
    
    # Metadata
    timestamp: float = field(default_factory=time.time)
    ttl_seconds: float = 300.0  # 5 minutes
    
    def is_expired(self) -> bool:
        """Check if message has expired."""
        return time.time() - self.timestamp > self.ttl_seconds
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "payload": self.payload,
            "reply_to": self.reply_to,
            "timestamp": self.timestamp,
            "ttl_seconds": self.ttl_seconds,
        }


@dataclass
class AgentSkill:
    """Agent skill/package for distribution."""
    id: str
    name: str
    version: str
    description: str
    
    # Skill metadata
    category: str = ""
    tags: list[str] = field(default_factory=list)
    
    # Files (for skill package)
    files: dict[str, str] = field(default_factory=dict)  # filename -> content
    
    # Configuration
    config_schema: dict = field(default_factory=dict)
    default_config: dict = field(default_factory=dict)
    
    # Dependencies
    required_capabilities: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "config_schema": self.config_schema,
            "default_config": self.default_config,
            "required_capabilities": self.required_capabilities,
        }


class A2AProtocol:
    """
    Agent-to-Agent Protocol Implementation.
    
    Features:
    - Agent discovery and registration
    - Task routing and delegation
    - Message passing with guaranteed delivery
    - Response aggregation
    - Skill distribution
    
    Architecture:
    - Agent Registry: tracks all available agents
    - Message Queue: handles async message passing
    - Task Manager: coordinates multi-agent tasks
    - Skill Catalog: manages agent capabilities
    """
    
    def __init__(self):
        self._agents: dict[str, AgentCard] = {}
        self._agent_handlers: dict[str, Callable] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._tasks: dict[str, Task] = {}
        self._skills: dict[str, AgentSkill] = {}
        self._lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
        }
        
        # Start message processor
        self._processor_task = asyncio.create_task(self._process_messages())
    
    async def shutdown(self) -> None:
        """Shutdown the protocol."""
        self._processor_task.cancel()
        try:
            await self._processor_task
        except asyncio.CancelledError:
            pass
    
    # ─── Agent Registry ────────────────────────────────────────────────────
    
    async def register_agent(self, card: AgentCard) -> None:
        """Register an agent with the protocol."""
        async with self._lock:
            self._agents[card.id] = card
            logger.info("agent_registered", agent_id=card.id, name=card.name)
    
    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        async with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                logger.info("agent_unregistered", agent_id=agent_id)
    
    async def discover_agents(
        self,
        capability: str | None = None,
        tag: str | None = None,
    ) -> list[AgentCard]:
        """Discover agents matching criteria."""
        results = []
        
        async with self._lock:
            for agent in self._agents.values():
                if capability and not agent.matches_capability(capability):
                    continue
                if tag and tag not in agent.tags:
                    continue
                results.append(agent)
        
        return results
    
    async def get_agent(self, agent_id: str) -> AgentCard | None:
        """Get agent by ID."""
        async with self._lock:
            return self._agents.get(agent_id)
    
    # ─── Agent Handlers ──────────────────────────────────────────────────
    
    async def register_handler(
        self,
        agent_id: str,
        handler: Callable[[Task], Any]
    ) -> None:
        """Register a handler for an agent."""
        self._agent_handlers[agent_id] = handler
        logger.info("agent_handler_registered", agent_id=agent_id)
    
    async def unregister_handler(self, agent_id: str) -> None:
        """Unregister a handler."""
        if agent_id in self._agent_handlers:
            del self._agent_handlers[agent_id]
    
    # ─── Task Management ─────────────────────────────────────────────────
    
    async def create_task(
        self,
        agent_id: str,
        task_type: str,
        input_data: dict,
        priority: int = 0,
        timeout: float = 60.0,
        parent_task_id: str | None = None,
    ) -> Task:
        """Create a new task for an agent."""
        task = Task(
            id=str(uuid4()),
            type=task_type,
            agent_id=agent_id,
            input_data=input_data,
            priority=priority,
            timeout_seconds=timeout,
            parent_task_id=parent_task_id,
            correlation_id=hashlib.md5(
                f"{agent_id}:{task_type}:{time.time()}".encode()
            ).hexdigest()[:8],
        )
        
        async with self._lock:
            self._tasks[task.id] = task
        
        logger.info(
            "task_created",
            task_id=task.id,
            agent_id=agent_id,
            type=task_type,
        )
        
        return task
    
    async def submit_task(self, task: Task) -> None:
        """Submit a task to the queue."""
        # Queue message for processing
        message = Message(
            id=str(uuid4()),
            type=MessageType.TASK_REQUEST,
            sender_id="protocol",
            receiver_id=task.agent_id,
            payload={"task": task.to_dict()},
        )
        
        await self._message_queue.put(message)
        self._stats["messages_sent"] += 1
        
        logger.debug("task_submitted", task_id=task.id)
    
    async def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        async with self._lock:
            return self._tasks.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        async with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = TaskStatus.CANCELLED
                
                # Send cancel message
                message = Message(
                    id=str(uuid4()),
                    type=MessageType.TASK_CANCEL,
                    sender_id="protocol",
                    receiver_id=task.agent_id,
                    payload={"task_id": task_id},
                )
                asyncio.create_task(self._message_queue.put(message))
                
                logger.info("task_cancelled", task_id=task_id)
                return True
        return False
    
    # ─── Message Processing ─────────────────────────────────────────────
    
    async def _process_messages(self) -> None:
        """Process messages from the queue."""
        while True:
            try:
                message = await self._message_queue.get()
                
                if message.is_expired():
                    logger.warning("message_expired", message_id=message.id)
                    continue
                
                await self._handle_message(message)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("message_processing_error", error=str(e))
    
    async def _handle_message(self, message: Message) -> None:
        """Handle an incoming message."""
        self._stats["messages_received"] += 1
        
        if message.type == MessageType.TASK_REQUEST:
            await self._handle_task_request(message)
        elif message.type == MessageType.TASK_RESPONSE:
            await self._handle_task_response(message)
        elif message.type == MessageType.AGENT_DISCOVERY:
            await self._handle_discovery(message)
        elif message.type == MessageType.HEARTBEAT:
            await self._handle_heartbeat(message)
    
    async def _handle_task_request(self, message: Message) -> None:
        """Handle a task request."""
        task_data = message.payload.get("task", {})
        task_id = task_data.get("id")
        
        if not task_id or task_id not in self._tasks:
            return
        
        task = self._tasks[task_id]
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = time.time()
        
        # Find handler
        handler = self._agent_handlers.get(task.agent_id)
        
        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"No handler for agent {task.agent_id}"
            self._stats["tasks_failed"] += 1
            return
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                handler(task),
                timeout=task.timeout_seconds
            )
            
            task.output_data = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            self._stats["tasks_completed"] += 1

            logger.info("task_completed", task_id=task_id)

            # Schedule task removal after 5 minutes to allow result retrieval
            asyncio.get_event_loop().call_later(300, lambda tid=task_id: self._tasks.pop(tid, None))
            
        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.error = f"Task timed out after {task.timeout_seconds}s"
            self._stats["tasks_failed"] += 1
            
            logger.warning("task_timeout", task_id=task_id)
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self._stats["tasks_failed"] += 1
            
            logger.error("task_failed", task_id=task_id, error=str(e))
    
    async def _handle_task_response(self, message: Message) -> None:
        """Handle a task response."""
        # Update task with response
        task_data = message.payload.get("task", {})
        task_id = task_data.get("id")
        
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.output_data = task_data.get("output_data")
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            asyncio.get_running_loop().call_later(300, lambda tid=task_id: self._tasks.pop(tid, None))
    
    async def _handle_discovery(self, message: Message) -> None:
        """Handle discovery request."""
        capability = message.payload.get("capability")
        tag = message.payload.get("tag")
        
        agents = await self.discover_agents(capability, tag)
        
        # Send response
        response = Message(
            id=str(uuid4()),
            type=MessageType.AGENT_DISCOVERY,
            sender_id="protocol",
            receiver_id=message.sender_id,
            reply_to=message.id,
            payload={"agents": [a.to_dict() for a in agents]},
        )
        
        await self._message_queue.put(response)
    
    async def _handle_heartbeat(self, message: Message) -> None:
        """Handle heartbeat."""
        # Agents send heartbeats to indicate they're alive
        logger.debug("heartbeat_received", from_agent=message.sender_id)
    
    # ─── High-Level Operations ────────────────────────────────────────────
    
    async def delegate_task(
        self,
        agent_id: str,
        task_type: str,
        input_data: dict,
        wait_for_result: bool = True,
        timeout: float = 60.0,
    ) -> tuple[Task, dict | None]:
        """
        Delegate a task to an agent.
        
        Args:
            agent_id: Target agent ID
            task_type: Type of task
            input_data: Task input
            wait_for_result: If True, wait for result
            timeout: Timeout in seconds
            
        Returns:
            (task, result) if wait_for_result, else (task, None)
        """
        task = await self.create_task(
            agent_id=agent_id,
            task_type=task_type,
            input_data=input_data,
            timeout=timeout,
        )
        
        await self.submit_task(task)
        
        if wait_for_result:
            result = await self._wait_for_task(task.id, timeout)
            return task, result
        
        return task, None
    
    async def _wait_for_task(
        self,
        task_id: str,
        timeout: float
    ) -> dict | None:
        """Wait for task completion."""
        start = time.time()
        
        while time.time() - start < timeout:
            task = await self.get_task(task_id)
            
            if not task:
                return None
            
            if task.status == TaskStatus.COMPLETED:
                return task.output_data
            
            if task.status in (TaskStatus.FAILED, TaskStatus.CANCELLED):
                return None
            
            await asyncio.sleep(0.1)

        logger.warning("task_wait_timeout", task_id=task_id, timeout=timeout)
        return None
    
    async def broadcast(
        self,
        sender_id: str,
        task_type: str,
        input_data: dict,
        required_capabilities: list[str] | None = None,
    ) -> list[tuple[AgentCard, dict]]:
        """
        Broadcast a task to all matching agents.
        
        Returns list of (agent, result) tuples.
        """
        # Find matching agents
        if required_capabilities:
            agents = []
            for cap in required_capabilities:
                agents.extend(await self.discover_agents(capability=cap))
            # Deduplicate
            seen = set()
            unique_agents = []
            for a in agents:
                if a.id not in seen:
                    seen.add(a.id)
                    unique_agents.append(a)
            agents = unique_agents
        else:
            agents = await self.discover_agents()
        
        # Submit tasks to all
        tasks = []
        for agent in agents:
            if agent.id == sender_id:
                continue  # Don't send to self
            
            task = await self.create_task(
                agent_id=agent.id,
                task_type=task_type,
                input_data=input_data,
            )
            await self.submit_task(task)
            tasks.append((agent, task))
        
        # Wait for results
        results = []
        for agent, task in tasks:
            result = await self._wait_for_task(task.id, timeout=30.0)
            results.append((agent, result))
        
        return results
    
    # ─── Skill Catalog ───────────────────────────────────────────────────
    
    async def register_skill(self, skill: AgentSkill) -> None:
        """Register a skill in the catalog."""
        async with self._lock:
            self._skills[skill.id] = skill
            logger.info("skill_registered", skill_id=skill.id, name=skill.name)
    
    async def get_skill(self, skill_id: str) -> AgentSkill | None:
        """Get a skill by ID."""
        async with self._lock:
            return self._skills.get(skill_id)
    
    async def find_skills(
        self,
        category: str | None = None,
        tag: str | None = None,
    ) -> list[AgentSkill]:
        """Find skills matching criteria."""
        results = []
        
        async with self._lock:
            for skill in self._skills.values():
                if category and skill.category != category:
                    continue
                if tag and tag not in skill.tags:
                    continue
                results.append(skill)
        
        return results
    
    # ─── Statistics ──────────────────────────────────────────────────────
    
    def get_stats(self) -> dict:
        """Get protocol statistics."""
        return {
            **self._stats,
            "registered_agents": len(self._agents),
            "active_tasks": sum(
                1 for t in self._tasks.values()
                if t.status == TaskStatus.IN_PROGRESS
            ),
            "pending_tasks": sum(
                1 for t in self._tasks.values()
                if t.status == TaskStatus.PENDING
            ),
            "queue_size": self._message_queue.qsize(),
        }


class A2AClient:
    """
    Client for interacting with A2A Protocol.
    
    Provides a simpler interface for making agent calls.
    """
    
    def __init__(self, protocol: A2AProtocol, agent_id: str):
        self.protocol = protocol
        self.agent_id = agent_id
    
    async def call_agent(
        self,
        target_agent: str,
        task_type: str,
        input_data: dict,
        timeout: float = 60.0,
    ) -> dict | None:
        """Call another agent and get result."""
        task, result = await self.protocol.delegate_task(
            agent_id=target_agent,
            task_type=task_type,
            input_data=input_data,
            wait_for_result=True,
            timeout=timeout,
        )
        return result
    
    async def find_agent(
        self,
        capability: str | None = None,
    ) -> list[AgentCard]:
        """Find agents by capability."""
        return await self.protocol.discover_agents(capability=capability)


# ─── Pre-built Agent Cards ───────────────────────────────────────────────────

def get_retrieval_agent_card() -> AgentCard:
    """Get agent card for retrieval agent."""
    return AgentCard(
        id="retrieval_agent",
        name="Retrieval Agent",
        description="Handles document retrieval and search",
        capabilities=["search", "embed", "retrieve", "rerank"],
        tags=["retrieval", "search", "rag"],
        endpoint="/agents/retrieval",
        detailed_capabilities=[
            Capability(
                name="hybrid_search",
                description="Perform hybrid search with BM25 and vector",
                input_schema={"query": "string", "top_k": "integer"},
                output_schema={"chunks": "array"},
            ),
            Capability(
                name="embed",
                description="Generate embeddings for text",
                input_schema={"text": "string"},
                output_schema={"embedding": "array"},
            ),
        ],
    )


def get_timeline_agent_card() -> AgentCard:
    """Get agent card for timeline agent."""
    return AgentCard(
        id="timeline_agent",
        name="Timeline Agent",
        description="Handles temporal queries and chronology",
        capabilities=["timeline", "chronology", "events", "dates"],
        tags=["timeline", "history", "events"],
        endpoint="/agents/timeline",
        detailed_capabilities=[
            Capability(
                name="get_events",
                description="Get historical events by date range",
                input_schema={"start_year": "integer", "end_year": "integer"},
                output_schema={"events": "array"},
            ),
        ],
    )


def get_graph_agent_card() -> AgentCard:
    """Get agent card for graph agent."""
    return AgentCard(
        id="graph_agent",
        name="Graph Agent",
        description="Handles entity relationships and knowledge graph",
        capabilities=["graph", "entities", "relationships", "neo4j"],
        tags=["graph", "knowledge", "entities"],
        endpoint="/agents/graph",
        detailed_capabilities=[
            Capability(
                name="get_neighbors",
                description="Get neighboring entities",
                input_schema={"entity_id": "string", "depth": "integer"},
                output_schema={"neighbors": "array"},
            ),
        ],
    )


def get_synthesizer_agent_card() -> AgentCard:
    """Get agent card for synthesizer agent."""
    return AgentCard(
        id="synthesizer_agent",
        name="Synthesizer Agent",
        description="Synthesizes final responses from agent outputs",
        capabilities=["synthesize", "generate", "cite"],
        tags=["synthesis", "generation", "llm"],
        endpoint="/agents/synthesizer",
        detailed_capabilities=[
            Capability(
                name="synthesize",
                description="Generate final answer with citations",
                input_schema={
                    "query": "string",
                    "chunks": "array",
                    "context": "object",
                },
                output_schema={
                    "answer": "string",
                    "citations": "array",
                },
            ),
        ],
    )


# ─── Global Protocol Instance ────────────────────────────────────────────────

_protocol_instance: A2AProtocol | None = None


def get_a2a_protocol() -> A2AProtocol:
    """Get the global A2A protocol instance."""
    global _protocol_instance
    if _protocol_instance is None:
        _protocol_instance = A2AProtocol()
    return _protocol_instance


async def init_a2a_protocol() -> A2AProtocol:
    """Initialize and configure the A2A protocol."""
    protocol = get_a2a_protocol()
    
    # Register default agents
    await protocol.register_agent(get_retrieval_agent_card())
    await protocol.register_agent(get_timeline_agent_card())
    await protocol.register_agent(get_graph_agent_card())
    await protocol.register_agent(get_synthesizer_agent_card())
    
    return protocol


async def shutdown_a2a_protocol() -> None:
    """Shutdown the A2A protocol."""
    global _protocol_instance
    if _protocol_instance:
        await _protocol_instance.shutdown()
        _protocol_instance = None
