"""
Immediate Context Buffer - Stores the most recent conversation exchanges.

This buffer maintains a sliding window of the most recent context,
optimized for ultra-fast access with minimal overhead.
"""

from typing import List, Optional, Dict, Any
from collections import deque
from datetime import datetime, timedelta
from loguru import logger
import threading

from mlcf.core.context_models import ContextItem


class ImmediateContextBuffer:
    """
    Fast-access buffer for immediate conversation context.
    
    Characteristics:
    - FIFO eviction (oldest items removed first)
    - Time-based expiration (TTL)
    - Thread-safe operations
    - Optimized for recency-based retrieval
    - Minimal computational overhead
    """
    
    def __init__(
        self,
        max_size: int = 10,
        ttl_seconds: int = 3600
    ):
        """
        Initialize immediate context buffer.
        
        Args:
            max_size: Maximum number of items to store
            ttl_seconds: Time-to-live for items in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        # Use deque for O(1) append and popleft
        self._buffer: deque[ContextItem] = deque(maxlen=max_size)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Metrics
        self._total_adds = 0
        self._total_evictions = 0
        
        logger.info(
            f"ImmediateContextBuffer initialized: "
            f"max_size={max_size}, ttl={ttl_seconds}s"
        )
    
    def add(self, item: ContextItem) -> bool:
        """
        Add item to buffer.
        
        Args:
            item: Context item to add
            
        Returns:
            True if added successfully
        """
        with self._lock:
            # Check if buffer is full (will auto-evict with deque maxlen)
            was_full = len(self._buffer) >= self.max_size
            
            # Add item (oldest will be auto-evicted if at capacity)
            self._buffer.append(item)
            
            self._total_adds += 1
            if was_full:
                self._total_evictions += 1
                logger.debug(f"Evicted oldest item from immediate buffer")
            
            logger.debug(
                f"Added to immediate buffer: {item.id} "
                f"(size: {len(self._buffer)}/{self.max_size})"
            )
            
            return True
    
    def get_recent(
        self,
        max_items: Optional[int] = None,
        conversation_id: Optional[str] = None
    ) -> List[ContextItem]:
        """
        Get most recent items from buffer.
        
        Args:
            max_items: Maximum number of items to return
            conversation_id: Filter by conversation ID
            
        Returns:
            List of recent context items
        """
        with self._lock:
            # Remove expired items first
            self._remove_expired()
            
            # Get all items (already in order, newest last)
            items = list(self._buffer)
            
            # Filter by conversation if specified
            if conversation_id:
                items = [
                    item for item in items
                    if item.conversation_id == conversation_id
                ]
            
            # Reverse to get newest first
            items.reverse()
            
            # Limit results
            if max_items:
                items = items[:max_items]
            
            # Mark as accessed
            for item in items:
                item.mark_accessed()
            
            return items
    
    def get_all(self) -> List[ContextItem]:
        """
        Get all items in buffer (newest first).
        
        Returns:
            All context items
        """
        with self._lock:
            self._remove_expired()
            items = list(self._buffer)
            items.reverse()
            return items
    
    def clear(self, conversation_id: Optional[str] = None):
        """
        Clear buffer or specific conversation.
        
        Args:
            conversation_id: Clear only this conversation (or all if None)
        """
        with self._lock:
            if conversation_id:
                # Remove items for specific conversation
                self._buffer = deque(
                    (
                        item for item in self._buffer
                        if item.conversation_id != conversation_id
                    ),
                    maxlen=self.max_size
                )
                logger.info(f"Cleared conversation {conversation_id} from immediate buffer")
            else:
                # Clear everything
                self._buffer.clear()
                logger.info("Cleared immediate buffer")
    
    def _remove_expired(self):
        """
        Remove expired items based on TTL.
        """
        if not self.ttl_seconds:
            return
        
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.ttl_seconds)
        
        # Remove items older than cutoff
        expired_count = 0
        while self._buffer and self._buffer[0].timestamp < cutoff_time:
            expired_item = self._buffer.popleft()
            expired_count += 1
            logger.debug(f"Removed expired item: {expired_item.id}")
        
        if expired_count > 0:
            logger.info(f"Removed {expired_count} expired items from immediate buffer")
    
    @property
    def size(self) -> int:
        """Get current buffer size."""
        with self._lock:
            return len(self._buffer)
    
    @property
    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        with self._lock:
            return len(self._buffer) == 0
    
    @property
    def is_full(self) -> bool:
        """Check if buffer is full."""
        with self._lock:
            return len(self._buffer) >= self.max_size
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get buffer metrics."""
        with self._lock:
            self._remove_expired()
            return {
                "current_size": len(self._buffer),
                "max_size": self.max_size,
                "total_adds": self._total_adds,
                "total_evictions": self._total_evictions,
                "ttl_seconds": self.ttl_seconds,
                "oldest_item_age": self._get_oldest_age(),
                "newest_item_age": self._get_newest_age()
            }
    
    def _get_oldest_age(self) -> Optional[float]:
        """Get age of oldest item in seconds."""
        if not self._buffer:
            return None
        oldest = self._buffer[0]
        return (datetime.utcnow() - oldest.timestamp).total_seconds()
    
    def _get_newest_age(self) -> Optional[float]:
        """Get age of newest item in seconds."""
        if not self._buffer:
            return None
        newest = self._buffer[-1]
        return (datetime.utcnow() - newest.timestamp).total_seconds()
    
    def __len__(self) -> int:
        """Get buffer size."""
        return self.size
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ImmediateContextBuffer("
            f"size={self.size}/{self.max_size}, "
            f"ttl={self.ttl_seconds}s)"
        )