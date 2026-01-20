"""
Main context manager orchestrating multi-layer memory and retrieval.
"""

from typing import Any, Dict, List, Optional
from loguru import logger

from mlcf.memory.memory_layers import ShortTermMemory, WorkingMemory, LongTermMemory
from mlcf.retrieval.hybrid_retriever import HybridRetriever
from mlcf.core.config import Config


class ContextManager:
    """
    Central orchestrator for multi-layer context management.
    
    Manages the flow of information between short-term, working, and long-term
    memory layers, and coordinates hybrid retrieval strategies.
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        vector_db: str = "qdrant",
        graph_db: str = "neo4j",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize the context manager.
        
        Args:
            config: Configuration object
            vector_db: Vector database provider (qdrant, chroma, milvus)
            graph_db: Graph database provider (neo4j, libsql)
            embedding_model: Model for generating embeddings
        """
        self.config = config or Config()
        self.vector_db = vector_db
        self.graph_db = graph_db
        self.embedding_model = embedding_model
        
        # Initialize memory layers
        self.short_term = ShortTermMemory(max_size=self.config.short_term_max_size)
        self.working = WorkingMemory(max_size=self.config.working_memory_max_size)
        self.long_term = LongTermMemory(
            vector_db=vector_db,
            graph_db=graph_db,
            embedding_model=embedding_model
        )
        
        # Initialize retriever
        self.retriever = HybridRetriever(
            vector_db=self.long_term.vector_store,
            graph_db=self.long_term.graph_store,
            config=self.config.retrieval_config
        )
        
        logger.info(f"ContextManager initialized with {vector_db} and {graph_db}")
    
    def store(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        layer: str = "auto"
    ) -> str:
        """
        Store information in appropriate memory layer.
        
        Args:
            content: Content to store
            metadata: Additional metadata
            layer: Target layer (auto, short, working, long)
            
        Returns:
            Document ID
        """
        metadata = metadata or {}
        
        if layer == "auto":
            # Determine appropriate layer based on content and metadata
            layer = self._determine_layer(content, metadata)
        
        if layer == "short":
            return self.short_term.add(content, metadata)
        elif layer == "working":
            return self.working.add(content, metadata)
        elif layer == "long":
            return self.long_term.add(content, metadata)
        else:
            raise ValueError(f"Unknown layer: {layer}")
    
    def retrieve(
        self,
        query: str,
        max_results: int = 5,
        strategy: str = "hybrid",
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context from all memory layers.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            strategy: Retrieval strategy (hybrid, semantic, keyword, graph)
            filters: Optional filters
            
        Returns:
            List of relevant context items
        """
        # Retrieve from all layers
        short_term_results = self.short_term.search(query, max_results=max_results)
        working_results = self.working.search(query, max_results=max_results)
        long_term_results = self.retriever.retrieve(
            query=query,
            max_results=max_results,
            strategy=strategy,
            filters=filters
        )
        
        # Merge and rank results
        all_results = self._merge_results(
            short_term_results,
            working_results,
            long_term_results
        )
        
        return all_results[:max_results]
    
    def _determine_layer(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        Determine appropriate memory layer for content.
        
        Args:
            content: Content to analyze
            metadata: Associated metadata
            
        Returns:
            Layer name (short, working, long)
        """
        # Simple heuristic - can be enhanced with ML classifier
        importance = metadata.get("importance", "normal")
        content_type = metadata.get("type", "general")
        
        if importance == "permanent" or content_type in ["fact", "preference"]:
            return "long"
        elif importance == "session" or content_type == "task":
            return "working"
        else:
            return "short"
    
    def _merge_results(
        self,
        short_results: List[Dict],
        working_results: List[Dict],
        long_results: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Merge and rank results from different memory layers.
        
        Args:
            short_results: Results from short-term memory
            working_results: Results from working memory
            long_results: Results from long-term memory
            
        Returns:
            Merged and ranked results
        """
        # Combine all results with layer weights
        all_results = []
        
        for result in short_results:
            result["layer"] = "short_term"
            result["layer_weight"] = 1.0
            all_results.append(result)
        
        for result in working_results:
            result["layer"] = "working"
            result["layer_weight"] = 0.8
            all_results.append(result)
        
        for result in long_results:
            result["layer"] = "long_term"
            result["layer_weight"] = 0.6
            all_results.append(result)
        
        # Sort by combined score
        all_results.sort(
            key=lambda x: x.get("score", 0) * x.get("layer_weight", 1.0),
            reverse=True
        )
        
        return all_results
    
    def clear_short_term(self):
        """Clear short-term memory."""
        self.short_term.clear()
        logger.info("Short-term memory cleared")
    
    def clear_working(self):
        """Clear working memory."""
        self.working.clear()
        logger.info("Working memory cleared")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Cleanup resources
        pass