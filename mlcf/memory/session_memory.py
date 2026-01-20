"""
Session Memory - Working memory for active task context with LRU eviction.
"""

from typing import Any, Dict, List, Optional, Set
from collections import OrderedDict
from datetime import datetime, timedelta
from loguru import logger
import threading


class SessionMemory:
    """
    Session memory for active task and conversational context.
    
    Implements LRU eviction with relevance-based retention.
    Supports multiple concurrent sessions with automatic cleanup.
    """
    
    def __init__(
        self,
        max_size: int = 50,
        relevance_threshold: float = 0.7,
        session_timeout: timedelta = timedelta(hours=2)
    ):
        """
        Initialize session memory.
        
        Args:
            max_size: Maximum number of items per session
            relevance_threshold: Minimum relevance score for retention
            session_timeout: Session inactivity timeout
        """
        self.max_size = max_size
        self.relevance_threshold = relevance_threshold
        self.session_timeout = session_timeout
        
        # Session storage: session_id -> OrderedDict of items
        self._sessions: Dict[str, OrderedDict] = {}
        
        # Session metadata
        self._session_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Active session tracking
        self._active_session: Optional[str] = None
        
        # Thread lock for concurrent access
        self._lock = threading.RLock()
        
        logger.info(
            f"SessionMemory initialized: max_size={max_size}, "
            f"relevance_threshold={relevance_threshold}"
        )
    
    def start_session(self, session_id: str) -> str:
        """
        Start a new session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Session ID
        """
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = OrderedDict()
                self._session_metadata[session_id] = {
                    "created_at": datetime.utcnow(),
                    "last_accessed": datetime.utcnow(),
                    "item_count": 0,
                    "total_accesses": 0
                }
            
            self._active_session = session_id
            logger.info(f"Started session: {session_id}")
            
            return session_id
    
    def add(
        self,
        item: Any,
        session_id: Optional[str] = None
    ) -> str:
        """
        Add item to session memory.
        
        Args:
            item: Context item to add
            session_id: Target session (uses active if None)
            
        Returns:
            Item ID
        """
        with self._lock:
            # Get or create session
            session_id = session_id or self._active_session
            if not session_id:
                session_id = self.start_session("default")
            
            if session_id not in self._sessions:
                self.start_session(session_id)
            
            session = self._sessions[session_id]
            
            # Check if item already exists (update instead of duplicate)
            if item.id in session:
                logger.debug(f"Updating existing item: {item.id}")
                session.move_to_end(item.id)  # Mark as recently used
                session[item.id] = item
            else:
                # Add new item
                session[item.id] = item
                
                # Evict LRU item if over capacity
                while len(session) > self.max_size:
                    evicted_id, evicted_item = session.popitem(last=False)
                    logger.debug(
                        f"Evicted LRU item from session {session_id}: {evicted_id}"
                    )
            
            # Update session metadata
            self._session_metadata[session_id]["last_accessed"] = datetime.utcnow()
            self._session_metadata[session_id]["item_count"] = len(session)
            
            logger.debug(f"Added to session {session_id}: {item.id}")
            
            return item.id
    
    def search(
        self,
        query: str,
        max_results: int = 10,
        session_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Search session memory for relevant items.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            session_id: Target session (uses active if None)
            filters: Optional metadata filters
            
        Returns:
            List of matching items
        """
        with self._lock:
            session_id = session_id or self._active_session
            if not session_id or session_id not in self._sessions:
                return []
            
            session = self._sessions[session_id]
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            results = []
            
            for item_id, item in session.items():
                # Apply filters if provided
                if filters and not self._matches_filters(item, filters):
                    continue
                
                # Calculate relevance
                content_lower = item.content.lower()
                content_words = set(content_lower.split())
                
                if query_words:
                    # Jaccard similarity
                    intersection = len(query_words & content_words)
                    union = len(query_words | content_words)
                    relevance = intersection / union if union > 0 else 0.0
                else:
                    relevance = 0.0
                
                # Boost by item's stored relevance score
                combined_score = relevance * item.relevance_score
                
                # Only include if above threshold
                if combined_score >= self.relevance_threshold:
                    item.relevance_score = combined_score
                    item.update_access()  # Update access tracking
                    results.append(item)
                    
                    # Move to end (mark as recently used)
                    session.move_to_end(item_id)
            
            # Sort by relevance
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # Update session access
            if session_id in self._session_metadata:
                self._session_metadata[session_id]["last_accessed"] = datetime.utcnow()
                self._session_metadata[session_id]["total_accesses"] += 1
            
            return results[:max_results]
    
    def get_active_items(
        self,
        session_id: Optional[str] = None,
        top_k: int = 20
    ) -> List[Any]:
        """
        Get most active/relevant items from session.
        
        Args:
            session_id: Target session (uses active if None)
            top_k: Number of top items to return
            
        Returns:
            List of active items
        """
        with self._lock:
            session_id = session_id or self._active_session
            if not session_id or session_id not in self._sessions:
                return []
            
            session = self._sessions[session_id]
            items = list(session.values())
            
            # Sort by combined score of relevance and access frequency
            items.sort(
                key=lambda x: (
                    x.relevance_score * (1 + x.access_count * 0.1),
                    x.priority.value
                ),
                reverse=True
            )
            
            return items[:top_k]
    
    def get_all(
        self,
        session_id: Optional[str] = None
    ) -> List[Any]:
        """
        Get all items from session.
        
        Args:
            session_id: Target session (uses active if None)
            
        Returns:
            List of all items
        """
        with self._lock:
            session_id = session_id or self._active_session
            if not session_id or session_id not in self._sessions:
                return []
            
            return list(self._sessions[session_id].values())
    
    def clear(self, session_id: Optional[str] = None):
        """
        Clear session memory.
        
        Args:
            session_id: Target session (clears active if None)
        """
        with self._lock:
            session_id = session_id or self._active_session
            
            if session_id and session_id in self._sessions:
                self._sessions[session_id].clear()
                self._session_metadata[session_id]["item_count"] = 0
                logger.info(f"Cleared session: {session_id}")
    
    def cleanup_expired_sessions(self):
        """
        Remove expired sessions based on timeout.
        """
        with self._lock:
            now = datetime.utcnow()
            expired_sessions = []
            
            for session_id, metadata in self._session_metadata.items():
                last_accessed = metadata.get("last_accessed")
                if last_accessed:
                    age = now - last_accessed
                    if age > self.session_timeout:
                        expired_sessions.append(session_id)
            
            # Remove expired sessions
            for session_id in expired_sessions:
                del self._sessions[session_id]
                del self._session_metadata[session_id]
                logger.info(f"Removed expired session: {session_id}")
            
            return len(expired_sessions)
    
    def get_session_stats(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get session statistics.
        
        Args:
            session_id: Target session (uses active if None)
            
        Returns:
            Statistics dictionary
        """
        with self._lock:
            session_id = session_id or self._active_session
            if not session_id or session_id not in self._sessions:
                return {}
            
            session = self._sessions[session_id]
            metadata = self._session_metadata.get(session_id, {})
            
            # Calculate average relevance
            items = list(session.values())
            avg_relevance = (
                sum(item.relevance_score for item in items) / len(items)
                if items else 0.0
            )
            
            return {
                "session_id": session_id,
                "item_count": len(session),
                "max_size": self.max_size,
                "usage_percent": (len(session) / self.max_size) * 100,
                "average_relevance": avg_relevance,
                "created_at": metadata.get("created_at"),
                "last_accessed": metadata.get("last_accessed"),
                "total_accesses": metadata.get("total_accesses", 0)
            }
    
    def _matches_filters(self, item: Any, filters: Dict[str, Any]) -> bool:
        """
        Check if item matches metadata filters.
        
        Args:
            item: Context item
            filters: Filter dictionary
            
        Returns:
            True if matches all filters
        """
        for key, value in filters.items():
            # Check in metadata
            if key in item.metadata:
                if item.metadata[key] != value:
                    return False
            # Check direct attributes
            elif hasattr(item, key):
                attr_value = getattr(item, key)
                # Handle enum comparison
                if hasattr(attr_value, 'value'):
                    attr_value = attr_value.value
                if attr_value != value:
                    return False
            else:
                return False
        
        return True
    
    def __len__(self) -> int:
        """Return total items across all sessions."""
        with self._lock:
            return sum(len(session) for session in self._sessions.values())
    
    def __repr__(self) -> str:
        """String representation."""
        with self._lock:
            return (
                f"SessionMemory(sessions={len(self._sessions)}, "
                f"total_items={len(self)}, active={self._active_session})"
            )