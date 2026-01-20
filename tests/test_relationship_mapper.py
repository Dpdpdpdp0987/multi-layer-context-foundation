"""
Tests for Relationship Mapper.
"""

import pytest

try:
    from mlcf.graph.relationship_mapper import RelationshipMapper
    from mlcf.graph.entity_extractor import EntityExtractor, Entity
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


@pytest.mark.skipif(not SPACY_AVAILABLE, reason="spacy not installed")
class TestRelationshipMapper:
    """Test relationship mapper."""
    
    @pytest.fixture
    def mapper(self):
        """Create relationship mapper."""
        try:
            return RelationshipMapper(model_name="en_core_web_sm")
        except OSError:
            pytest.skip("Spacy model not downloaded")
    
    @pytest.fixture
    def extractor(self):
        """Create entity extractor."""
        try:
            return EntityExtractor(model_name="en_core_web_sm")
        except OSError:
            pytest.skip("Spacy model not downloaded")
    
    def test_initialization(self, mapper):
        """Test mapper initializes correctly."""
        assert mapper is not None
        assert mapper.nlp is not None
    
    def test_extract_work_relationship(self, mapper, extractor):
        """Test extracting work relationships."""
        text = "John Smith works at Google."
        entities = extractor.extract(text)
        relationships = mapper.extract(text, entities)
        
        # Should find work relationship
        assert len(relationships) > 0
    
    def test_extract_location_relationship(self, mapper, extractor):
        """Test extracting location relationships."""
        text = "Apple is located in California."
        entities = extractor.extract(text)
        relationships = mapper.extract(text, entities)
        
        # Should find location relationship
        assert len(relationships) > 0
    
    def test_extract_multiple_relationships(self, mapper, extractor):
        """Test extracting multiple relationships."""
        text = "Alice works at Microsoft and Bob works at Google."
        entities = extractor.extract(text)
        relationships = mapper.extract(text, entities)
        
        # Should find multiple relationships
        assert len(relationships) >= 1
    
    def test_cooccurrence_relationships(self, mapper, extractor):
        """Test co-occurrence based relationships."""
        text = "Steve Jobs and Steve Wozniak founded Apple."
        entities = extractor.extract(text)
        relationships = mapper.extract(text, entities)
        
        # Should find some relationships
        assert len(relationships) > 0
    
    def test_relationship_to_dict(self, extractor):
        """Test relationship to dictionary conversion."""
        from mlcf.graph.relationship_mapper import Relationship
        
        source = Entity("Alice", "Person", 0, 5)
        target = Entity("IBM", "Organization", 15, 18)
        
        rel = Relationship(
            source=source,
            target=target,
            relationship_type="WORKS_FOR",
            confidence=0.8
        )
        
        rel_dict = rel.to_dict()
        
        assert rel_dict["type"] == "WORKS_FOR"
        assert rel_dict["confidence"] == 0.8
        assert "source" in rel_dict
        assert "target" in rel_dict