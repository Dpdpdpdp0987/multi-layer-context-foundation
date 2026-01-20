"""
Graph database components for entity and relationship management.
"""

try:
    from mlcf.graph.neo4j_store import Neo4jStore
except ImportError:
    Neo4jStore = None

try:
    from mlcf.graph.entity_extractor import EntityExtractor, Entity
except ImportError:
    EntityExtractor = None
    Entity = None

try:
    from mlcf.graph.relationship_mapper import RelationshipMapper, Relationship
except ImportError:
    RelationshipMapper = None
    Relationship = None

try:
    from mlcf.graph.knowledge_graph import KnowledgeGraph
except ImportError:
    KnowledgeGraph = None

__all__ = [
    "Neo4jStore",
    "EntityExtractor",
    "Entity",
    "RelationshipMapper",
    "Relationship",
    "KnowledgeGraph",
]