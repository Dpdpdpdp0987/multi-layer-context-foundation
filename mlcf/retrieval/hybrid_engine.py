"""
Hybrid Retrieval Engine - Combines semantic, keyword, and graph search.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import numpy as np
from loguru import logger

from mlcf.retrieval.bm25_search import BM25Search
from mlcf.retrieval.adaptive_chunking import AdaptiveChunker


@dataclass
class RetrievalResult:
    """Unified retrieval result."""
    id: str
    content: str
    score: float
    method: str  # semantic, keyword, graph, hybrid
    metadata: Dict[str, Any]
    component_scores: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "score": self.score,
            "method": self.method,
            "metadata": self.metadata,
            "component_scores": self.component_scores
        }


class HybridRetrievalEngine:
    """
    Hybrid retrieval engine combining multiple search strategies.
    
    Implements:
    - Semantic search (vector similarity)
    - Keyword search (BM25)
    - Graph search (relationship traversal)
    - Intelligent result fusion and reranking
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        embedding_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize hybrid retrieval engine.
        
        Args:
            config: Retrieval configuration
            embedding_config: Embedding model configuration
        """
        self.config = config or {}
        self.embedding_config = embedding_config or {}
        
        # Strategy weights
        self.semantic_weight = self.config.get("semantic_weight", 0.5)
        self.keyword_weight = self.config.get("keyword_weight", 0.3)
        self.graph_weight = self.config.get("graph_weight", 0.2)
        
        # Initialize components
        self.bm25_search = BM25Search(
            k1=self.config.get("bm25_k1", 1.5),
            b=self.config.get("bm25_b", 0.75)
        )
        
        self.chunker = AdaptiveChunker(
            chunk_size=self.config.get("chunk_size", 512),
            base_overlap=self.config.get("chunk_overlap", 50),
            adaptive_overlap=self.config.get("adaptive_overlap", True)
        )
        
        # Lazy initialization
        self._vector_search = None
        self._graph_search = None
        self._reranker = None
        
        # Document storage
        self.documents: Dict[str, Dict[str, Any]] = {}
        
        logger.info(
            f"HybridRetrievalEngine initialized: "
            f"weights=({self.semantic_weight}, {self.keyword_weight}, {self.graph_weight})"
        )
    
    def index_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        auto_chunk: bool = True
    ):
        """
        Index document for retrieval.
        
        Args:
            doc_id: Document ID
            content: Document content
            metadata: Optional metadata
            auto_chunk: Automatically chunk long documents
        """
        metadata = metadata or {}
        
        # Store original document
        self.documents[doc_id] = {
            "content": content,
            "metadata": metadata
        }
        
        # Chunk if needed
        if auto_chunk and len(content) > self.config.get("chunk_size", 512):
            chunks = self.chunker.chunk_text(content, metadata)
            
            for chunk in chunks:
                chunk_id = f"{doc_id}_{chunk.chunk_id}"
                
                # Index chunk in BM25
                self.bm25_search.add_document(
                    doc_id=chunk_id,
                    content=chunk.content,
                    metadata={
                        **metadata,
                        "parent_doc_id": doc_id,
                        "chunk_index": chunk.metadata.get("chunk_index"),
                        "is_chunk": True
                    }
                )
                
                # TODO: Index in vector store
                # TODO: Index in graph store
        else:
            # Index whole document
            self.bm25_search.add_document(
                doc_id=doc_id,
                content=content,
                metadata=metadata
            )
            
            # TODO: Index in vector store
            # TODO: Index in graph store
        
        logger.debug(f"Indexed document: {doc_id}")
    
    def retrieve(
        self,
        query: str,
        max_results: int = 10,
        strategy: str = "hybrid",
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            strategy: Retrieval strategy (hybrid, semantic, keyword, graph)
            filters: Optional filters
            
        Returns:
            List of retrieval results
        """
        if strategy == "hybrid":
            return self._hybrid_retrieve(query, max_results, filters)
        elif strategy == "semantic":
            return self._semantic_retrieve(query, max_results, filters)
        elif strategy == "keyword":
            return self._keyword_retrieve(query, max_results, filters)
        elif strategy == "graph":
            return self._graph_retrieve(query, max_results, filters)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    def _hybrid_retrieve(
        self,
        query: str,
        max_results: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval combining all strategies.
        
        Args:
            query: Search query
            max_results: Maximum results
            filters: Optional filters
            
        Returns:
            Fused and ranked results
        """
        # Retrieve from each method
        keyword_results = self._keyword_retrieve(
            query,
            max_results * 2,
            filters
        )
        
        semantic_results = self._semantic_retrieve(
            query,
            max_results * 2,
            filters
        )
        
        graph_results = self._graph_retrieve(
            query,
            max_results * 2,
            filters
        )
        
        # Fuse results
        fused_results = self._fuse_results(
            keyword_results,
            semantic_results,
            graph_results
        )
        
        # Apply reranking if enabled
        if self.config.get("reranking_enabled", True):
            fused_results = self._rerank_results(query, fused_results)
        
        return fused_results[:max_results]
    
    def _keyword_retrieve(
        self,
        query: str,
        max_results: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        BM25 keyword retrieval.
        
        Args:
            query: Search query
            max_results: Maximum results
            filters: Optional filters
            
        Returns:
            Keyword search results
        """
        results = self.bm25_search.search(
            query=query,
            max_results=max_results,
            filters=filters
        )
        
        logger.debug(f"Keyword search returned {len(results)} results")
        return results
    
    def _semantic_retrieve(
        self,
        query: str,
        max_results: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Semantic vector search.
        
        Args:
            query: Search query
            max_results: Maximum results
            filters: Optional filters
            
        Returns:
            Semantic search results
        """
        # TODO: Implement vector search
        logger.debug("Semantic search not yet implemented")
        return []
    
    def _graph_retrieve(
        self,
        query: str,
        max_results: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Graph-based retrieval.
        
        Args:
            query: Search query
            max_results: Maximum results
            filters: Optional filters
            
        Returns:
            Graph search results
        """
        # TODO: Implement graph search
        logger.debug("Graph search not yet implemented")
        return []
    
    def _fuse_results(
        self,
        keyword_results: List[Dict],
        semantic_results: List[Dict],
        graph_results: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Fuse results from multiple strategies using weighted scoring.
        
        Args:
            keyword_results: BM25 results
            semantic_results: Vector search results
            graph_results: Graph search results
            
        Returns:
            Fused results
        """
        # Normalize scores to [0, 1] range for each method
        keyword_results = self._normalize_scores(keyword_results)
        semantic_results = self._normalize_scores(semantic_results)
        graph_results = self._normalize_scores(graph_results)
        
        # Create score map: doc_id -> weighted score
        score_map: Dict[str, Dict[str, Any]] = {}
        
        # Process keyword results
        for result in keyword_results:
            doc_id = result["id"]
            if doc_id not in score_map:
                score_map[doc_id] = {
                    "id": doc_id,
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "combined_score": 0.0,
                    "component_scores": {}
                }
            
            score_map[doc_id]["component_scores"]["keyword"] = result["score"]
            score_map[doc_id]["combined_score"] += result["score"] * self.keyword_weight
        
        # Process semantic results
        for result in semantic_results:
            doc_id = result["id"]
            if doc_id not in score_map:
                score_map[doc_id] = {
                    "id": doc_id,
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "combined_score": 0.0,
                    "component_scores": {}
                }
            
            score_map[doc_id]["component_scores"]["semantic"] = result["score"]
            score_map[doc_id]["combined_score"] += result["score"] * self.semantic_weight
        
        # Process graph results
        for result in graph_results:
            doc_id = result["id"]
            if doc_id not in score_map:
                score_map[doc_id] = {
                    "id": doc_id,
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "combined_score": 0.0,
                    "component_scores": {}
                }
            
            score_map[doc_id]["component_scores"]["graph"] = result["score"]
            score_map[doc_id]["combined_score"] += result["score"] * self.graph_weight
        
        # Convert to list and sort
        fused_results = list(score_map.values())
        fused_results.sort(
            key=lambda x: x["combined_score"],
            reverse=True
        )
        
        # Add method and final score
        for result in fused_results:
            result["method"] = "hybrid"
            result["score"] = result["combined_score"]
        
        logger.debug(
            f"Fused {len(keyword_results)} keyword + {len(semantic_results)} semantic + "
            f"{len(graph_results)} graph results into {len(fused_results)} results"
        )
        
        return fused_results
    
    def _normalize_scores(self, results: List[Dict]) -> List[Dict]:
        """
        Normalize scores to [0, 1] range.
        
        Args:
            results: Results to normalize
            
        Returns:
            Results with normalized scores
        """
        if not results:
            return results
        
        scores = [r["score"] for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        # Avoid division by zero
        if max_score - min_score < 1e-10:
            for result in results:
                result["score"] = 1.0
            return results
        
        # Normalize
        for result in results:
            result["score"] = (result["score"] - min_score) / (max_score - min_score)
        
        return results
    
    def _rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Rerank results using cross-encoder.
        
        Args:
            query: Original query
            results: Results to rerank
            
        Returns:
            Reranked results
        """
        # TODO: Implement cross-encoder reranking
        logger.debug(f"Reranking {len(results)} results (placeholder)")
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get retrieval engine statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "total_documents": len(self.documents),
            "bm25_stats": self.bm25_search.get_statistics(),
            "weights": {
                "semantic": self.semantic_weight,
                "keyword": self.keyword_weight,
                "graph": self.graph_weight
            }
        }