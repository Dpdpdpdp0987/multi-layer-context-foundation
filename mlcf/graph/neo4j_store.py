"""
Neo4j Graph Store - Graph database integration for entity relationships.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
from loguru import logger
import json

try:
    from neo4j import GraphDatabase, basic_auth
    from neo4j.exceptions import ServiceUnavailable, AuthError
    NEO4J_AVAILABLE = True
except ImportError:
    logger.warning(
        "neo4j driver not installed. "
        "Install with: pip install neo4j"
    )
    NEO4J_AVAILABLE = False


class Neo4jStore:
    """
    Neo4j graph database integration.
    
    Manages entities, relationships, and graph-based queries
    for semantic knowledge representation.
    """
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
        database: str = "neo4j"
    ):
        """
        Initialize Neo4j store.
        
        Args:
            uri: Neo4j connection URI
            user: Username
            password: Password
            database: Database name
        """
        if not NEO4J_AVAILABLE:
            raise ImportError(
                "neo4j driver required. Install with: pip install neo4j"
            )
        
        self.uri = uri
        self.user = user
        self.database = database
        
        # Create driver
        try:
            self.driver = GraphDatabase.driver(
                uri,
                auth=basic_auth(user, password)
            )
            
            # Verify connection
            self.driver.verify_connectivity()
            
            # Initialize schema
            self._ensure_schema()
            
            logger.info(f"Neo4jStore initialized: {uri}, database={database}")
        
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def _ensure_schema(self):
        """
        Ensure graph schema exists.
        
        Creates constraints and indexes for optimal performance.
        """
        with self.driver.session(database=self.database) as session:
            # Constraints for uniqueness
            constraints = [
                "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
                "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT organization_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
                "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            ]
            
            # Indexes for performance
            indexes = [
                "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
                "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
                "CREATE INDEX document_created IF NOT EXISTS FOR (d:Document) ON (d.created_at)",
            ]
            
            for query in constraints + indexes:
                try:
                    session.run(query)
                except Exception as e:
                    # Ignore if already exists
                    if "already exists" not in str(e).lower():
                        logger.warning(f"Schema creation warning: {e}")
            
            logger.debug("Graph schema ensured")
    
    def add_entity(
        self,
        entity_id: str,
        entity_type: str,
        name: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add or update an entity in the graph.
        
        Args:
            entity_id: Unique entity identifier
            entity_type: Entity type (Person, Organization, Concept, etc.)
            name: Entity name
            properties: Additional properties
            
        Returns:
            Created/updated entity
        """
        properties = properties or {}
        
        with self.driver.session(database=self.database) as session:
            result = session.run(
                f"""
                MERGE (e:{entity_type} {{id: $id}})
                SET e.name = $name,
                    e.type = $type,
                    e.updated_at = datetime(),
                    e += $properties
                ON CREATE SET e.created_at = datetime()
                RETURN e
                """,
                id=entity_id,
                name=name,
                type=entity_type,
                properties=properties
            )
            
            record = result.single()
            if record:
                entity = dict(record["e"])
                logger.debug(f"Added entity: {entity_type}:{entity_id}")
                return entity
            
            return {}
    
    def add_relationship(
        self,
        from_id: str,
        to_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a relationship between two entities.
        
        Args:
            from_id: Source entity ID
            to_id: Target entity ID
            relationship_type: Type of relationship
            properties: Relationship properties
            
        Returns:
            True if created
        """
        properties = properties or {}
        
        with self.driver.session(database=self.database) as session:
            result = session.run(
                f"""
                MATCH (a:Entity {{id: $from_id}})
                MATCH (b:Entity {{id: $to_id}})
                MERGE (a)-[r:{relationship_type}]->(b)
                SET r += $properties,
                    r.updated_at = datetime()
                ON CREATE SET r.created_at = datetime()
                RETURN r
                """,
                from_id=from_id,
                to_id=to_id,
                properties=properties
            )
            
            record = result.single()
            if record:
                logger.debug(
                    f"Added relationship: {from_id}-[{relationship_type}]->{to_id}"
                )
                return True
            
            return False
    
    def get_entity(
        self,
        entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get entity by ID.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            Entity data or None
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(
                "MATCH (e:Entity {id: $id}) RETURN e",
                id=entity_id
            )
            
            record = result.single()
            if record:
                return dict(record["e"])
            
            return None
    
    def find_entities(
        self,
        entity_type: Optional[str] = None,
        name_pattern: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find entities matching criteria.
        
        Args:
            entity_type: Filter by entity type
            name_pattern: Name pattern (case-insensitive)
            properties: Property filters
            limit: Maximum results
            
        Returns:
            List of matching entities
        """
        # Build query
        where_clauses = []
        params = {"limit": limit}
        
        label = f":{entity_type}" if entity_type else ":Entity"
        
        if name_pattern:
            where_clauses.append("toLower(e.name) CONTAINS toLower($name_pattern)")
            params["name_pattern"] = name_pattern
        
        if properties:
            for key, value in properties.items():
                where_clauses.append(f"e.{key} = ${key}")
                params[key] = value
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        with self.driver.session(database=self.database) as session:
            result = session.run(
                f"""
                MATCH (e{label})
                {where_clause}
                RETURN e
                LIMIT $limit
                """,
                **params
            )
            
            return [dict(record["e"]) for record in result]
    
    def get_relationships(
        self,
        entity_id: str,
        direction: str = "both",
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get relationships for an entity.
        
        Args:
            entity_id: Entity identifier
            direction: Direction (outgoing, incoming, both)
            relationship_type: Filter by relationship type
            
        Returns:
            List of relationships with connected entities
        """
        # Build relationship pattern
        if direction == "outgoing":
            rel_pattern = "-[r]->"
        elif direction == "incoming":
            rel_pattern = "<-[r]-"
        else:
            rel_pattern = "-[r]-"
        
        type_filter = f":{relationship_type}" if relationship_type else ""
        
        with self.driver.session(database=self.database) as session:
            result = session.run(
                f"""
                MATCH (a:Entity {{id: $id}}){rel_pattern.replace('[r]', f'[r{type_filter}]')}(b:Entity)
                RETURN a, r, b, type(r) as rel_type
                """,
                id=entity_id
            )
            
            relationships = []
            for record in result:
                relationships.append({
                    "source": dict(record["a"]),
                    "target": dict(record["b"]),
                    "relationship": dict(record["r"]),
                    "type": record["rel_type"]
                })
            
            return relationships
    
    def traverse_graph(
        self,
        start_id: str,
        max_depth: int = 2,
        relationship_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Traverse graph from starting entity.
        
        Args:
            start_id: Starting entity ID
            max_depth: Maximum traversal depth
            relationship_types: Filter by relationship types
            
        Returns:
            Subgraph containing nodes and relationships
        """
        rel_filter = "|".join(relationship_types) if relationship_types else ""
        rel_pattern = f"[r:{rel_filter}]" if rel_filter else "[r]"
        
        with self.driver.session(database=self.database) as session:
            result = session.run(
                f"""
                MATCH path = (start:Entity {{id: $start_id}})-{rel_pattern}*1..{max_depth}-(end:Entity)
                WITH nodes(path) as nodes, relationships(path) as rels
                UNWIND nodes as node
                UNWIND rels as rel
                RETURN COLLECT(DISTINCT node) as nodes, COLLECT(DISTINCT rel) as relationships
                """,
                start_id=start_id
            )
            
            record = result.single()
            if record:
                return {
                    "nodes": [dict(n) for n in record["nodes"]],
                    "relationships": [dict(r) for r in record["relationships"]]
                }
            
            return {"nodes": [], "relationships": []}
    
    def semantic_search(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search entities by semantic similarity.
        
        Uses full-text search on entity names and properties.
        
        Args:
            query: Search query
            entity_types: Filter by entity types
            max_results: Maximum results
            
        Returns:
            Matching entities
        """
        # Build type filter
        type_filter = ":".join(["Entity"] + (entity_types or []))
        
        with self.driver.session(database=self.database) as session:
            # Simple pattern matching (can be enhanced with full-text index)
            result = session.run(
                f"""
                MATCH (e:{type_filter})
                WHERE toLower(e.name) CONTAINS toLower($query)
                   OR any(prop IN keys(e) WHERE toLower(toString(e[prop])) CONTAINS toLower($query))
                RETURN e, 
                       CASE 
                         WHEN toLower(e.name) = toLower($query) THEN 1.0
                         WHEN toLower(e.name) STARTS WITH toLower($query) THEN 0.8
                         ELSE 0.5
                       END as score
                ORDER BY score DESC
                LIMIT $limit
                """,
                query=query,
                limit=max_results
            )
            
            return [
                {**dict(record["e"]), "score": record["score"]}
                for record in result
            ]
    
    def find_shortest_path(
        self,
        from_id: str,
        to_id: str,
        max_depth: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Find shortest path between two entities.
        
        Args:
            from_id: Source entity ID
            to_id: Target entity ID
            max_depth: Maximum path length
            
        Returns:
            Path as list of nodes and relationships
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(
                f"""
                MATCH path = shortestPath(
                  (a:Entity {{id: $from_id}})-[*..{max_depth}]-(b:Entity {{id: $to_id}})
                )
                RETURN nodes(path) as nodes, relationships(path) as rels
                """,
                from_id=from_id,
                to_id=to_id
            )
            
            record = result.single()
            if record:
                return {
                    "nodes": [dict(n) for n in record["nodes"]],
                    "relationships": [dict(r) for r in record["rels"]]
                }
            
            return None
    
    def delete_entity(
        self,
        entity_id: str,
        delete_relationships: bool = True
    ) -> bool:
        """
        Delete an entity.
        
        Args:
            entity_id: Entity to delete
            delete_relationships: Also delete connected relationships
            
        Returns:
            True if deleted
        """
        with self.driver.session(database=self.database) as session:
            if delete_relationships:
                query = "MATCH (e:Entity {id: $id}) DETACH DELETE e"
            else:
                query = "MATCH (e:Entity {id: $id}) DELETE e"
            
            result = session.run(query, id=entity_id)
            
            # Check if entity was deleted
            summary = result.consume()
            deleted = summary.counters.nodes_deleted > 0
            
            if deleted:
                logger.debug(f"Deleted entity: {entity_id}")
            
            return deleted
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get graph statistics.
        
        Returns:
            Statistics dictionary
        """
        with self.driver.session(database=self.database) as session:
            # Count nodes by type
            node_counts = session.run(
                "MATCH (n) RETURN labels(n)[0] as label, count(*) as count"
            )
            
            # Count relationships by type
            rel_counts = session.run(
                "MATCH ()-[r]->() RETURN type(r) as type, count(*) as count"
            )
            
            return {
                "nodes_by_type": {record["label"]: record["count"] for record in node_counts},
                "relationships_by_type": {record["type"]: record["count"] for record in rel_counts}
            }
    
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.debug("Neo4j connection closed")
    
    def __del__(self):
        """Destructor to ensure connection is closed."""
        self.close()
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Neo4jStore(uri={self.uri}, database={self.database})"