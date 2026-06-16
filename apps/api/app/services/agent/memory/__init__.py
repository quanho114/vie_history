"""5-tier Memory Architecture for Agentic AI Systems.

This module implements a comprehensive memory hierarchy following the 2026 best practices:
1. Short-term (Working) - Current execution context
2. Episodic - Past conversation turns in current session
3. Semantic - Vector-stored knowledge and facts
4. Procedural - Learned agent behaviors and skills
5. Observational - Learned patterns and feedback

Usage:
    from app.services.agent.memory import AgentMemory, get_agent_memory
    
    memory = get_agent_memory()
    
    # Store a turn
    await memory.add_turn(session_id, role="user", content="question...")
    
    # Retrieve relevant memories
    memories = await memory.retrieve(session_id, query="historical events")
    
    # Compact when context is full
    await memory.maybe_compact(session_id)
"""

from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

from app.core.cache import cache
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("agent_memory")


T = TypeVar("T")


class MemoryTier(Enum):
    """Memory tier identifiers."""
    SHORT_TERM = "short_term"      # Working context
    EPISODIC = "episodic"          # Past turns
    SEMANTIC = "semantic"          # Vector knowledge
    PROCEDURAL = "procedural"       # Learned behaviors
    OBSERVATIONAL = "observational" # Learned patterns


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    tier: MemoryTier
    content: str
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    importance: float = 1.0  # 0.0 - 1.0
    
    def access(self) -> None:
        """Record access."""
        self.access_count += 1
        self.last_accessed = time.time()
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tier": self.tier.value,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "importance": self.importance,
        }


@dataclass
class Turn:
    """A single conversation turn."""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class MemoryConfig:
    """Memory system configuration."""
    # Short-term (working context)
    max_short_term_items: int = 50
    max_short_term_chars: int = 8000
    
    # Episodic (conversation history)
    max_episodic_turns: int = 100
    max_episodic_chars: int = 50000
    
    # Semantic (vector knowledge)
    semantic_top_k: int = 10
    semantic_similarity_threshold: float = 0.7
    
    # Compaction
    auto_compact_threshold: float = 0.8  # 80% of max context
    compaction_ratio: float = 0.5  # Compress to 50%
    min_compaction_interval_seconds: int = 60
    
    # Importance decay
    decay_rate: float = 0.95  # Importance multiplier per access
    min_importance: float = 0.1
    
    # Relevance decay
    relevance_decay_hours: float = 24.0


class BaseMemoryStore(ABC, Generic[T]):
    """Abstract base for memory stores."""
    
    @abstractmethod
    async def add(self, entry: T) -> str:
        """Add an entry to the store."""
        pass
    
    @abstractmethod
    async def get(self, id: str) -> T | None:
        """Get an entry by ID."""
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[T]:
        """Search entries."""
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete an entry."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all entries."""
        pass


