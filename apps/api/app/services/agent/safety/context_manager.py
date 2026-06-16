"""Context Manager with Sliding Window and Summarization for Agentic AI Systems.

This module provides production-grade context management:
- Sliding window for conversation history
- Automatic summarization when context is full
- Priority-based context retention
- Cross-session context optimization

Usage:
    from app.services.agent.safety import ContextManager, get_context_manager
    
    manager = get_context_manager()
    
    # Add context
    await manager.add("user", "What's about Vietnam war?")
    await manager.add("assistant", "The Vietnam War...")
    
    # Get optimized context for prompt
    context = await manager.get_context(session_id, max_tokens=4000)
    
    # Compact when needed
    await manager.maybe_compact(session_id)
"""

from __future__ import annotations

import hashlib
import time
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.logging import get_logger

logger = get_logger("context_manager")


class ContextPriority(Enum):
    """Priority levels for context items."""
    CRITICAL = 3   # System instructions, constraints
    HIGH = 2      # User queries, key facts
    MEDIUM = 1    # Assistant responses
    LOW = 0       # Metadata, filler


@dataclass
class ContextItem:
    """A single context item."""
    role: str
    content: str
    priority: ContextPriority = ContextPriority.MEDIUM
    tokens: int = 0
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)
    
    def access(self) -> None:
        """Record access."""
        self.access_count += 1
        self.last_accessed = time.time()
    
    def estimate_tokens(self) -> int:
        """Estimate token count (rough approximation)."""
        if self.tokens > 0:
            return self.tokens
        # Rough estimate: ~4 characters per token for Vietnamese/English mix
        return len(self.content) // 4
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "priority": self.priority.name,
            "tokens": self.estimate_tokens(),
            "created_at": self.created_at,
            "access_count": self.access_count,
        }


@dataclass
class ContextConfig:
    """Configuration for context management."""
    # Size limits
    max_total_tokens: int = 8000
    max_items: int = 100
    
    # Summarization
    enable_summarization: bool = True
    summary_trigger_ratio: float = 0.8  # Start summarizing at 80% capacity
    summary_min_tokens: int = 500      # Minimum before summarizing
    
    # Priority thresholds
    auto_promote_threshold: float = 0.8  # Access count ratio to auto-promote
    
    # Compression
    compression_ratio: float = 0.5  # Compress to 50% of original
    
    # Preservation
    preserve_first_n: int = 2  # Always keep first N items
    preserve_last_n: int = 3    # Always keep last N items
    
    # Time decay
    time_decay_enabled: bool = True
    decay_hours: float = 24.0   # Start decaying after 24 hours


