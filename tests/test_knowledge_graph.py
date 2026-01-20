"""
Tests for Knowledge Graph.
"""

import pytest

try:
    from mlcf.graph.knowledge_graph import KnowledgeGraph
    from mlcf.graph.neo4j_store import Neo4jStore
    from mlcf.graph.entity_extractor import EntityExtractor
    from mlcf.graph.relationship_mapper import RelationshipMapper
    GRAPH_AVAILABLE = True
except ImportError:
    GRAPH_AVAILABLE = False


@pytest.mark.skipif(not GRAPH_AVAILABLE, reason="Graph components not installed")
class TestKnowledgeGraph:
    """Test knowledge graph builder."""
    
    @pytest.fixture
    def kg(self):
        """Create knowledge graph."""
        try:
            neo4j_store = Neo4jStore(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="password"
            )
            
            extractor = EntityExtractor(model_name="en_core_web_sm")
            mapper = RelationshipMapper(model_name="en_core_web_sm")
            
            kg = KnowledgeGraph(
                neo4j_store=neo4j_store,
                entity_extractor=extractor,
                relationship_mapper=mapper,
                auto_commit=False  # Don't auto-commit in tests
            )
            
            yield kg
            
            # Cleanup
            neo4j_store.close()
        except Exception:
            pytest.skip("Neo4j server or spacy not available")
    
    def test_initialization(self, kg):
        """Test knowledge graph initializes correctly."""
        assert kg is not None
        assert kg.neo4j_store is not None
        assert kg.entity_extractor is not None
        assert kg.relationship_mapper is not None
    
    def test_process_text(self, kg):
        """Test processing text into knowledge graph."""
        text = "Alice works at Google in California."
        result = kg.process_text(text, document_id="test_doc_1")
        
        assert "entities" in result
        assert "relationships" in result
        assert result["entity_count"] > 0
    
    def test_entity_extraction(self, kg):
        """Test entity extraction from text."""
        text = "Steve Jobs founded Apple Inc. in 1976."
        result = kg.process_text(text)
        
        # Should extract entities
        assert len(result["entities"]) >= 2
    
    def test_relationship_extraction(self, kg):
        """Test relationship extraction from text."""
        text = "Bob works at Microsoft."
        result = kg.process_text(text)
        
        # Should extract relationships
        assert result["relationship_count"] >= 0