class ShortTermMemory:
    """
    Tier 1: Short-term / Working Memory
    
    Holds the current execution context:
    - Current query and intent
    - Active retrieval results
    - Node execution state
    - Tool call stack
    
    Very fast, ephemeral, cleared per task.
    """
    
    def __init__(self, config: MemoryConfig | None = None):
        self.config = config or MemoryConfig()
        self._items: dict[str, Any] = {}
    
    async def set(self, key: str, value: Any) -> None:
        """Set a working memory item."""
        self._items[key] = value
        
        # Enforce size limit
        if len(self._items) > self.config.max_short_term_items:
            # Remove oldest items
            sorted_items = sorted(
                self._items.items(),
                key=lambda x: getattr(x[1], "created_at", time.time()) if hasattr(x[1], "created_at") else time.time()
            )
            self._items = dict(sorted_items[:self.config.max_short_term_items // 2])
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a working memory item."""
        return self._items.get(key, default)
    
    async def delete(self, key: str) -> bool:
        """Delete a working memory item."""
        if key in self._items:
            del self._items[key]
            return True
        return False
    
    async def clear(self) -> None:
        """Clear all working memory."""
        self._items.clear()
    
    def to_dict(self) -> dict:
        """Export as dictionary."""
        return self._items.copy()

    @classmethod
    def from_dict(cls, data: dict, config: MemoryConfig | None = None) -> "ShortTermMemory":
        """Restore from dictionary."""
        instance = cls(config)
        instance._items = dict(data) if data else {}
        return instance

    def __len__(self) -> int:
        return len(self._items)


class EpisodicMemory:
    """
    Tier 2: Episodic Memory
    
    Stores conversation history as turns:
    - User queries
    - Assistant responses
    - Tool results
    - System messages
    
    Compressed over time to save context space.
    """
    
    def __init__(self, config: MemoryConfig | None = None):
        self.config = config or MemoryConfig()
        self._turns: list[Turn] = []
    
    async def add_turn(
        self,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> str:
        """Add a conversation turn."""
        turn = Turn(
            role=role,
            content=content[:10000],  # Hard limit
            metadata=metadata or {},
        )
        self._turns.append(turn)
        
        # Enforce size limit
        while len(self._turns) > self.config.max_episodic_turns:
            self._turns.pop(0)  # Remove oldest
        
        return hashlib.md5(
            f"{turn.timestamp}:{role}:{content[:100]}".encode()
        ).hexdigest()
    
    async def get_recent(self, n: int = 10) -> list[Turn]:
        """Get recent turns."""
        return self._turns[-n:]
    
    async def get_all(self) -> list[Turn]:
        """Get all turns."""
        return self._turns.copy()
    
    async def summarize(self, turns: list[Turn] | None = None) -> str:
        """Create a summary of turns."""
        if turns is None:
            turns = self._turns
        
        if not turns:
            return ""
        
        # Simple summarization: extract key information
        summaries = []
        for turn in turns[-10:]:  # Last 10 turns
            preview = turn.content[:200]
            summaries.append(f"[{turn.role}] {preview}...")
        
        return "\n".join(summaries)
    
    async def compact(self, ratio: float = 0.5) -> int:
        """
        Compact memory by keeping every nth turn.
        
        Returns number of turns removed.
        """
        if not self._turns:
            return 0
        
        keep_every = max(1, int(1 / ratio))
        original_count = len(self._turns)
        
        # Keep first turn, then every nth turn
        compacted = [self._turns[0]]
        for i in range(1, len(self._turns)):
            if i % keep_every == 0:
                compacted.append(self._turns[i])
        
        # Add summary turn if we removed middle turns
        if len(compacted) < original_count * ratio:
            summary = Turn(
                role="system",
                content=f"[Compacted summary of {original_count - len(compacted)} turns]",
                metadata={"compacted": True},
            )
            compacted.insert(1, summary)
        
        removed = original_count - len(compacted)
        self._turns = compacted
        
        logger.info("episodic_memory_compacted", removed=removed, remaining=len(compacted))
        return removed
    
    async def clear(self) -> None:
        """Clear all episodic memory."""
        self._turns.clear()
    
    def to_dict(self) -> dict:
        """Export as dictionary."""
        return {
            "turn_count": len(self._turns),
            "turns": [t.to_dict() for t in self._turns[-20:]],  # Last 20
        }

    @classmethod
    def from_dict(cls, data: dict | None, config: MemoryConfig | None = None) -> "EpisodicMemory":
        """Restore from dictionary."""
        instance = cls(config)
        if data and "turns" in data:
            for turn_data in data["turns"]:
                # timestamp is stored as float (Unix timestamp), pass directly to dataclass
                instance._turns.append(Turn(**turn_data))
        return instance


class SemanticMemory:
    """
    Tier 3: Semantic Memory (Vector Store)
    
    Stores structured knowledge:
    - Document summaries
    - Extracted facts
    - Entity relationships
    - Historical events
    
    Retrieved via similarity search.
    """
    
    def __init__(self, config: MemoryConfig | None = None):
        self.config = config or MemoryConfig()
        self._entries: list[MemoryEntry] = []
    
    async def add(
        self,
        content: str,
        metadata: dict | None = None,
        importance: float = 1.0,
    ) -> str:
        """Add a semantic memory entry."""
        entry_id = hashlib.sha256(
            f"{content[:200]}:{time.time()}".encode()
        ).hexdigest()[:16]
        
        entry = MemoryEntry(
            id=entry_id,
            tier=MemoryTier.SEMANTIC,
            content=content,
            metadata=metadata or {},
            importance=importance,
        )
        
        self._entries.append(entry)
        return entry_id
    
    async def get(self, id: str) -> MemoryEntry | None:
        """Get by ID."""
        for entry in self._entries:
            if entry.id == id:
                entry.access()
                return entry
        return None
    
    async def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        """Simple keyword-based search (production would use vectors)."""
        query_lower = query.lower()
        results = []
        
        for entry in self._entries:
            # Simple relevance scoring
            content_lower = entry.content.lower()
            
            # Calculate relevance
            query_words = set(query_lower.split())
            content_words = set(content_lower.split())
            
            if not query_words:
                continue
            
            overlap = len(query_words & content_words)
            relevance = overlap / len(query_words)
            
            # Apply importance boost
            score = relevance * entry.importance
            
            if score > 0:
                results.append((score, entry))
        
        # Sort by score
        results.sort(key=lambda x: x[0], reverse=True)
        
        # Apply similarity threshold
        threshold = self.config.semantic_similarity_threshold
        filtered = [(s, e) for s, e in results if s >= threshold]
        
        # Return entries (without scores)
        return [e for _, e in filtered[:limit]]
    
    async def update_importance(self, id: str, delta: float) -> bool:
        """Update importance score."""
        entry = await self.get(id)
        if entry:
            entry.importance = max(
                self.config.min_importance,
                entry.importance * (1 + delta)
            )
            return True
        return False
    
    async def apply_decay(self, decay_rate: float) -> int:
        """Apply importance decay to all entries."""
        decayed = 0
        for entry in self._entries:
            new_importance = entry.importance * decay_rate
            if new_importance < self.config.min_importance:
                new_importance = self.config.min_importance
            if new_importance != entry.importance:
                entry.importance = new_importance
                decayed += 1
        return decayed
    
    async def clear(self) -> None:
        """Clear all semantic memory."""
        self._entries.clear()
    
    def to_dict(self) -> dict:
        """Export as dictionary."""
        return {
            "entry_count": len(self._entries),
            "entries": [e.to_dict() for e in self._entries[-20:]],
        }

    @classmethod
    def from_dict(cls, data: dict | None, config: MemoryConfig | None = None) -> "SemanticMemory":
        """Restore from dictionary."""
        instance = cls(config)
        if data and "entries" in data:
            for entry_data in data["entries"]:
                # Convert tier string back to enum
                if "tier" in entry_data and isinstance(entry_data["tier"], str):
                    from app.services.agent.memory import MemoryTier
                    entry_data = {**entry_data, "tier": MemoryTier(entry_data["tier"])}
                instance._entries.append(MemoryEntry(**entry_data))
        return instance


class ProceduralMemory:
    """
    Tier 4: Procedural Memory
    
    Stores learned agent behaviors:
    - Prompt templates
    - Tool usage patterns
    - Workflow definitions
    - Response styles
    
    Organized by category and use case.
    """
    
    def __init__(self, config: MemoryConfig | None = None):
        self.config = config or MemoryConfig()
        self._procedures: dict[str, dict[str, Any]] = {}
        self._patterns: dict[str, list[str]] = {}  # category -> patterns
    
    async def add_procedure(
        self,
        name: str,
        category: str,
        template: str,
        metadata: dict | None = None,
    ) -> str:
        """Add a procedure."""
        procedure_id = hashlib.sha256(
            f"{name}:{category}:{time.time()}".encode()
        ).hexdigest()[:16]
        
        self._procedures[procedure_id] = {
            "id": procedure_id,
            "name": name,
            "category": category,
            "template": template,
            "metadata": metadata or {},
            "usage_count": 0,
            "created_at": time.time(),
        }
        
        # Add to patterns index
        if category not in self._patterns:
            self._patterns[category] = []
        self._patterns[category].append(procedure_id)
        
        return procedure_id
    
    async def get_procedure(self, id: str) -> dict | None:
        """Get a procedure by ID."""
        if id in self._procedures:
            proc = self._procedures[id]
            proc["usage_count"] += 1
            return proc
        return None
    
    async def get_by_category(self, category: str) -> list[dict]:
        """Get all procedures in a category."""
        if category not in self._patterns:
            return []
        return [
            self._procedures[pid]
            for pid in self._patterns[category]
            if pid in self._procedures
        ]
    
    async def find_matching(
        self,
        query: str,
        category: str | None = None,
    ) -> list[dict]:
        """Find procedures matching a query."""
        query_lower = query.lower()
        results = []
        
        for proc_id, proc in self._procedures.items():
            if category and proc["category"] != category:
                continue
            
            # Simple matching on name and template
            content = f"{proc['name']} {proc['template']}".lower()
            if query_lower in content:
                results.append(proc)
        
        # Sort by usage count
        results.sort(key=lambda x: x["usage_count"], reverse=True)
        return results
    
    async def clear(self) -> None:
        """Clear all procedural memory."""
        self._procedures.clear()
        self._patterns.clear()
    
    def to_dict(self) -> dict:
        """Export as dictionary."""
        return {
            "procedure_count": len(self._procedures),
            "procedures": self._procedures,
            "patterns": self._patterns,
        }

    @classmethod
    def from_dict(cls, data: dict | None, config: MemoryConfig | None = None) -> "ProceduralMemory":
        """Restore from dictionary."""
        instance = cls(config)
        if data:
            instance._procedures = data.get("procedures", {})
            instance._patterns = data.get("patterns", {})
        return instance


class ObservationalMemory:
    """
    Tier 5: Observational Memory
    
    Stores learned patterns from feedback:
    - User preferences
    - Response quality feedback
    - Error patterns
    - Success patterns
    
    Enables self-improvement over time.
    """
    
    def __init__(self, config: MemoryConfig | None = None):
        self.config = config or MemoryConfig()
        self._observations: list[dict] = []
        self._feedback_patterns: dict[str, float] = {}  # pattern -> score
        self._user_preferences: dict[str, dict] = {}  # user_id -> preferences
    
    async def record_feedback(
        self,
        session_id: str,
        query: str,
        response: str,
        rating: float,  # 0.0 - 1.0
        feedback: str | None = None,
    ) -> str:
        """Record user feedback on a response."""
        observation_id = hashlib.sha256(
            f"{session_id}:{query}:{time.time()}".encode()
        ).hexdigest()[:16]
        
        observation = {
            "id": observation_id,
            "session_id": session_id,
            "query": query,
            "response": response,
            "rating": rating,
            "feedback": feedback,
            "timestamp": time.time(),
        }
        
        self._observations.append(observation)
        
        # Update feedback patterns
        query_key = query[:100].lower()  # Normalize
        if query_key not in self._feedback_patterns:
            self._feedback_patterns[query_key] = rating
        else:
            # Exponential moving average
            self._feedback_patterns[query_key] = (
                0.7 * self._feedback_patterns[query_key] + 0.3 * rating
            )
        
        # Keep only recent observations
        if len(self._observations) > 1000:
            self._observations = self._observations[-500:]
        
        return observation_id
    
    async def record_success(
        self,
        pattern: str,
        context: dict,
    ) -> None:
        """Record a successful agent behavior pattern."""
        observation = {
            "type": "success",
            "pattern": pattern,
            "context": context,
            "timestamp": time.time(),
        }
        self._observations.append(observation)
    
    async def record_error(
        self,
        error_type: str,
        error_message: str,
        context: dict,
    ) -> None:
        """Record an error pattern."""
        observation = {
            "type": "error",
            "error_type": error_type,
            "error_message": error_message,
            "context": context,
            "timestamp": time.time(),
        }
        self._observations.append(observation)
        
        # Update error patterns
        if error_type not in self._feedback_patterns:
            self._feedback_patterns[error_type] = 0.0
        # Decay score
        self._feedback_patterns[error_type] *= 0.9
    
    async def get_user_preference(
        self,
        user_id: str,
        preference_key: str,
        default: Any = None,
    ) -> Any:
        """Get a user preference."""
        if user_id in self._user_preferences:
            return self._user_preferences[user_id].get(preference_key, default)
        return default
    
    async def set_user_preference(
        self,
        user_id: str,
        preference_key: str,
        value: Any,
    ) -> None:
        """Set a user preference."""
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = {}
        self._user_preferences[user_id][preference_key] = value
    
    async def get_average_rating(self) -> float:
        """Get average rating of recent observations."""
        ratings = [
            o["rating"] for o in self._observations[-100:]
            if "rating" in o
        ]
        if not ratings:
            return 0.5
        return sum(ratings) / len(ratings)
    
    async def get_pattern_score(self, pattern: str) -> float:
        """Get score for a pattern."""
        return self._feedback_patterns.get(pattern, 0.5)
    
    async def clear(self) -> None:
        """Clear all observational memory."""
        self._observations.clear()
        self._feedback_patterns.clear()
        self._user_preferences.clear()
    
    def to_dict(self) -> dict:
        """Export as dictionary."""
        return {
            "observation_count": len(self._observations),
            "observations": self._observations,
            "feedback_patterns": self._feedback_patterns,
            "user_preferences": self._user_preferences,
        }

    @classmethod
    def from_dict(cls, data: dict | None, config: MemoryConfig | None = None) -> "ObservationalMemory":
        """Restore from dictionary."""
        instance = cls(config)
        if data:
            instance._observations = data.get("observations", [])
            instance._feedback_patterns = data.get("feedback_patterns", {})
            instance._user_preferences = data.get("user_preferences", {})
        return instance


class AgentMemory:
    """
    Complete 5-tier Memory System for Agentic AI.
    
    Integrates all memory tiers into a unified interface:
    - ShortTerm: Working context
    - Episodic: Conversation history
    - Semantic: Vector knowledge
    - Procedural: Learned behaviors
    - Observational: Feedback patterns
    
    Handles:
    - Memory allocation and limits
    - Cross-tier retrieval
    - Automatic compaction
    - Persistence (via Redis)
    """
    
    def __init__(self, config: MemoryConfig | None = None):
        self.config = config or MemoryConfig()
        
        # Initialize all tiers
        self.short_term = ShortTermMemory(self.config)
        self.episodic = EpisodicMemory(self.config)
        self.semantic = SemanticMemory(self.config)
        self.procedural = ProceduralMemory(self.config)
        self.observational = ObservationalMemory(self.config)
        
        # Compaction tracking
        self._last_compaction: dict[str, float] = {}
        self._compaction_count: dict[str, int] = {}
    
    # ─── Session Management ───────────────────────────────────────────────────
    
    async def init_session(self, session_id: str) -> None:
        """Initialize memory for a session, restoring from cache if available."""
        cached = await cache.get(f"memory:session:{session_id}")
        if cached:
            if cached.get("short_term"):
                self.short_term = ShortTermMemory.from_dict(cached["short_term"], self.config)
            if cached.get("episodic"):
                # Restore episodic turns
                turns_data = cached["episodic"].get("turns", [])
                self.episodic = EpisodicMemory.from_dict(cached["episodic"], self.config)
            if cached.get("semantic"):
                self.semantic = SemanticMemory.from_dict(cached["semantic"], self.config)
            if cached.get("procedural"):
                self.procedural = ProceduralMemory.from_dict(cached["procedural"], self.config)
            if cached.get("observational"):
                self.observational = ObservationalMemory.from_dict(cached["observational"], self.config)
            if cached.get("config"):
                self._last_compaction[session_id] = cached["config"].get("last_compaction")
                self._compaction_count[session_id] = cached["config"].get("compaction_count", 0)
            logger.info("memory_session_loaded", session_id=session_id)

    async def save_session(self, session_id: str) -> None:
        """Persist session memory to cache."""
        state = {
            "short_term": self.short_term.to_dict(),
            "episodic": self.episodic.to_dict(),
            "semantic": self.semantic.to_dict(),
            "procedural": self.procedural.to_dict(),
            "observational": self.observational.to_dict(),
            "config": {
                "last_compaction": self._last_compaction.get(session_id),
                "compaction_count": self._compaction_count.get(session_id, 0),
            },
        }
        await cache.set(f"memory:session:{session_id}", state, ttl=86400)  # 24 hours
    
    async def clear_session(self, session_id: str) -> None:
        """Clear memory for a session."""
        await self.short_term.clear()
        await self.episodic.clear()
        
        # Clear session-specific tracking
        self._last_compaction.pop(session_id, None)
        self._compaction_count.pop(session_id, None)
        
        await cache.delete(f"memory:session:{session_id}")
        logger.info("memory_session_cleared", session_id=session_id)
    
    # ─── Turn Management ──────────────────────────────────────────────────────
    
    async def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> str:
        """Add a conversation turn to episodic memory."""
        return await self.episodic.add_turn(role, content, metadata)
    
    async def get_conversation_context(
        self,
        session_id: str,
        max_turns: int = 20,
    ) -> list[Turn]:
        """Get conversation context for prompt building."""
        turns = await self.episodic.get_recent(max_turns)
        
        # Check if we need to compact
        total_chars = sum(len(t.content) for t in turns)
        if total_chars > self.config.max_episodic_chars * self.config.auto_compact_threshold:
            await self.maybe_compact(session_id)
            turns = await self.episodic.get_recent(max_turns)
        
        return turns
    
    # ─── Knowledge Management ─────────────────────────────────────────────────
    
    async def store_knowledge(
        self,
        content: str,
        metadata: dict | None = None,
        importance: float = 1.0,
    ) -> str:
        """Store a fact in semantic memory."""
        return await self.semantic.add(content, metadata, importance)
    
    async def retrieve_knowledge(
        self,
        query: str,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Retrieve relevant knowledge from semantic memory."""
        return await self.semantic.search(query, limit)
    
    # ─── Compaction ──────────────────────────────────────────────────────────
    
    async def maybe_compact(
        self,
        session_id: str,
        force: bool = False,
    ) -> bool:
        """
        Check and perform compaction if needed.
        
        Returns True if compaction was performed.
        """
        now = time.time()
        last_compaction = self._last_compaction.get(session_id, 0)
        
        # Check minimum interval
        if not force and (now - last_compaction) < self.config.min_compaction_interval_seconds:
            return False
        
        # Check if compaction is needed
        turns = await self.episodic.get_all()
        total_chars = sum(len(t.content) for t in turns)
        
        if total_chars < self.config.max_episodic_chars * self.config.auto_compact_threshold:
            return False
        
        # Perform compaction
        removed = await self.episodic.compact(self.config.compaction_ratio)
        
        if removed > 0:
            self._last_compaction[session_id] = now
            self._compaction_count[session_id] = self._compaction_count.get(session_id, 0) + 1
            
            logger.info(
                "memory_compacted",
                session_id=session_id,
                turns_removed=removed,
                remaining=len(turns) - removed,
            )
            
            return True
        
        return False
    
    # ─── Cross-tier Operations ────────────────────────────────────────────────
    
    async def retrieve_all(
        self,
        session_id: str,
        query: str,
        include_tiers: list[MemoryTier] | None = None,
    ) -> dict[MemoryTier, list]:
        """
        Retrieve from all memory tiers.
        
        Returns dict mapping tier to list of relevant entries.
        """
        if include_tiers is None:
            include_tiers = [
                MemoryTier.SHORT_TERM,
                MemoryTier.EPISODIC,
                MemoryTier.SEMANTIC,
            ]
        
        results: dict[MemoryTier, list] = {}
        
        # Short-term: return all items
        if MemoryTier.SHORT_TERM in include_tiers:
            results[MemoryTier.SHORT_TERM] = [self.short_term.to_dict()]
        
        # Episodic: search by keywords
        if MemoryTier.EPISODIC in include_tiers:
            turns = await self.episodic.get_recent(10)
            query_lower = query.lower()
            relevant = [
                t for t in turns
                if query_lower in t.content.lower()
            ]
            results[MemoryTier.EPISODIC] = relevant
        
        # Semantic: vector similarity search
        if MemoryTier.SEMANTIC in include_tiers:
            results[MemoryTier.SEMANTIC] = await self.semantic.search(query)
        
        return results
    
    async def build_context_prompt(
        self,
        session_id: str,
        query: str,
        max_chars: int = 8000,
    ) -> str:
        """
        Build a context prompt from all memory tiers.
        
        Optimized for LLM consumption.
        """
        parts = []
        remaining_chars = max_chars
        
        # Add recent conversation (highest priority)
        turns = await self.episodic.get_recent(10)
        turn_text = ""
        for turn in turns:
            turn_line = f"{turn.role.upper()}: {turn.content[:500]}\n"
            if len(turn_text) + len(turn_line) > remaining_chars * 0.4:  # 40% for history
                break
            turn_text += turn_line
        
        if turn_text:
            parts.append(f"=== CONVERSATION HISTORY ===\n{turn_text}")
            remaining_chars -= len(turn_text)
        
        # Add semantic knowledge
        knowledge = await self.semantic.search(query, limit=5)
        if knowledge:
            knowledge_text = "=== RELEVANT KNOWLEDGE ===\n"
            for entry in knowledge:
                knowledge_text += f"- {entry.content[:300]}\n"
                if len(knowledge_text) > remaining_chars * 0.3:  # 30% for knowledge
                    break
            
            if len(parts[-1] if parts else "") + len(knowledge_text) <= max_chars:
                parts.append(knowledge_text)
                remaining_chars -= len(knowledge_text)
        
        # Add short-term context
        st_context = self.short_term.to_dict()
        if st_context:
            st_text = f"=== CURRENT CONTEXT ===\n"
            for key, value in list(st_context.items())[:5]:
                st_text += f"{key}: {str(value)[:200]}\n"
            
            if len(parts[-1] if parts else "") + len(st_text) <= max_chars:
                parts.append(st_text)
        
        return "\n\n".join(parts) if parts else ""
    
    # ─── Self-improvement ───────────────────────────────────────────────────
    
    async def learn_from_feedback(
        self,
        session_id: str,
        query: str,
        response: str,
        rating: float,
        feedback: str | None = None,
    ) -> None:
        """Learn from user feedback."""
        # Record in observational memory
        await self.observational.record_feedback(
            session_id, query, response, rating, feedback
        )
        
        # Update semantic importance based on feedback
        if rating > 0.8:
            # High rating: boost importance
            knowledge = await self.semantic.search(query, limit=1)
            if knowledge:
                await self.semantic.update_importance(knowledge[0].id, 0.1)
        elif rating < 0.3:
            # Low rating: decrease importance
            knowledge = await self.semantic.search(query, limit=1)
            if knowledge:
                await self.semantic.update_importance(knowledge[0].id, -0.2)
    
    async def get_quality_score(self, session_id: str) -> float:
        """Get overall quality score based on recent feedback."""
        return await self.observational.get_average_rating()
    
    # ─── Utility ─────────────────────────────────────────────────────────────
    
    async def get_memory_stats(self, session_id: str) -> dict:
        """Get memory usage statistics for a session."""
        return {
            "short_term_items": len(self.short_term),
            "episodic_turns": len(await self.episodic.get_all()),
            "semantic_entries": len(self.semantic._entries),
            "compaction_count": self._compaction_count.get(session_id, 0),
            "avg_rating": await self.observational.get_average_rating(),
        }


# ─── Global Instance ─────────────────────────────────────────────────────────

_memory_instance: AgentMemory | None = None


def get_agent_memory() -> AgentMemory:
    """Get the global AgentMemory instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = AgentMemory()
    return _memory_instance


def reset_agent_memory() -> None:
    """Reset the global instance (for testing)."""
    global _memory_instance
    _memory_instance = None
