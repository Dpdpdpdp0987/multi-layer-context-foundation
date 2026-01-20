"""
Data models for context management.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import uuid
import hashlib


class LayerType(Enum):
    """Memory layer types."""
    IMMEDIATE = "immediate"
    SESSION = "session"
    LONG_TERM = "long_term"


class RetrievalStrategy(Enum):
    """Retrieval strategy types."""
    RECENCY = "recency"  # Most recent items
    RELEVANCE = "relevance"  # Most relevant items
    HYBRID = "hybrid"  # Combined recency + relevance
    SEMANTIC = "semantic"  # Vector similarity
    KEYWORD = "keyword"  # Keyword matching
    GRAPH = "graph"  # Graph traversal


@dataclass
class ContextItem:
    """
    Single unit of context information.
    
    Represents a piece of information stored in memory,
    with metadata for retrieval and ranking.
    """
    
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    conversation_id: Optional[str] = None
    
    # Access tracking
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    # Embedding (populated lazily)
    embedding: Optional[List[float]] = None
    
    # Computed fields
    importance_score: float = 1.0
    relevance_score: float = 0.0
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Calculate importance from metadata
        self.importance_score = self._calculate_importance()
    
    def _calculate_importance(self) -> float:
        """Calculate importance score from metadata."""
        importance_map = {
            "critical": 1.5,
            "high": 1.2,
            "normal": 1.0,
            "low": 0.8,
            "minimal": 0.5
        }
        
        importance = self.metadata.get("importance", "normal")
        return importance_map.get(importance, 1.0)
    
    def mark_accessed(self):
        """Mark item as accessed."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "conversation_id": self.conversation_id,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "importance_score": self.importance_score,
            "relevance_score": self.relevance_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextItem":
        """Create from dictionary."""
        timestamp = None
        if data.get("timestamp"):
            timestamp = datetime.fromisoformat(data["timestamp"])
        
        last_accessed = None
        if data.get("last_accessed"):
            last_accessed = datetime.fromisoformat(data["last_accessed"])
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data["content"],
            metadata=data.get("metadata", {}),
            timestamp=timestamp,
            conversation_id=data.get("conversation_id"),
            access_count=data.get("access_count", 0),
            last_accessed=last_accessed,
            importance_score=data.get("importance_score", 1.0),
            relevance_score=data.get("relevance_score", 0.0)
        )
    
    def content_hash(self) -> str:
        """Generate content hash for deduplication."""
        return hashlib.md5(self.content.encode()).hexdigest()


@dataclass
class ContextRequest:
    """
    Request for context retrieval.
    """
    
    query: str
    max_results: int = 10
    max_tokens: Optional[int] = None
    
    # Layer selection
    include_immediate: bool = True
    include_session: bool = True
    include_long_term: bool = True
    
    # Retrieval strategy
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    
    # Filtering
    filters: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None
    
    # Time range
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    
    # Metadata
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def cache_key(self) -> str:
        """Generate cache key for this request."""
        key_parts = [
            self.query,
            str(self.max_results),
            self.strategy.value,
            str(self.filters) if self.filters else "",
            self.conversation_id or ""
        ]
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()


@dataclass
class ContextResponse:
    """
    Response containing retrieved context.
    """
    
    items: List[ContextItem]
    query: str
    strategy: RetrievalStrategy
    
    total_retrieved: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def total_tokens(self) -> int:
        """Estimate total tokens in response."""
        total_chars = sum(len(item.content) for item in self.items)
        return total_chars // 4  # Rough estimate
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "response_id": self.response_id,
            "query": self.query,
            "strategy": self.strategy.value,
            "items": [item.to_dict() for item in self.items],
            "total_retrieved": self.total_retrieved,
            "total_tokens": self.total_tokens,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ContextMetrics:
    """
    Metrics for context orchestration.
    """
    
    # Storage metrics
    total_stores: int = 0
    avg_store_time: float = 0.0
    
    # Retrieval metrics
    total_retrievals: int = 0
    avg_retrieval_time: float = 0.0
    avg_results_per_retrieval: float = 0.0
    
    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    
    # Layer distribution
    immediate_stores: int = 0
    session_stores: int = 0
    long_term_stores: int = 0
    
    def record_storage(self, elapsed_time: float, layers: List[LayerType]):
        """Record storage operation."""
        self.total_stores += 1
        self.avg_store_time = (
            (self.avg_store_time * (self.total_stores - 1) + elapsed_time)
            / self.total_stores
        )
        
        for layer in layers:
            if layer == LayerType.IMMEDIATE:
                self.immediate_stores += 1
            elif layer == LayerType.SESSION:
                self.session_stores += 1
            elif layer == LayerType.LONG_TERM:
                self.long_term_stores += 1
    
    def record_retrieval(self, elapsed_time: float, num_results: int):
        """Record retrieval operation."""
        self.total_retrievals += 1
        self.avg_retrieval_time = (
            (self.avg_retrieval_time * (self.total_retrievals - 1) + elapsed_time)
            / self.total_retrievals
        )
        self.avg_results_per_retrieval = (
            (self.avg_results_per_retrieval * (self.total_retrievals - 1) + num_results)
            / self.total_retrievals
        )
    
    def record_cache_hit(self):
        """Record cache hit."""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record cache miss."""
        self.cache_misses += 1
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "storage": {
                "total_stores": self.total_stores,
                "avg_store_time": self.avg_store_time,
                "immediate_stores": self.immediate_stores,
                "session_stores": self.session_stores,
                "long_term_stores": self.long_term_stores
            },
            "retrieval": {
                "total_retrievals": self.total_retrievals,
                "avg_retrieval_time": self.avg_retrieval_time,
                "avg_results": self.avg_results_per_retrieval
            },
            "cache": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "hit_rate": self.cache_hit_rate
            }
        }