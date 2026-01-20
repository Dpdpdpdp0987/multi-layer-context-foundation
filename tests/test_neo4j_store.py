"""
Tests for Neo4j Graph Store.
"""

import pytest

try:
    from mlcf.graph.neo4j_store import Neo4jStore
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False


@pytest.mark.skipif(not NEO4J_AVAILABLE, reason="Neo4j not installed")
class TestNeo4jStore:
    """Test Neo4j graph store."""
    
    @pytest.fixture
    def graph_store(self):
        """Create graph store for testing."""
        try:
            store = Neo4jStore(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="password"
            )
            yield store
            # Cleanup - delete test data
            with store.driver.session(database=store.database) as session:
                session.run("MATCH (n) WHERE n.test = true DETACH DELETE n")
            store.close()
        except Exception:
            pytest.skip("Neo4j server not available")
    
    def test_initialization(self, graph_store):
        """Test graph store initializes correctly."""
        assert graph_store is not None
        assert graph_store.driver is not None
    
    def test_add_entity(self, graph_store):
        """Test adding an entity."""
        entity = graph_store.add_entity(
            entity_id="person_test_1",
            entity_type="Person",
            name="John Doe",
            properties={"test": True, "role": "developer"}
        )
        
        assert entity is not None
        assert entity["name"] == "John Doe"
        assert entity["type"] == "Person"
    
    def test_add_relationship(self, graph_store):
        """Test adding a relationship."""
        # Add two entities
        graph_store.add_entity(
            "person_test_2",
            "Person",
            "Alice",
            {"test": True}
        )
        graph_store.add_entity(
            "org_test_1",
            "Organization",
            "ACME Corp",
            {"test": True}
        )
        
        # Add relationship
        result = graph_store.add_relationship(
            from_id="person_test_2",
            to_id="org_test_1",
            relationship_type="WORKS_FOR",
            properties={"since": 2020}
        )
        
        assert result is True
    
    def test_get_entity(self, graph_store):
        """Test retrieving an entity."""
        # Add entity
        graph_store.add_entity(
            "person_test_3",
            "Person",
            "Bob",
            {"test": True}
        )
        
        # Get entity
        entity = graph_store.get_entity("person_test_3")
        
        assert entity is not None
        assert entity["name"] == "Bob"
    
    def test_find_entities(self, graph_store):
        """Test finding entities."""
        # Add test entities
        graph_store.add_entity(
            "person_test_4",
            "Person",
            "Charlie",
            {"test": True}
        )
        
        # Find by name pattern
        results = graph_store.find_entities(
            entity_type="Person",
            name_pattern="Charlie"
        )
        
        assert len(results) > 0
        assert any(e["name"] == "Charlie" for e in results)
    
    def test_get_relationships(self, graph_store):
        """Test getting entity relationships."""
        # Add entities and relationship
        graph_store.add_entity("person_test_5", "Person", "Diana", {"test": True})
        graph_store.add_entity("person_test_6", "Person", "Eve", {"test": True})
        graph_store.add_relationship(
            "person_test_5",
            "person_test_6",
            "KNOWS"
        )
        
        # Get relationships
        rels = graph_store.get_relationships("person_test_5")
        
        assert len(rels) > 0
        assert any(r["type"] == "KNOWS" for r in rels)
    
    def test_semantic_search(self, graph_store):
        """Test semantic search."""
        # Add test entity
        graph_store.add_entity(
            "person_test_7",
            "Person",
            "Frank Smith",
            {"test": True, "occupation": "engineer"}
        )
        
        # Search
        results = graph_store.semantic_search("Frank")
        
        assert len(results) > 0
    
    def test_delete_entity(self, graph_store):
        """Test deleting an entity."""
        # Add entity
        graph_store.add_entity(
            "person_test_8",
            "Person",
            "George",
            {"test": True}
        )
        
        # Delete entity
        deleted = graph_store.delete_entity("person_test_8")
        
        assert deleted is True
        
        # Verify deleted
        entity = graph_store.get_entity("person_test_8")
        assert entity is None
    
    def test_statistics(self, graph_store):
        """Test getting graph statistics."""
        stats = graph_store.get_statistics()
        
        assert "nodes_by_type" in stats
        assert "relationships_by_type" in stats