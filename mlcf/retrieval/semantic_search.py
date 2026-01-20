"""
Semantic Search - Vector-based similarity search.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from loguru import logger

from mlcf.embeddings.embedding_generator import EmbeddingGenerator
from mlcf.storage.vector_store import QdrantVectorStore, VectorSearchResult


@dataclass
class SemanticSearchConfig:
    """Configuration for semantic search."""
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    score_threshold: float = 0.5
    max_results: int = 10
    normalize_scores: bool = True


class SemanticSearch:
    """
    Semantic search using vector embeddings.
    
    Provides similarity search based on semantic meaning
    rather than keyword matching.
    """
    
    def __init__(
        self,
        vector_store: QdrantVectorStore,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        config: Optional[SemanticSearchConfig] = None
    ):
        """
        Initialize semantic search.
        
        Args:
            vector_store: Vector store instance
            embedding_generator: Embedding generator instance
            config: Search configuration
        """
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.config = config or SemanticSearchConfig()
        
        logger.info("SemanticSearch initialized")
    
    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search.
        
        Args:
            query: Search query
            max_results: Maximum results (uses config if None)
            score_threshold: Minimum score (uses config if None)
            filters: Metadata filters
            
        Returns:
            List of search results
        """
        max_results = max_results or self.config.max_results
        score_threshold = score_threshold or self.config.score_threshold
        
        # Perform vector search
        results = self.vector_store.search(
            query=query,
            max_results=max_results,
            score_threshold=score_threshold,
            filters=filters
        )
        
        # Convert to dictionary format
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "content": result.content,
                "score": result.score,
                "metadata": result.metadata,
                "method": "semantic"
            })
        
        # Normalize scores if requested
        if self.config.normalize_scores and formatted_results:
            formatted_results = self._normalize_scores(formatted_results)
        
        logger.debug(f"Semantic search returned {len(formatted_results)} results")
        return formatted_results
    
    def search_similar(
        self,
        doc_id: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find similar documents to a given document.
        
        Args:
            doc_id: Document ID to find similar documents for
            max_results: Maximum results
            
        Returns:
            List of similar documents
        """
        # This would require retrieving the embedding for doc_id
        # and searching with it
        logger.warning("search_similar not fully implemented")
        return []
    
    def _normalize_scores(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize scores to [0, 1] range.
        
        Args:
            results: Search results
            
        Returns:
            Results with normalized scores
        """
        if not results:
            return results
        
        scores = [r['score'] for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score - min_score < 1e-10:
            return results
        
        for result in results:
            result['score'] = (result['score'] - min_score) / (max_score - min_score)
        
        return results