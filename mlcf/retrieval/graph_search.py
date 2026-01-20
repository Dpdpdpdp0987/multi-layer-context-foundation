"""
Graph Search - Graph-based retrieval using relationship traversal.
"""

from typing import Any, Dict, List, Optional
from loguru import logger

from mlcf.graph.neo4j_store import Neo4jStore


class GraphSearch:
    """
    Graph-based search and retrieval.
    
    Retrieves information by traversing entity relationships
    in the knowledge graph.
    """
    
    def __init__(
        self,
        neo4j_store: Neo4jStore,
        max_depth: int = 3,
        max_results: int = 10
    ):
        """
        Initialize graph search.
        
        Args:
            neo4j_store: Neo4j store instance
            max_depth: Maximum traversal depth
            max_results: Maximum results per query
        """
        self.neo4j_store = neo4j_store
        self.max_depth = max_depth
        self.max_results = max_results
        
        logger.info(f"GraphSearch initialized: max_depth={max_depth}")
    
    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        entity_types: Optional[List[str]] = None,
        relationship_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search graph for relevant entities and relationships.
        
        Args:
            query: Search query
            max_results: Maximum results
            entity_types: Filter by entity types
            relationship_types: Filter by relationship types
            
        Returns:
            List of results with scores
        """
        max_results = max_results or self.max_results
        
        # Find matching entities
        entities = self.neo4j_store.semantic_search(
            query=query,
            entity_types=entity_types,
            max_results=max_results
        )
        
        # Expand with connected context
        results = []
        
        for entity in entities:
            entity_id = entity.get("id")
            
            # Get relationships
            relationships = self.neo4j_store.get_relationships(
                entity_id=entity_id,
                relationship_type=relationship_types[0] if relationship_types else None
            )
            
            # Build result with context
            context_text = self._build_context_text(entity, relationships)
            
            results.append({
                "id": entity_id,
                "content": context_text,
                "score": entity.get("score", 0.5),
                "metadata": {
                    "entity": entity,
                    "relationships": relationships,
                    "method": "graph"
                },
                "method": "graph"
            })
        
        logger.debug(f"Graph search returned {len(results)} results")
        return results
    
    def find_path(
        self,
        from_entity: str,
        to_entity: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find path between two entities.
        
        Args:
            from_entity: Source entity name or ID
            to_entity: Target entity name or ID
            
        Returns:
            Path information or None
        """
        # Search for entities
        from_results = self.neo4j_store.semantic_search(from_entity, max_results=1)
        to_results = self.neo4j_store.semantic_search(to_entity, max_results=1)
        
        if not from_results or not to_results:
            return None
        
        from_id = from_results[0]["id"]
        to_id = to_results[0]["id"]
        
        # Find shortest path
        path = self.neo4j_store.find_shortest_path(
            from_id=from_id,
            to_id=to_id,
            max_depth=self.max_depth
        )
        
        return path
    
    def explore_neighborhood(
        self,
        entity_id: str,
        depth: int = 1
    ) -> Dict[str, Any]:
        """
        Explore entity's neighborhood in graph.
        
        Args:
            entity_id: Entity identifier
            depth: Traversal depth
            
        Returns:
            Subgraph
        """
        return self.neo4j_store.traverse_graph(
            start_id=entity_id,
            max_depth=depth
        )
    
    def _build_context_text(
        self,
        entity: Dict[str, Any],
        relationships: List[Dict[str, Any]]
    ) -> str:
        """
        Build context text from entity and relationships.
        
        Args:
            entity: Entity data
            relationships: Related relationships
            
        Returns:
            Context text
        """
        parts = []
        
        # Entity description
        entity_name = entity.get("name", "")
        entity_type = entity.get("type", "Entity")
        parts.append(f"{entity_name} ({entity_type})")
        
        # Add relationships
        for rel in relationships[:5]:  # Limit to top 5
            source = rel.get("source", {})
            target = rel.get("target", {})
            rel_type = rel.get("type", "related to")
            
            source_name = source.get("name", "unknown")
            target_name = target.get("name", "unknown")
            
            # Format relationship
            rel_text = rel_type.replace("_", " ").lower()
            parts.append(f"{source_name} {rel_text} {target_name}")
        
        return ". ".join(parts)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get knowledge graph statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = self.neo4j_store.get_statistics()
        
        return {
            "graph_stats": stats,
            "entity_types": self.entity_extractor.get_entity_types(),
            "extractor": str(self.entity_extractor),
            "mapper": str(self.relationship_mapper)
        }
    
    def __repr__(self) -> str:
        """String representation."""
        return "KnowledgeGraph(neo4j + NER + relationship_extraction)"