class SimpleSummarizer:
    """
    Simple extractive summarization for context compression.
    
    Uses key sentence extraction rather than full LLM summarization
    to minimize token usage and latency.
    """
    
    def __init__(self):
        # Vietnamese stopwords
        self._stopwords = {
            "và", "của", "là", "có", "trong", "được", "cho", "với",
            "này", "đã", "để", "từ", "một", "các", "những", "không",
            "theo", "về", "ra", "hay", "vào", "năm", "sau", "trước",
        }
        
        # Important keywords for history context
        self._important_keywords = {
            "sự kiện", "chiến dịch", "hiệp định", "nhân vật", "địa điểm",
            "ngày", "tháng", "năm", "quân", "đảng", "chính phủ",
            "cách mạng", "lịch sử", "hòa bình", "chiến tranh",
            "ai", "là gì", "ở đâu", "khi nào", "tại sao",
        }
    
    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization."""
        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        return [w for w in text.split() if w]
    
    def _score_sentence(self, sentence: str) -> float:
        """Score a sentence for importance."""
        score = 0.0
        
        # Count important keywords
        sentence_lower = sentence.lower()
        for keyword in self._important_keywords:
            if keyword in sentence_lower:
                score += 2.0
        
        # Penalize short sentences
        words = self._tokenize(sentence)
        if len(words) < 5:
            score -= 1.0
        
        # Reward sentences with numbers (dates, counts)
        if re.search(r'\d+', sentence):
            score += 1.0
        
        # Penalize stopwords ratio
        if words:
            stopword_ratio = sum(1 for w in words if w in self._stopwords) / len(words)
            score -= stopword_ratio
        
        return score
    
    def summarize(self, text: str, target_tokens: int) -> str:
        """
        Create a summary of text targeting a specific token count.
        
        Uses extractive summarization - picks most important sentences.
        """
        if not text:
            return ""
        
        # Split into sentences
        # Simple split by common delimiters
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return text[:target_tokens * 4]  # Fallback
        
        # Score each sentence
        scored = [(self._score_sentence(s), s) for s in sentences]
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Select sentences until we reach target
        selected = []
        current_tokens = 0
        target_chars = target_tokens * 4
        
        for _, sentence in scored:
            if current_tokens + len(sentence) > target_chars:
                # Don't add if it would exceed
                if not selected:
                    selected.append(sentence)  # Always add at least one
                break
            selected.append(sentence)
            current_tokens += len(sentence) + 1
        
        # Reconstruct in original order
        original_order = []
        for sentence in sentences:
            if sentence in selected:
                original_order.append(sentence)
                selected.remove(sentence)
        
        result = ". ".join(original_order)
        if result and not result.endswith('.'):
            result += "."
        
        return result
    
    def create_conversation_summary(
        self,
        turns: list[ContextItem],
        target_tokens: int,
    ) -> str:
        """
        Create a summary of a conversation.
        
        Extracts key points from each turn.
        """
        if not turns:
            return ""
        
        parts = []
        current_tokens = 0
        max_chars = target_tokens * 4
        
        for turn in turns:
            # Add role label
            role_label = {
                "user": "Người hỏi",
                "assistant": "Trợ lý",
                "system": "Hệ thống",
            }.get(turn.role, turn.role)
            
            # Extract key content
            content = turn.content
            
            # Summarize each turn if too long
            if len(content) > 500:
                content = self.summarize(content, 150)
            
            part = f"{role_label}: {content}"
            
            if current_tokens + len(part) > max_chars:
                break
            
            parts.append(part)
            current_tokens += len(part) + 1
        
        return " | ".join(parts)


class SlidingWindowManager:
    """
    Sliding window for context with priority-based retention.
    
    Features:
    - Priority-based item retention
    - Automatic eviction of low-priority items
    - Preservation of first/last N items
    """
    
    def __init__(self, config: ContextConfig):
        self.config = config
        self._items: list[ContextItem] = []
    
    def add(self, item: ContextItem) -> None:
        """Add a context item."""
        self._items.append(item)
        self._maybe_evict()
    
    def _maybe_evict(self) -> None:
        """Evict low-priority items if over capacity."""
        # Check total tokens
        total_tokens = sum(item.estimate_tokens() for item in self._items)
        
        while (
            total_tokens > self.config.max_total_tokens or
            len(self._items) > self.config.max_items
        ):
            # Find item to evict
            to_evict = self._find_item_to_evict()
            if to_evict is None:
                break
            
            total_tokens -= to_evict.estimate_tokens()
            self._items.remove(to_evict)
    
    def _find_item_to_evict(self) -> ContextItem | None:
        """Find the best item to evict."""
        if not self._items:
            return None
        
        # Never evict preserved items
        preservable_indices = set(range(self.config.preserve_first_n)) | set(
            range(max(0, len(self._items) - self.config.preserve_last_n), len(self._items))
        )
        
        candidates = [
            (i, item) for i, item in enumerate(self._items)
            if i not in preservable_indices
        ]
        
        if not candidates:
            # Fallback: evict from the middle
            mid = len(self._items) // 2
            return self._items[mid]
        
        # Score candidates: lower priority, less access, older = more likely to evict
        def eviction_score(idx: int, item: ContextItem) -> float:
            score = item.priority.value * 10
            score += item.access_count * 0.1
            score += item.created_at * 0.001
            return score
        
        candidates.sort(key=lambda x: eviction_score(x[0], x[1]))
        return candidates[0][1]
    
    def get_all(self) -> list[ContextItem]:
        """Get all items in order."""
        return self._items.copy()
    
    def get_tokens(self) -> int:
        """Get total token count."""
        return sum(item.estimate_tokens() for item in self._items)
    
    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()


class ContextManager:
    """
    Complete Context Management System.
    
    Features:
    - Sliding window with priority-based retention
    - Automatic summarization
    - Token budget management
    - Cross-tier context optimization
    
    Usage:
        manager = ContextManager()
        await manager.add_turn(session_id, "user", "question...")
        context = await manager.get_prompt_context(session_id, max_tokens=4000)
    """
    
    def __init__(self, config: ContextConfig | None = None):
        self.config = config or ContextConfig()
        self._summarizer = SimpleSummarizer()
        
        # Session-specific sliding windows
        self._session_windows: dict[str, SlidingWindowManager] = {}
        
        # Session summaries
        self._session_summaries: dict[str, str] = {}
        
        # Statistics
        self._compaction_stats: dict[str, int] = {}
    
    def _get_window(self, session_id: str) -> SlidingWindowManager:
        """Get or create sliding window for session."""
        if session_id not in self._session_windows:
            self._session_windows[session_id] = SlidingWindowManager(self.config)
        return self._session_windows[session_id]
    
    async def add(
        self,
        session_id: str,
        role: str,
        content: str,
        priority: ContextPriority = ContextPriority.MEDIUM,
        metadata: dict | None = None,
    ) -> None:
        """Add a context item to session."""
        item = ContextItem(
            role=role,
            content=content,
            priority=priority,
            metadata=metadata or {},
        )
        
        window = self._get_window(session_id)
        window.add(item)
        
        logger.debug(
            "context_item_added",
            session_id=session_id,
            role=role,
            tokens=item.estimate_tokens(),
            total_tokens=window.get_tokens(),
        )
    
    async def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        """Add a conversation turn."""
        # Infer priority from role
        priority = {
            "user": ContextPriority.HIGH,
            "assistant": ContextPriority.MEDIUM,
            "system": ContextPriority.CRITICAL,
            "tool": ContextPriority.LOW,
        }.get(role, ContextPriority.MEDIUM)
        
        await self.add(session_id, role, content, priority, metadata)
    
    async def get_all(self, session_id: str) -> list[ContextItem]:
        """Get all context items for session."""
        return self._get_window(session_id).get_all()
    
    async def get_tokens(self, session_id: str) -> int:
        """Get total tokens for session."""
        return self._get_window(session_id).get_tokens()
    
    async def get_prompt_context(
        self,
        session_id: str,
        max_tokens: int | None = None,
        include_system: bool = True,
    ) -> str:
        """
        Get optimized context for LLM prompt.
        
        Includes:
        - System messages (if include_system)
        - Recent conversation
        - Conversation summary (if context is truncated)
        """
        if max_tokens is None:
            max_tokens = self.config.max_total_tokens
        
        window = self._get_window(session_id)
        items = window.get_all()
        
        if not items:
            return ""
        
        # Separate system and non-system messages
        system_items = [i for i in items if i.role == "system"]
        other_items = [i for i in items if i.role != "system"]
        
        # Calculate token budget
        system_tokens = sum(i.estimate_tokens() for i in system_items)
        available_tokens = max_tokens - system_tokens
        
        # Build context
        parts = []
        current_tokens = 0
        
        # Add system messages first
        for item in system_items:
            if include_system:
                parts.append(f"<system>{item.content}</system>")
                current_tokens += item.estimate_tokens()
        
        # Add conversation history
        for item in other_items:
            item_tokens = item.estimate_tokens()
            
            if current_tokens + item_tokens > available_tokens:
                # Need to truncate - add summary instead
                if self._session_summaries.get(session_id):
                    parts.append(f"[Tóm tắt cuộc trò chuyện trước đó]\n{self._session_summaries[session_id]}")
                break
            
            # Format based on role
            if item.role == "user":
                parts.append(f"<người_dùng>{item.content}</người_dùng>")
            elif item.role == "assistant":
                parts.append(f"<trợ_lý>{item.content}</trợ_lý>")
            else:
                parts.append(f"<{item.role}>{item.content}</{item.role}>")
            
            current_tokens += item_tokens
        
        return "\n\n".join(parts)
    
    async def maybe_compact(
        self,
        session_id: str,
        force: bool = False,
    ) -> bool:
        """
        Check and perform context compaction if needed.
        
        Returns True if compaction was performed.
        """
        window = self._get_window(session_id)
        total_tokens = window.get_tokens()
        
        # Check if compaction is needed
        trigger_tokens = self.config.max_total_tokens * self.config.summary_trigger_ratio
        
        if not force and total_tokens < trigger_tokens:
            return False
        
        if not self.config.enable_summarization:
            return False
        
        # Perform summarization
        items = window.get_all()
        
        # Separate categories
        system_items = [i for i in items if i.role == "system"]
        conversation_items = [i for i in items if i.role != "system"]
        
        # Calculate target tokens for summary
        summary_target = int(self.config.max_total_tokens * 0.2)  # 20% of budget
        
        # Create summary
        summary = self._summarizer.create_conversation_summary(
            conversation_items,
            summary_target
        )
        
        if summary:
            self._session_summaries[session_id] = summary
        
        # Update stats
        self._compaction_stats[session_id] = self._compaction_stats.get(session_id, 0) + 1
        
        logger.info(
            "context_compacted",
            session_id=session_id,
            original_tokens=total_tokens,
            summary_tokens=len(summary) // 4,
            compaction_count=self._compaction_stats[session_id],
        )
        
        # Evict old items if still over capacity
        window._maybe_evict()
        
        return True
    
    async def compact_to_tokens(
        self,
        session_id: str,
        target_tokens: int,
    ) -> int:
        """
        Compact context to target token count.
        
        Returns number of tokens removed.
        """
        window = self._get_window(session_id)
        current_tokens = window.get_tokens()
        
        if current_tokens <= target_tokens:
            return 0
        
        tokens_to_remove = current_tokens - target_tokens
        
        # Remove lowest priority items
        items = window.get_all()
        removed_tokens = 0
        
        # Sort by priority (low first), then by access count, then by age
        def removal_priority(item: ContextItem) -> tuple:
            return (item.priority.value, item.access_count, item.created_at)
        
        items.sort(key=removal_priority)
        
        # Remove from middle of conversation (keep first/last)
        mid_start = self.config.preserve_first_n
        mid_end = len(items) - self.config.preserve_last_n
        
        for i, item in enumerate(items):
            if i < mid_start or i >= mid_end:
                continue  # Skip preserved items
            
            removed_tokens += item.estimate_tokens()
            window._items.remove(item)
            
            if removed_tokens >= tokens_to_remove:
                break
        
        # If still over budget, remove from preserved items
        while window.get_tokens() > target_tokens and window._items:
            item = window._items[mid_start] if mid_start < len(window._items) else window._items[-1]
            removed_tokens += item.estimate_tokens()
            window._items.remove(item)
        
        logger.info(
            "context_compacted_to_target",
            session_id=session_id,
            original_tokens=current_tokens,
            final_tokens=window.get_tokens(),
            tokens_removed=removed_tokens,
        )
        
        return removed_tokens
    
    async def get_summary(self, session_id: str) -> str:
        """Get conversation summary for session."""
        return self._session_summaries.get(session_id, "")
    
    async def clear(self, session_id: str) -> None:
        """Clear all context for session."""
        if session_id in self._session_windows:
            self._session_windows[session_id].clear()
        self._session_summaries.pop(session_id, None)
        self._compaction_stats.pop(session_id, None)
    
    def get_stats(self, session_id: str) -> dict:
        """Get context statistics for session."""
        window = self._get_window(session_id)
        
        return {
            "total_items": len(window._items),
            "total_tokens": window.get_tokens(),
            "max_tokens": self.config.max_total_tokens,
            "utilization": window.get_tokens() / max(1, self.config.max_total_tokens),
            "has_summary": session_id in self._session_summaries,
            "summary_length": len(self._session_summaries.get(session_id, "")),
            "compaction_count": self._compaction_stats.get(session_id, 0),
        }


# ─── Global Instance ─────────────────────────────────────────────────────────

_context_instance: ContextManager | None = None


def get_context_manager() -> ContextManager:
    """Get the global ContextManager instance."""
    global _context_instance
    if _context_instance is None:
        _context_instance = ContextManager()
    return _context_instance


def reset_context_manager() -> None:
    """Reset the global instance (for testing)."""
    global _context_instance
    _context_instance = None
