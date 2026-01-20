"""
Context Orchestrator - Central coordinator for multi-layer context management.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
from loguru import logger

from mlcf.memory.immediate_buffer import ImmediateContextBuffer
from mlcf.memory.session_memory import SessionMemory
from mlcf.memory.persistent_memory import PersistentMemory
from mlcf.retrieval.hybrid_engine import HybridRetrievalEngine
from mlcf.core.config import Config


class ContextPriority(Enum):
    """Priority levels for context items."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class ContextType(Enum):
    """Types of context."""
    CONVERSATION = "conversation"
    TASK = "task"
    FACT = "fact"
    PREFERENCE = "preference"
    EVENT = "event"
    ENTITY = "entity"


@dataclass
class ContextItem:
    """Represents a single context item."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    context_type: ContextType = ContextType.CONVERSATION
    priority: ContextPriority = ContextPriority.MEDIUM
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    relevance_score: float = 1.0
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.context_type, str):
            self.context_type = ContextType(self.context_type)
        if isinstance(self.priority, int):
            self.priority = ContextPriority(self.priority)
    
    def is_expired(self) -> bool:
        """Check if context item has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def update_access(self):
        """Update access tracking."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "context_type": self.context_type.value,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "relevance_score": self.relevance_score,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat(),
        }


class ContextOrchestrator:
    """
    Central orchestrator for multi-layer context management.
    
    Coordinates between immediate buffer, session memory, and persistent storage.
    Implements intelligent context promotion, eviction, and retrieval strategies.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the context orchestrator.
        
        Args:
            config: Configuration object
        """
        self.config = config or Config()
        
        # Initialize memory layers
        self.immediate_buffer = ImmediateContextBuffer(
            max_size=self.config.short_term_max_size,
            max_tokens=self.config.memory_config.get("immediate_max_tokens", 2048)
        )
        
        self.session_memory = SessionMemory(
            max_size=self.config.working_memory_max_size,
            relevance_threshold=self.config.memory_config.relevance_threshold,
            session_timeout=timedelta(hours=2)
        )
        
        self.persistent_memory = PersistentMemory(
            config=self.config.database_config
        )
        
        # Initialize retrieval engine
        self.retrieval_engine = HybridRetrievalEngine(
            config=self.config.retrieval_config,
            embedding_config=self.config.embedding_config
        )
        
        # State tracking
        self.current_session_id: Optional[str] = None
        self.context_budget_used: int = 0
        self.max_context_budget: int = self.config.memory_config.get("max_context_tokens", 4096)
        
        logger.info("ContextOrchestrator initialized")
    
    def add_context(
        self,
        content: str,
        context_type: ContextType = ContextType.CONVERSATION,
        priority: ContextPriority = ContextPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
        layer: str = "auto"
    ) -> str:
        """
        Add context to appropriate memory layer.
        
        Args:
            content: Context content
            context_type: Type of context
            priority: Priority level
            metadata: Additional metadata
            layer: Target layer (auto, immediate, session, persistent)
            
        Returns:
            Context item ID
        """
        # Create context item
        item = ContextItem(
            content=content,
            context_type=context_type,
            priority=priority,
            metadata=metadata or {}
        )
        
        # Determine target layer
        if layer == "auto":
            layer = self._determine_layer(item)
        
        # Add to appropriate layer
        if layer == "immediate":
            self.immediate_buffer.add(item)
            logger.debug(f"Added to immediate buffer: {item.id}")
        elif layer == "session":
            self.session_memory.add(item)
            logger.debug(f"Added to session memory: {item.id}")
        elif layer == "persistent":
            self.persistent_memory.add(item)
            logger.debug(f"Added to persistent memory: {item.id}")
        else:
            raise ValueError(f"Unknown layer: {layer}")
        
        # Check for promotion opportunities
        self._check_promotion(item)
        
        # Update context budget
        self._update_context_budget()
        
        return item.id
    
    def retrieve_context(
        self,
        query: str,
        max_results: int = 10,
        strategy: str = "hybrid",
        time_decay: bool = True,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ContextItem]:
        """
        Retrieve relevant context from all layers.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            strategy: Retrieval strategy
            time_decay: Apply time-based decay to scores
            filters: Optional filters
            
        Returns:
            List of relevant context items
        """
        results = []
        
        # Search immediate buffer (always include recent context)
        immediate_results = self.immediate_buffer.search(
            query=query,
            max_results=max_results
        )
        results.extend(immediate_results)
        
        # Search session memory
        session_results = self.session_memory.search(
            query=query,
            max_results=max_results,
            filters=filters
        )
        results.extend(session_results)
        
        # Search persistent memory using hybrid retrieval
        persistent_results = self.retrieval_engine.retrieve(
            query=query,
            max_results=max_results * 2,  # Retrieve more for better fusion
            strategy=strategy,
            filters=filters
        )
        
        # Convert to ContextItems
        for result in persistent_results:
            item = self._result_to_context_item(result)
            results.append(item)
        
        # Apply time decay if requested
        if time_decay:
            results = self._apply_time_decay(results)
        
        # Deduplicate and merge scores
        results = self._deduplicate_results(results)
        
        # Sort by combined score
        results.sort(
            key=lambda x: x.relevance_score,
            reverse=True
        )
        
        # Update access tracking
        for item in results[:max_results]:
            item.update_access()
        
        return results[:max_results]
    
    def get_active_context(
        self,
        max_tokens: Optional[int] = None
    ) -> Tuple[List[ContextItem], int]:
        """
        Get currently active context within token budget.
        
        Args:
            max_tokens: Maximum token budget (uses default if None)
            
        Returns:
            Tuple of (context items, total tokens used)
        """
        max_tokens = max_tokens or self.max_context_budget
        
        # Get all immediate buffer items (highest priority)
        immediate_items = self.immediate_buffer.get_all()
        
        # Get relevant session items
        session_items = self.session_memory.get_active_items()
        
        # Combine and sort by priority and recency
        all_items = immediate_items + session_items
        all_items.sort(
            key=lambda x: (x.priority.value, -x.timestamp.timestamp())
        )
        
        # Pack within token budget
        selected_items = []
        total_tokens = 0
        
        for item in all_items:
            item_tokens = self._estimate_tokens(item.content)
            
            if total_tokens + item_tokens <= max_tokens:
                selected_items.append(item)
                total_tokens += item_tokens
            else:
                break
        
        return selected_items, total_tokens
    
    def clear_immediate_buffer(self):
        """Clear immediate context buffer."""
        self.immediate_buffer.clear()
        logger.info("Immediate buffer cleared")
    
    def clear_session(self, session_id: Optional[str] = None):
        """Clear session memory."""
        self.session_memory.clear(session_id)
        logger.info(f"Session memory cleared: {session_id or 'current'}")
    
    def start_new_session(self, session_id: Optional[str] = None) -> str:
        """Start a new session."""
        session_id = session_id or str(uuid.uuid4())
        self.current_session_id = session_id
        self.session_memory.start_session(session_id)
        logger.info(f"Started new session: {session_id}")
        return session_id
    
    def _determine_layer(self, item: ContextItem) -> str:
        """
        Determine appropriate layer for context item.
        
        Args:
            item: Context item to classify
            
        Returns:
            Layer name
        """
        # Critical priority or facts always go to persistent
        if item.priority == ContextPriority.CRITICAL:
            return "persistent"
        
        if item.context_type in [ContextType.FACT, ContextType.PREFERENCE]:
            return "persistent"
        
        # Tasks and events go to session
        if item.context_type in [ContextType.TASK, ContextType.EVENT]:
            return "session"
        
        # Recent conversation goes to immediate
        if item.context_type == ContextType.CONVERSATION:
            return "immediate"
        
        # Default to session
        return "session"
    
    def _check_promotion(self, item: ContextItem):
        """
        Check if item should be promoted to higher layer.
        
        Args:
            item: Context item to check
        """
        # Promote frequently accessed items
        if item.access_count > 5:
            # Consider promoting to persistent
            if item.context_type in [ContextType.FACT, ContextType.PREFERENCE]:
                self.persistent_memory.add(item)
                logger.debug(f"Promoted item to persistent: {item.id}")
    
    def _update_context_budget(self):
        """Update context budget tracking."""
        active_items, total_tokens = self.get_active_context()
        self.context_budget_used = total_tokens
        
        # Log warning if approaching budget
        usage_percent = (total_tokens / self.max_context_budget) * 100
        if usage_percent > 80:
            logger.warning(
                f"Context budget at {usage_percent:.1f}% ({total_tokens}/{self.max_context_budget} tokens)"
            )
    
    def _apply_time_decay(self, items: List[ContextItem]) -> List[ContextItem]:
        """
        Apply time-based decay to relevance scores.
        
        Args:
            items: Context items
            
        Returns:
            Items with updated scores
        """
        now = datetime.utcnow()
        
        for item in items:
            # Calculate age in hours
            age_hours = (now - item.timestamp).total_seconds() / 3600
            
            # Apply exponential decay
            # Half-life of 24 hours
            decay_factor = 0.5 ** (age_hours / 24)
            
            # Update relevance score
            item.relevance_score *= decay_factor
        
        return items
    
    def _deduplicate_results(self, items: List[ContextItem]) -> List[ContextItem]:
        """
        Remove duplicate items, keeping highest scoring version.
        
        Args:
            items: Context items
            
        Returns:
            Deduplicated items
        """
        seen_ids = {}
        deduplicated = []
        
        for item in items:
            if item.id not in seen_ids:
                seen_ids[item.id] = item
                deduplicated.append(item)
            else:
                # Keep version with higher score
                existing = seen_ids[item.id]
                if item.relevance_score > existing.relevance_score:
                    seen_ids[item.id] = item
                    deduplicated.remove(existing)
                    deduplicated.append(item)
        
        return deduplicated
    
    def _result_to_context_item(self, result: Dict[str, Any]) -> ContextItem:
        """
        Convert retrieval result to ContextItem.
        
        Args:
            result: Retrieval result dictionary
            
        Returns:
            ContextItem instance
        """
        return ContextItem(
            id=result.get("id", str(uuid.uuid4())),
            content=result.get("content", ""),
            context_type=ContextType(result.get("type", "conversation")),
            priority=ContextPriority.MEDIUM,
            metadata=result.get("metadata", {}),
            relevance_score=result.get("score", 0.0)
        )
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 characters per token
        return len(text) // 4
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get orchestrator statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "immediate_buffer_size": len(self.immediate_buffer.get_all()),
            "session_memory_size": len(self.session_memory.get_all()),
            "current_session_id": self.current_session_id,
            "context_budget_used": self.context_budget_used,
            "context_budget_max": self.max_context_budget,
            "budget_usage_percent": (self.context_budget_used / self.max_context_budget) * 100,
        }