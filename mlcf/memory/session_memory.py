"""
Session Memory - Manages active session and task context.

This layer maintains working memory for the current session,
with intelligent consolidation and relevance-based retention.
"""

from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger
import threading
from dataclasses import dataclass

from mlcf.core.context_models import ContextItem


@dataclass
class ConsolidationCandidate:
    """Candidate for memory consolidation."""
    items: List[ContextItem]
    consolidated_content: str
    importance: float
    timestamp: datetime


class SessionMemory:
    """
    Session-scoped memory with intelligent management.
    
    Features:
    - Relevance-based retention
    - Automatic consolidation of related items
    - LRU eviction with importance weighting
    - Conversation grouping
    - Task context tracking
    """
    
    def __init__(
        self,
        max_size: int = 50,
        consolidation_threshold: int = 100,
        relevance_threshold: float = 0.6,
        enable_consolidation: bool = True
    ):
        """
        Initialize session memory.
        
        Args:
            max_size: Maximum number of items to store
            consolidation_threshold: Trigger consolidation at this size
            relevance_threshold: Minimum relevance score to retain
            enable_consolidation: Enable automatic consolidation
        """
        self.max_size = max_size
        self.consolidation_threshold = consolidation_threshold
        self.relevance_threshold = relevance_threshold
        self.enable_consolidation = enable_consolidation
        
        # Storage: item_id -> ContextItem
        self._items: Dict[str, ContextItem] = {}
        
        # Conversation grouping: conversation_id -> Set[item_id]
        self._conversations: Dict[str, Set[str]] = defaultdict(set)
        
        # Task tracking: task_id -> Set[item_id]
        self._tasks: Dict[str, Set[str]] = defaultdict(set)
        
        # Access order for LRU (item_id, last_access_time)
        self._access_order: List[tuple[str, datetime]] = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Metrics
        self._total_adds = 0
        self._total_evictions = 0
        self._total_consolidations = 0
        
        logger.info(
            f"SessionMemory initialized: max_size={max_size}, "
            f"consolidation_threshold={consolidation_threshold}"
        )
    
    def add(self, item: ContextItem) -> bool:
        """
        Add item to session memory.
        
        Args:
            item: Context item to add
            
        Returns:
            True if added successfully
        """
        with self._lock:
            # Check if consolidation needed
            if (self.enable_consolidation and
                len(self._items) >= self.consolidation_threshold):
                self._consolidate()
            
            # Check if eviction needed
            if len(self._items) >= self.max_size:
                self._evict_least_important()
            
            # Add item
            self._items[item.id] = item
            
            # Update conversation tracking
            if item.conversation_id:
                self._conversations[item.conversation_id].add(item.id)
            
            # Update task tracking
            task_id = item.metadata.get("task_id")
            if task_id:
                self._tasks[task_id].add(item.id)
            
            # Update access order
            self._access_order.append((item.id, datetime.utcnow()))
            
            self._total_adds += 1
            
            logger.debug(
                f"Added to session memory: {item.id} "
                f"(size: {len(self._items)}/{self.max_size})"
            )
            
            return True
    
    def search(
        self,
        query: Optional[str] = None,
        max_results: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> List[ContextItem]:
        """
        Search session memory.
        
        Args:
            query: Search query (keyword matching)
            max_results: Maximum number of results
            filters: Metadata filters
            conversation_id: Filter by conversation
            task_id: Filter by task
            
        Returns:
            List of matching items, sorted by relevance
        """
        with self._lock:
            # Start with all items
            candidates = list(self._items.values())
            
            # Apply conversation filter
            if conversation_id:
                conversation_ids = self._conversations.get(conversation_id, set())
                candidates = [
                    item for item in candidates
                    if item.id in conversation_ids
                ]
            
            # Apply task filter
            if task_id:
                task_ids = self._tasks.get(task_id, set())
                candidates = [
                    item for item in candidates
                    if item.id in task_ids
                ]
            
            # Apply metadata filters
            if filters:
                candidates = self._apply_filters(candidates, filters)
            
            # Apply query matching and scoring
            if query:
                scored_items = []
                for item in candidates:
                    relevance = self._calculate_relevance(item, query)
                    if relevance >= self.relevance_threshold:
                        item.relevance_score = relevance
                        scored_items.append(item)
                
                # Sort by relevance * importance
                scored_items.sort(
                    key=lambda x: x.relevance_score * x.importance_score,
                    reverse=True
                )
                
                results = scored_items[:max_results]
            else:
                # No query - sort by recency and importance
                candidates.sort(
                    key=lambda x: (
                        x.timestamp.timestamp() * x.importance_score
                    ),
                    reverse=True
                )
                results = candidates[:max_results]
            
            # Mark as accessed
            for item in results:
                item.mark_accessed()
                self._update_access_order(item.id)
            
            return results
    
    def get_conversation_context(
        self,
        conversation_id: str,
        max_items: Optional[int] = None
    ) -> List[ContextItem]:
        """
        Get all items for a conversation.
        
        Args:
            conversation_id: Conversation identifier
            max_items: Maximum items to return
            
        Returns:
            Conversation items sorted by timestamp
        """
        with self._lock:
            item_ids = self._conversations.get(conversation_id, set())
            items = [
                self._items[item_id]
                for item_id in item_ids
                if item_id in self._items
            ]
            
            # Sort by timestamp
            items.sort(key=lambda x: x.timestamp)
            
            if max_items:
                items = items[-max_items:]  # Most recent
            
            return items
    
    def get_task_context(
        self,
        task_id: str
    ) -> List[ContextItem]:
        """
        Get all items related to a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task-related items
        """
        with self._lock:
            item_ids = self._tasks.get(task_id, set())
            items = [
                self._items[item_id]
                for item_id in item_ids
                if item_id in self._items
            ]
            
            # Sort by importance then timestamp
            items.sort(
                key=lambda x: (x.importance_score, x.timestamp.timestamp()),
                reverse=True
            )
            
            return items
    
    def clear(self):
        """Clear all session memory."""
        with self._lock:
            self._items.clear()
            self._conversations.clear()
            self._tasks.clear()
            self._access_order.clear()
            logger.info("Session memory cleared")
    
    def clear_conversation(self, conversation_id: str):
        """Clear specific conversation."""
        with self._lock:
            item_ids = self._conversations.get(conversation_id, set())
            
            for item_id in item_ids:
                if item_id in self._items:
                    del self._items[item_id]
            
            # Remove from access order
            self._access_order = [
                (iid, ts) for iid, ts in self._access_order
                if iid not in item_ids
            ]
            
            # Clear conversation tracking
            if conversation_id in self._conversations:
                del self._conversations[conversation_id]
            
            logger.info(f"Cleared conversation: {conversation_id}")
    
    def clear_task(self, task_id: str):
        """Clear specific task."""
        with self._lock:
            item_ids = self._tasks.get(task_id, set())
            
            for item_id in item_ids:
                # Only remove if not part of active conversation
                item = self._items.get(item_id)
                if item and not item.conversation_id:
                    del self._items[item_id]
            
            # Clear task tracking
            if task_id in self._tasks:
                del self._tasks[task_id]
            
            logger.info(f"Cleared task: {task_id}")
    
    def _calculate_relevance(self, item: ContextItem, query: str) -> float:
        """
        Calculate relevance score for item against query.
        
        Uses simple keyword matching with TF-IDF-like weighting.
        """
        content_lower = item.content.lower()
        query_lower = query.lower()
        
        query_words = set(query_lower.split())
        content_words = content_lower.split()
        
        if not query_words:
            return 0.0
        
        # Count matches
        matches = sum(1 for word in query_words if word in content_lower)
        
        # Jaccard similarity
        content_word_set = set(content_words)
        intersection = len(query_words & content_word_set)
        union = len(query_words | content_word_set)
        
        jaccard = intersection / union if union > 0 else 0.0
        
        # Combine with match ratio
        match_ratio = matches / len(query_words)
        
        # Weighted average
        relevance = 0.6 * match_ratio + 0.4 * jaccard
        
        return relevance
    
    def _apply_filters(
        self,
        items: List[ContextItem],
        filters: Dict[str, Any]
    ) -> List[ContextItem]:
        """Apply metadata filters to items."""
        filtered = []
        
        for item in items:
            matches = True
            
            for key, value in filters.items():
                if key not in item.metadata:
                    matches = False
                    break
                
                if isinstance(value, list):
                    # OR matching for lists
                    if item.metadata[key] not in value:
                        matches = False
                        break
                else:
                    # Exact match
                    if item.metadata[key] != value:
                        matches = False
                        break
            
            if matches:
                filtered.append(item)
        
        return filtered
    
    def _evict_least_important(self):
        """
        Evict least important item based on LRU and importance.
        """
        if not self._items:
            return
        
        # Score items: recency * importance * access_count
        scores = []
        now = datetime.utcnow()
        
        for item_id, item in self._items.items():
            # Get last access time
            last_access = item.last_accessed or item.timestamp
            age_hours = (now - last_access).total_seconds() / 3600
            
            # Recency score (decay over time)
            recency = 1.0 / (1.0 + age_hours)
            
            # Combined score
            score = recency * item.importance_score * (1.0 + item.access_count)
            
            scores.append((item_id, score))
        
        # Sort by score (lowest first)
        scores.sort(key=lambda x: x[1])
        
        # Evict lowest scoring item
        evict_id = scores[0][0]
        evicted_item = self._items[evict_id]
        
        del self._items[evict_id]
        
        # Clean up tracking
        if evicted_item.conversation_id:
            self._conversations[evicted_item.conversation_id].discard(evict_id)
        
        task_id = evicted_item.metadata.get("task_id")
        if task_id:
            self._tasks[task_id].discard(evict_id)
        
        # Remove from access order
        self._access_order = [
            (iid, ts) for iid, ts in self._access_order
            if iid != evict_id
        ]
        
        self._total_evictions += 1
        
        logger.debug(
            f"Evicted from session memory: {evict_id} "
            f"(score: {scores[0][1]:.3f})"
        )
    
    def _update_access_order(self, item_id: str):
        """Update access order for item."""
        # Remove old entry
        self._access_order = [
            (iid, ts) for iid, ts in self._access_order
            if iid != item_id
        ]
        
        # Add new entry
        self._access_order.append((item_id, datetime.utcnow()))
    
    def _consolidate(self):
        """
        Consolidate related items to save space.
        
        Groups similar items and creates consolidated summaries.
        """
        logger.info("Starting session memory consolidation...")
        
        # Find consolidation candidates (items within same conversation/task)
        candidates = self._find_consolidation_candidates()
        
        if not candidates:
            logger.info("No consolidation candidates found")
            return
        
        # Consolidate each group
        for candidate in candidates:
            consolidated_item = self._create_consolidated_item(candidate)
            
            # Remove original items
            for item in candidate.items:
                if item.id in self._items:
                    del self._items[item.id]
            
            # Add consolidated item
            self._items[consolidated_item.id] = consolidated_item
        
        self._total_consolidations += 1
        logger.info(
            f"Consolidated {len(candidates)} groups, "
            f"new size: {len(self._items)}"
        )
    
    def _find_consolidation_candidates(self) -> List[ConsolidationCandidate]:
        """Find groups of items that can be consolidated."""
        candidates = []
        
        # Group by conversation
        for conv_id, item_ids in self._conversations.items():
            if len(item_ids) >= 5:  # Only consolidate if 5+ items
                items = [
                    self._items[iid] for iid in item_ids
                    if iid in self._items
                ]
                
                # Sort by timestamp
                items.sort(key=lambda x: x.timestamp)
                
                # Create candidate
                consolidated_content = self._summarize_items(items)
                avg_importance = sum(i.importance_score for i in items) / len(items)
                
                candidates.append(ConsolidationCandidate(
                    items=items,
                    consolidated_content=consolidated_content,
                    importance=avg_importance,
                    timestamp=items[0].timestamp
                ))
        
        return candidates
    
    def _summarize_items(self, items: List[ContextItem]) -> str:
        """Create summary of multiple items."""
        # Simple concatenation with markers
        # TODO: Implement LLM-based summarization
        parts = [
            f"[{item.timestamp.strftime('%H:%M')}] {item.content}"
            for item in items
        ]
        return "\n".join(parts)
    
    def _create_consolidated_item(self, candidate: ConsolidationCandidate) -> ContextItem:
        """Create a consolidated item from candidates."""
        return ContextItem(
            content=candidate.consolidated_content,
            metadata={
                "type": "consolidated",
                "original_count": len(candidate.items),
                "importance": candidate.importance,
                "consolidated_at": datetime.utcnow().isoformat()
            },
            timestamp=candidate.timestamp,
            conversation_id=candidate.items[0].conversation_id,
            importance_score=candidate.importance
        )
    
    @property
    def size(self) -> int:
        """Get current size."""
        with self._lock:
            return len(self._items)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get session memory metrics."""
        with self._lock:
            return {
                "current_size": len(self._items),
                "max_size": self.max_size,
                "total_adds": self._total_adds,
                "total_evictions": self._total_evictions,
                "total_consolidations": self._total_consolidations,
                "active_conversations": len(self._conversations),
                "active_tasks": len(self._tasks),
                "avg_access_count": self._get_avg_access_count()
            }
    
    def _get_avg_access_count(self) -> float:
        """Get average access count."""
        if not self._items:
            return 0.0
        total = sum(item.access_count for item in self._items.values())
        return total / len(self._items)
    
    def __len__(self) -> int:
        """Get size."""
        return self.size
    
    def __repr__(self) -> str:
        """String representation."""
        return f"SessionMemory(size={self.size}/{self.max_size})"