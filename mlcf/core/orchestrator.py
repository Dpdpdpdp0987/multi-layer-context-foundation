"""
Context Orchestrator - Central coordinator for multi-layer context management.

The orchestrator manages the flow of information between different memory layers,
handles context assembly, and coordinates retrieval strategies.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger
from dataclasses import dataclass, field
import asyncio

from mlcf.memory.immediate_buffer import ImmediateContextBuffer
from mlcf.memory.session_memory import SessionMemory
from mlcf.memory.long_term_store import LongTermStore
from mlcf.core.context_models import (
    ContextItem,
    ContextRequest,
    ContextResponse,
    ContextMetrics,
    LayerType
)


@dataclass
class OrchestratorConfig:
    """Configuration for Context Orchestrator."""
    
    # Buffer settings
    immediate_buffer_size: int = 10
    immediate_buffer_ttl: int = 3600  # 1 hour
    
    # Session settings
    session_max_size: int = 50
    session_consolidation_threshold: int = 100
    
    # Context assembly
    max_context_tokens: int = 4096
    context_overlap_tokens: int = 128
    
    # Retrieval settings
    default_retrieval_strategy: str = "hybrid"
    enable_adaptive_retrieval: bool = True
    
    # Performance
    enable_async: bool = True
    enable_caching: bool = True
    cache_ttl: int = 300  # 5 minutes


class ContextOrchestrator:
    """
    Central orchestrator for multi-layer context management.
    
    Responsibilities:
    - Coordinate between memory layers (Immediate, Session, Long-term)
    - Assemble context for LLM consumption
    - Route storage and retrieval requests
    - Optimize context window usage
    - Track context metrics and performance
    """
    
    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        enable_long_term: bool = True
    ):
        """
        Initialize the Context Orchestrator.
        
        Args:
            config: Orchestrator configuration
            enable_long_term: Whether to enable long-term storage
        """
        self.config = config or OrchestratorConfig()
        self.enable_long_term = enable_long_term
        
        # Initialize memory layers
        self.immediate_buffer = ImmediateContextBuffer(
            max_size=self.config.immediate_buffer_size,
            ttl_seconds=self.config.immediate_buffer_ttl
        )
        
        self.session_memory = SessionMemory(
            max_size=self.config.session_max_size,
            consolidation_threshold=self.config.session_consolidation_threshold
        )
        
        self.long_term_store = None
        if enable_long_term:
            self.long_term_store = LongTermStore()
        
        # Context cache
        self._context_cache: Dict[str, Tuple[ContextResponse, datetime]] = {}
        
        # Metrics
        self.metrics = ContextMetrics()
        
        logger.info("ContextOrchestrator initialized")
    
    async def store(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        layer_hint: Optional[LayerType] = None,
        conversation_id: Optional[str] = None
    ) -> ContextItem:
        """
        Store content in appropriate memory layer(s).
        
        Args:
            content: Content to store
            metadata: Additional metadata
            layer_hint: Suggested target layer (auto-determined if None)
            conversation_id: ID for conversation grouping
            
        Returns:
            ContextItem with storage details
        """
        start_time = datetime.utcnow()
        metadata = metadata or {}
        
        # Create context item
        item = ContextItem(
            content=content,
            metadata=metadata,
            conversation_id=conversation_id,
            timestamp=start_time
        )
        
        # Determine target layer(s)
        if layer_hint:
            target_layers = [layer_hint]
        else:
            target_layers = self._determine_storage_layers(item)
        
        # Store in each layer
        for layer in target_layers:
            if layer == LayerType.IMMEDIATE:
                self.immediate_buffer.add(item)
                logger.debug(f"Stored in immediate buffer: {item.id}")
            
            elif layer == LayerType.SESSION:
                self.session_memory.add(item)
                logger.debug(f"Stored in session memory: {item.id}")
            
            elif layer == LayerType.LONG_TERM and self.long_term_store:
                if self.config.enable_async:
                    asyncio.create_task(self.long_term_store.add_async(item))
                else:
                    await self.long_term_store.add_async(item)
                logger.debug(f"Stored in long-term: {item.id}")
        
        # Update metrics
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        self.metrics.record_storage(elapsed, target_layers)
        
        # Invalidate cache
        if self.config.enable_caching:
            self._invalidate_cache()
        
        return item
    
    def store_sync(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        layer_hint: Optional[LayerType] = None,
        conversation_id: Optional[str] = None
    ) -> ContextItem:
        """Synchronous version of store."""
        return asyncio.run(self.store(content, metadata, layer_hint, conversation_id))
    
    async def retrieve(
        self,
        request: ContextRequest
    ) -> ContextResponse:
        """
        Retrieve and assemble context based on request.
        
        Args:
            request: Context retrieval request
            
        Returns:
            Assembled context response
        """
        start_time = datetime.utcnow()
        
        # Check cache
        if self.config.enable_caching:
            cached = self._get_from_cache(request.cache_key)
            if cached:
                logger.debug(f"Cache hit for: {request.query}")
                self.metrics.record_cache_hit()
                return cached
            self.metrics.record_cache_miss()
        
        # Retrieve from each layer
        immediate_results = self._retrieve_from_immediate(request)
        session_results = self._retrieve_from_session(request)
        long_term_results = []
        
        if self.long_term_store and request.include_long_term:
            long_term_results = await self._retrieve_from_long_term(request)
        
        # Assemble and rank results
        assembled_context = self._assemble_context(
            immediate_results,
            session_results,
            long_term_results,
            request
        )
        
        # Create response
        response = ContextResponse(
            items=assembled_context,
            query=request.query,
            strategy=request.strategy,
            total_retrieved=len(immediate_results) + len(session_results) + len(long_term_results),
            metadata={
                "immediate_count": len(immediate_results),
                "session_count": len(session_results),
                "long_term_count": len(long_term_results),
                "cache_hit": False
            }
        )
        
        # Update cache
        if self.config.enable_caching:
            self._add_to_cache(request.cache_key, response)
        
        # Update metrics
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        self.metrics.record_retrieval(elapsed, len(assembled_context))
        
        return response
    
    def retrieve_sync(self, request: ContextRequest) -> ContextResponse:
        """Synchronous version of retrieve."""
        return asyncio.run(self.retrieve(request))
    
    def _determine_storage_layers(self, item: ContextItem) -> List[LayerType]:
        """
        Determine which layer(s) should store this item.
        
        Logic:
        - All items go to immediate buffer
        - Important items go to session memory
        - Permanent items go to long-term storage
        """
        layers = [LayerType.IMMEDIATE]
        
        importance = item.metadata.get("importance", "normal")
        item_type = item.metadata.get("type", "general")
        persistence = item.metadata.get("persistence", "session")
        
        # Session memory criteria
        if importance in ["high", "critical"] or item_type in ["task", "decision", "preference"]:
            layers.append(LayerType.SESSION)
        
        # Long-term storage criteria
        if persistence == "permanent" or item_type in ["fact", "knowledge", "preference"]:
            if self.enable_long_term:
                layers.append(LayerType.LONG_TERM)
        
        return layers
    
    def _retrieve_from_immediate(self, request: ContextRequest) -> List[ContextItem]:
        """Retrieve from immediate context buffer."""
        if not request.include_immediate:
            return []
        
        # Get recent items
        results = self.immediate_buffer.get_recent(
            max_items=request.max_results,
            conversation_id=request.conversation_id
        )
        
        # Apply query filtering if needed
        if request.query:
            results = [
                item for item in results
                if self._matches_query(item, request.query)
            ]
        
        return results
    
    def _retrieve_from_session(self, request: ContextRequest) -> List[ContextItem]:
        """Retrieve from session memory."""
        if not request.include_session:
            return []
        
        # Search session memory
        results = self.session_memory.search(
            query=request.query,
            max_results=request.max_results,
            filters=request.filters,
            conversation_id=request.conversation_id
        )
        
        return results
    
    async def _retrieve_from_long_term(self, request: ContextRequest) -> List[ContextItem]:
        """Retrieve from long-term storage."""
        if not self.long_term_store:
            return []
        
        # Perform hybrid retrieval
        results = await self.long_term_store.search(
            query=request.query,
            max_results=request.max_results,
            strategy=request.strategy,
            filters=request.filters
        )
        
        return results
    
    def _assemble_context(
        self,
        immediate: List[ContextItem],
        session: List[ContextItem],
        long_term: List[ContextItem],
        request: ContextRequest
    ) -> List[ContextItem]:
        """
        Assemble and rank context from all layers.
        
        Strategy:
        1. Combine results from all layers
        2. Remove duplicates
        3. Rank by relevance and recency
        4. Limit by token budget
        """
        # Combine all results
        all_items: List[Tuple[ContextItem, float, LayerType]] = []
        
        # Add immediate buffer items (highest priority)
        for item in immediate:
            score = self._calculate_score(item, request, LayerType.IMMEDIATE)
            all_items.append((item, score, LayerType.IMMEDIATE))
        
        # Add session memory items
        for item in session:
            score = self._calculate_score(item, request, LayerType.SESSION)
            all_items.append((item, score, LayerType.SESSION))
        
        # Add long-term items
        for item in long_term:
            score = self._calculate_score(item, request, LayerType.LONG_TERM)
            all_items.append((item, score, LayerType.LONG_TERM))
        
        # Remove duplicates (keep highest scoring version)
        unique_items = self._deduplicate(all_items)
        
        # Sort by score
        unique_items.sort(key=lambda x: x[1], reverse=True)
        
        # Apply token budget if specified
        if request.max_tokens:
            final_items = self._apply_token_budget(
                unique_items,
                request.max_tokens
            )
        else:
            final_items = unique_items[:request.max_results]
        
        # Extract just the items (remove scores and layers)
        return [item for item, score, layer in final_items]
    
    def _calculate_score(
        self,
        item: ContextItem,
        request: ContextRequest,
        layer: LayerType
    ) -> float:
        """
        Calculate relevance score for an item.
        
        Factors:
        - Layer weight (immediate > session > long-term)
        - Recency
        - Query relevance
        - Metadata importance
        """
        # Base layer weights
        layer_weights = {
            LayerType.IMMEDIATE: 1.0,
            LayerType.SESSION: 0.8,
            LayerType.LONG_TERM: 0.6
        }
        
        score = layer_weights.get(layer, 0.5)
        
        # Recency bonus (decay over time)
        if item.timestamp:
            age_hours = (datetime.utcnow() - item.timestamp).total_seconds() / 3600
            recency_factor = 1.0 / (1.0 + age_hours / 24)  # Decay over days
            score *= recency_factor
        
        # Query relevance (simple keyword matching for now)
        if request.query:
            relevance = self._calculate_relevance(item.content, request.query)
            score *= (0.5 + 0.5 * relevance)  # Scale between 0.5 and 1.0
        
        # Importance metadata
        importance_map = {
            "critical": 1.5,
            "high": 1.2,
            "normal": 1.0,
            "low": 0.8
        }
        importance = item.metadata.get("importance", "normal")
        score *= importance_map.get(importance, 1.0)
        
        return score
    
    def _calculate_relevance(self, content: str, query: str) -> float:
        """Calculate simple keyword-based relevance."""
        content_lower = content.lower()
        query_lower = query.lower()
        
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        
        if not query_words:
            return 0.0
        
        # Jaccard similarity
        intersection = len(query_words & content_words)
        union = len(query_words | content_words)
        
        return intersection / union if union > 0 else 0.0
    
    def _matches_query(self, item: ContextItem, query: str) -> bool:
        """Check if item matches query (simple keyword matching)."""
        return any(
            word.lower() in item.content.lower()
            for word in query.split()
        )
    
    def _deduplicate(
        self,
        items: List[Tuple[ContextItem, float, LayerType]]
    ) -> List[Tuple[ContextItem, float, LayerType]]:
        """Remove duplicate items, keeping highest scoring version."""
        seen_ids = set()
        seen_content = {}  # content hash -> (item, score, layer)
        
        unique_items = []
        
        for item, score, layer in items:
            # Skip if we've seen this exact ID
            if item.id in seen_ids:
                continue
            
            # Check for content duplication
            content_hash = hash(item.content.strip().lower())
            
            if content_hash in seen_content:
                # Keep the higher scoring version
                existing_score = seen_content[content_hash][1]
                if score > existing_score:
                    # Remove old version
                    unique_items = [
                        x for x in unique_items
                        if x[0].content.strip().lower() != item.content.strip().lower()
                    ]
                    seen_content[content_hash] = (item, score, layer)
                    unique_items.append((item, score, layer))
                    seen_ids.add(item.id)
            else:
                seen_content[content_hash] = (item, score, layer)
                unique_items.append((item, score, layer))
                seen_ids.add(item.id)
        
        return unique_items
    
    def _apply_token_budget(
        self,
        items: List[Tuple[ContextItem, float, LayerType]],
        max_tokens: int
    ) -> List[Tuple[ContextItem, float, LayerType]]:
        """Limit items to fit within token budget."""
        total_tokens = 0
        selected_items = []
        
        for item, score, layer in items:
            # Rough estimate: 1 token ≈ 4 characters
            item_tokens = len(item.content) // 4
            
            if total_tokens + item_tokens <= max_tokens:
                selected_items.append((item, score, layer))
                total_tokens += item_tokens
            else:
                # Budget exceeded
                break
        
        return selected_items
    
    def _get_from_cache(self, key: str) -> Optional[ContextResponse]:
        """Get response from cache if valid."""
        if key not in self._context_cache:
            return None
        
        response, cached_at = self._context_cache[key]
        age = (datetime.utcnow() - cached_at).total_seconds()
        
        if age > self.config.cache_ttl:
            # Cache expired
            del self._context_cache[key]
            return None
        
        response.metadata["cache_hit"] = True
        return response
    
    def _add_to_cache(self, key: str, response: ContextResponse):
        """Add response to cache."""
        self._context_cache[key] = (response, datetime.utcnow())
        
        # Simple cache size limit
        if len(self._context_cache) > 100:
            # Remove oldest entries
            sorted_items = sorted(
                self._context_cache.items(),
                key=lambda x: x[1][1]
            )
            for k, _ in sorted_items[:20]:
                del self._context_cache[k]
    
    def _invalidate_cache(self):
        """Invalidate entire cache."""
        self._context_cache.clear()
    
    def clear_immediate(self):
        """Clear immediate context buffer."""
        self.immediate_buffer.clear()
        logger.info("Immediate buffer cleared")
    
    def clear_session(self, conversation_id: Optional[str] = None):
        """Clear session memory."""
        if conversation_id:
            self.session_memory.clear_conversation(conversation_id)
            logger.info(f"Session cleared for conversation: {conversation_id}")
        else:
            self.session_memory.clear()
            logger.info("All session memory cleared")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics."""
        return self.metrics.to_dict()