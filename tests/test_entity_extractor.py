"""
Tests for Entity Extractor.
"""

import pytest

try:
    from mlcf.graph.entity_extractor import EntityExtractor, Entity
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


@pytest.mark.skipif(not SPACY_AVAILABLE, reason="spacy not installed")
class TestEntityExtractor:
    """Test entity extractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create entity extractor."""
        try:
            return EntityExtractor(model_name="en_core_web_sm")
        except OSError:
            pytest.skip("Spacy model not downloaded")
    
    def test_initialization(self, extractor):
        """Test extractor initializes correctly."""
        assert extractor is not None
        assert extractor.nlp is not None
    
    def test_extract_persons(self, extractor):
        """Test extracting person entities."""
        text = "John Smith works at Google with Mary Johnson."
        entities = extractor.extract(text)
        
        # Should find persons
        person_entities = [e for e in entities if e.entity_type == "Person"]
        assert len(person_entities) >= 2
    
    def test_extract_organizations(self, extractor):
        """Test extracting organization entities."""
        text = "Apple Inc. and Microsoft are technology companies."
        entities = extractor.extract(text)
        
        # Should find organizations
        org_entities = [e for e in entities if e.entity_type == "Organization"]
        assert len(org_entities) >= 2
    
    def test_extract_locations(self, extractor):
        """Test extracting location entities."""
        text = "Paris is the capital of France."
        entities = extractor.extract(text)
        
        # Should find locations
        loc_entities = [e for e in entities if e.entity_type == "Location"]
        assert len(loc_entities) >= 2
    
    def test_extract_email(self, extractor):
        """Test extracting email addresses."""
        text = "Contact me at john.doe@example.com for details."
        entities = extractor.extract(text)
        
        # Should find email
        email_entities = [e for e in entities if e.entity_type == "Email"]
        assert len(email_entities) >= 1
        assert "@" in email_entities[0].text
    
    def test_extract_url(self, extractor):
        """Test extracting URLs."""
        text = "Visit https://www.example.com for more information."
        entities = extractor.extract(text)
        
        # Should find URL
        url_entities = [e for e in entities if e.entity_type == "URL"]
        assert len(url_entities) >= 1
    
    def test_batch_extraction(self, extractor):
        """Test batch entity extraction."""
        texts = [
            "Alice works at IBM.",
            "Bob lives in New York.",
            "Carol studies at MIT."
        ]
        
        results = extractor.extract_batch(texts)
        
        assert len(results) == 3
        assert all(len(entities) > 0 for entities in results)
    
    def test_extract_with_context(self, extractor):
        """Test extracting entities with context."""
        text = "Steve Jobs founded Apple in 1976 in California."
        results = extractor.extract_with_context(text, context_window=20)
        
        assert len(results) > 0
        assert all("context" in r for r in results)
    
    def test_entity_to_dict(self):
        """Test entity to dictionary conversion."""
        entity = Entity(
            text="John Doe",
            entity_type="Person",
            start=0,
            end=8,
            confidence=0.9
        )
        
        entity_dict = entity.to_dict()
        
        assert entity_dict["text"] == "John Doe"
        assert entity_dict["type"] == "Person"
        assert entity_dict["confidence"] == 0.9