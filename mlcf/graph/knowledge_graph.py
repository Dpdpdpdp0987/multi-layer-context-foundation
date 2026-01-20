"""
Knowledge Graph - Integrated entity extraction and graph building.
"""

from typing import Any, Dict, List, Optional, Set
from loguru import logger
import hashlib

from mlcf.graph.neo4j_store import Neo4jStore
from mlcf.graph.entity_extractor import EntityExtractor, Entity
from mlcf.graph.relationship_mapper import RelationshipMapper, Relationship


class KnowledgeGraph:
    """
    Knowledge graph builder.
    
    Combines entity extraction, relationship mapping, and graph storage
    to build a semantic knowledge graph from text.
    """
    
    def __init__(
        self,
        neo4j_store: Optional[Neo4jStore] = None,
        entity_extractor: Optional[EntityExtractor] = None,
        relationship_mapper: Optional[RelationshipMapper] = None,
        auto_commit: bool = True
    ):
        """
        Initialize knowledge graph.
        
        Args:
            neo4j_store: Neo4j store instance
            entity_extractor: Entity extractor instance
            relationship_mapper: Relationship mapper instance
            auto_commit: Automatically commit to graph
        """
        self.neo4j_store = neo4j_store or Neo4jStore()
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.relationship_mapper = relationship_mapper or RelationshipMapper()
        self.auto_commit = auto_commit
        
        logger.info("KnowledgeGraph initialized")
    
    def process_text(
        self,
        text: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process text and build knowledge graph.
        
        Args:
            text: Input text
            document_id: Document identifier
            metadata: Document metadata
            
        Returns:
            Processing results
        """
        # Extract entities
        entities = self.entity_extractor.extract(text)
        
        # Extract relationships
        relationships = self.relationship_mapper.extract(text, entities)
        
        # Commit to graph if enabled
        if self.auto_commit:
            entity_ids = self._commit_entities(entities, document_id)
            self._commit_relationships(relationships, entity_ids)
        
        return {
            "entities": [e.to_dict() for e in entities],
            "relationships": [r.to_dict() for r in relationships],
            "entity_count": len(entities),
            "relationship_count": len(relationships)
        }
    
    def _commit_entities(
        self,
        entities: List[Entity],
        document_id: Optional[str]
    ) -> Dict[str, str]:
        """
        Commit entities to graph.
        
        Args:
            entities: List of entities
            document_id: Document identifier
            
        Returns:
            Mapping of entity text to graph ID
        """
        entity_ids = {}
        
        for entity in entities:
            # Generate unique ID
            entity_id = self._generate_entity_id(entity)
            
            # Add to graph
            self.neo4j_store.add_entity(
                entity_id=entity_id,
                entity_type=entity.entity_type,
                name=entity.text,
                properties={
                    **entity.properties,
                    "confidence": entity.confidence,
                    "source_document": document_id
                }
            )
            
            entity_ids[entity.text] = entity_id
        
        return entity_ids
    
    def _commit_relationships(
        self,
        relationships: List[Relationship],
        entity_ids: Dict[str, str]
    ):
        """
        Commit relationships to graph.
        
        Args:
            relationships: List of relationships
            entity_ids: Entity ID mapping
        """
        for rel in relationships:
            source_id = entity_ids.get(rel.source.text)
            target_id = entity_ids.get(rel.target.text)
            
            if source_id and target_id:
                self.neo4j_store.add_relationship(
                    from_id=source_id,
                    to_id=target_id,
                    relationship_type=rel.relationship_type,
                    properties={
                        **rel.properties,
                        "confidence": rel.confidence
                    }
                )
    
    def _generate_entity_id(self, entity: Entity) -> str:
        """
        Generate unique entity ID.
        
        Args:
            entity: Entity
            
        Returns:
            Entity ID
        """
        # Use hash of normalized name
        normalized = entity.text.lower().strip()
        hash_obj = hashlib.md5(normalized.encode())
        return f"{entity.entity_type}_{hash_obj.hexdigest()[:12]}"
    
    def query(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query knowledge graph.
        
        Args:
            query: Search query
            max_results: Maximum results
            
        Returns:
            Matching entities
        """
        return self.neo4j_store.semantic_search(query, max_results=max_results)
    
    def get_entity_graph(
        self,
        entity_id: str,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get subgraph around an entity.
        
        Args:
            entity_id: Entity identifier
            max_depth: Traversal depth
            
        Returns:
            Subgraph
        """
        return self.neo4j_store.traverse_graph(entity_id, max_depth=max_depth)
    
    def __repr__(self) -> str:
        """String representation."""
        return "KnowledgeGraph(neo4j + entity_extraction + relationship_mapping)"