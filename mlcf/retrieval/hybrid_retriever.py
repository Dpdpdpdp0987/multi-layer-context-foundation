"""
Hybrid Retriever - Updated with complete graph search integration.
"""

from typing import Any, Dict, List, Optional
from loguru import logger

from mlcf.retrieval.bm25_search import BM25Search
from mlcf.retrieval.semantic_search import SemanticSearch
from mlcf.retrieval.graph_search import GraphSearch
from mlcf.storage.vector_store import QdrantVectorStore
from mlcf.graph.neo4j_store import Neo4jStore


class HybridRetriever:
    """
    Complete hybrid retrieval combining semantic, keyword, and graph search.
    
    Implements intelligent fusion of multiple search strategies.
    """
    
    def __init__(
        self,
        vector_store: Optional[QdrantVectorStore] = None,
        graph_store: Optional[Neo4jStore] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            vector_store: Vector store for semantic search
            graph_store: Graph store for graph search
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Strategy weights
        self.semantic_weight = self.config.get("semantic_weight", 0.5)
        self.keyword_weight = self.config.get("keyword_weight", 0.3)
        self.graph_weight = self.config.get("graph_weight", 0.2)
        
        # Initialize search components
        self.bm25_search = BM25Search()
        
        self.semantic_search = None
        if vector_store:
            self.semantic_search = SemanticSearch(vector_store=vector_store)
        
        self.graph_search = None
        if graph_store:
            self.graph_search = GraphSearch(neo4j_store=graph_store)
        
        logger.info(
            f"HybridRetriever initialized: "
            f"semantic={self.semantic_search is not None}, "
            f"keyword=True, "
            f"graph={self.graph_search is not None}"
        )
    
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
            max_results: Maximum results
            strategy: Strategy (hybrid, semantic, keyword, graph)
            filters: Optional filters
            
        Returns:
            Retrieved results
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
        """
        # Retrieve from each method
        keyword_results = self._keyword_retrieve(query, max_results * 2, filters)
        semantic_results = self._semantic_retrieve(query, max_results * 2, filters)
        graph_results = self._graph_retrieve(query, max_results * 2, filters)
        
        # Fuse results
        fused = self._fuse_results(keyword_results, semantic_results, graph_results)
        
        return fused[:max_results]
    
    def _keyword_retrieve(
        self,
        query: str,
        max_results: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """BM25 keyword retrieval."""
        return self.bm25_search.search(query, max_results, filters)
    
    def _semantic_retrieve(
        self,
        query: str,
        max_results: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Semantic vector retrieval."""
        if not self.semantic_search:
            return []
        return self.semantic_search.search(query, max_results, filters=filters)
    
    def _graph_retrieve(
        self,
        query: str,
        max_results: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Graph-based retrieval."""
        if not self.graph_search:
            return []
        return self.graph_search.search(query, max_results)
    
    def _fuse_results(
        self,
        keyword: List[Dict],
        semantic: List[Dict],
        graph: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Fuse results from multiple strategies."""
        # Normalize scores
        keyword = self._normalize_scores(keyword)
        semantic = self._normalize_scores(semantic)
        graph = self._normalize_scores(graph)
        
        # Combine scores
        score_map = {}
        
        for result in keyword:
            doc_id = result["id"]
            score_map[doc_id] = {
                **result,
                "combined_score": result["score"] * self.keyword_weight,
                "component_scores": {"keyword": result["score"]}
            }
        
        for result in semantic:
            doc_id = result["id"]
            if doc_id not in score_map:
                score_map[doc_id] = {
                    **result,
                    "combined_score": 0.0,
                    "component_scores": {}
                }
            score_map[doc_id]["component_scores"]["semantic"] = result["score"]
            score_map[doc_id]["combined_score"] += result["score"] * self.semantic_weight
        
        for result in graph:
            doc_id = result["id"]
            if doc_id not in score_map:
                score_map[doc_id] = {
                    **result,
                    "combined_score": 0.0,
                    "component_scores": {}
                }
            score_map[doc_id]["component_scores"]["graph"] = result["score"]
            score_map[doc_id]["combined_score"] += result["score"] * self.graph_weight
        
        # Sort by combined score
        results = list(score_map.values())
        results.sort(key=lambda x: x["combined_score"], reverse=True)
        
        for r in results:
            r["score"] = r["combined_score"]
            r["method"] = "hybrid"
        
        return results
    
    def _normalize_scores(self, results: List[Dict]) -> List[Dict]:
        """Normalize scores to [0, 1]."""
        if not results:
            return results
        
        scores = [r["score"] for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score - min_score < 1e-10:
            return results
        
        for result in results:
            result["score"] = (result["score"] - min_score) / (max_score - min_score)
        
        return results