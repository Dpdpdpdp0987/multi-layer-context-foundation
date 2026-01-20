"""
Immediate Context Buffer - High-speed in-memory buffer for recent context.
"""

from typing import Any, Dict, List, Optional
from collections import deque
from datetime import datetime
from loguru import logger


class ImmediateContextBuffer:
    """
    Immediate context buffer for recent conversational context.
    
    Implements a circular buffer with token budget management.
    Optimized for fast access and recency-based retrieval.
    """
    
    def __init__(self, max_size: int = 10, max_tokens: int = 2048):
        """
        Initialize immediate context buffer.
        
        Args:
            max_size: Maximum number of items
            max_tokens: Maximum token budget
        """
        self.max_size = max_size
        self.max_tokens = max_tokens
        self.buffer: deque = deque(maxlen=max_size)
        self.current_tokens = 0
        
        logger.info(
            f"ImmediateContextBuffer initialized: max_size={max_size}, "
            f"max_tokens={max_tokens}"
        )
    
    def add(self, item: Any) -> str:
        """
        Add item to buffer.
        
        Args:
            item: Context item to add
            
        Returns:
            Item ID
        """
        # Estimate tokens for new item
        item_tokens = self._estimate_tokens(item.content)
        
        # Make room if needed
        while self.current_tokens + item_tokens > self.max_tokens and self.buffer:
            evicted = self.buffer.popleft()
            evicted_tokens = self._estimate_tokens(evicted.content)
            self.current_tokens -= evicted_tokens
            logger.debug(f"Evicted from buffer: {evicted.id}")
        
        # Add new item
        self.buffer.append(item)
        self.current_tokens += item_tokens
        
        logger.debug(
            f"Added to buffer: {item.id}, tokens: {self.current_tokens}/{self.max_tokens}"
        )
        
        return item.id
    
    def search(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Any]:
        """
        Search buffer for relevant items.
        
        Uses simple keyword matching with recency bias.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of matching items
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        results = []
        
        # Search from most recent to oldest
        for idx, item in enumerate(reversed(list(self.buffer))):
            content_lower = item.content.lower()
            content_words = set(content_lower.split())
            
            # Calculate relevance
            if query_words:
                overlap = len(query_words & content_words)
                relevance = overlap / len(query_words)
            else:
                relevance = 0.0
            
            # Apply recency boost (more recent = higher score)
            recency_boost = 1.0 - (idx * 0.1)
            recency_boost = max(0.5, recency_boost)  # Minimum 0.5
            
            combined_score = relevance * recency_boost
            
            if combined_score > 0:
                item.relevance_score = combined_score
                results.append(item)
        
        # Sort by score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results[:max_results]
    
    def get_all(self) -> List[Any]:
        """
        Get all items in buffer.
        
        Returns:
            List of all items
        """
        return list(self.buffer)
    
    def get_recent(self, n: int = 5) -> List[Any]:
        """
        Get n most recent items.
        
        Args:
            n: Number of items to retrieve
            
        Returns:
            List of recent items
        """
        n = min(n, len(self.buffer))
        return list(self.buffer)[-n:]
    
    def clear(self):
        """Clear the buffer."""
        self.buffer.clear()
        self.current_tokens = 0
        logger.info("Immediate buffer cleared")
    
    def get_token_usage(self) -> Dict[str, int]:
        """
        Get token usage statistics.
        
        Returns:
            Dictionary with usage stats
        """
        return {
            "current_tokens": self.current_tokens,
            "max_tokens": self.max_tokens,
            "usage_percent": (self.current_tokens / self.max_tokens) * 100 if self.max_tokens > 0 else 0,
            "item_count": len(self.buffer)
        }
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        # Simple heuristic: ~4 characters per token
        return max(1, len(text) // 4)
    
    def __len__(self) -> int:
        """Return buffer size."""
        return len(self.buffer)
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ImmediateContextBuffer(items={len(self.buffer)}, "
            f"tokens={self.current_tokens}/{self.max_tokens})"
        )