"""
Tests for Embedding Generator.
"""

import pytest

try:
    from mlcf.embeddings.embedding_generator import EmbeddingGenerator
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


@pytest.mark.skipif(not EMBEDDINGS_AVAILABLE, reason="sentence-transformers not installed")
class TestEmbeddingGenerator:
    """Test embedding generator."""
    
    @pytest.fixture
    def generator(self):
        """Create embedding generator."""
        return EmbeddingGenerator(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    
    def test_initialization(self, generator):
        """Test generator initializes correctly."""
        assert generator is not None
        assert generator.embedding_dim == 384
    
    def test_generate_single(self, generator):
        """Test generating single embedding."""
        embedding = generator.generate("Test text for embedding")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
    
    def test_generate_batch(self, generator):
        """Test batch embedding generation."""
        texts = [
            "First text",
            "Second text",
            "Third text"
        ]
        
        embeddings = generator.generate_batch(texts)
        
        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)
    
    def test_empty_text(self, generator):
        """Test handling empty text."""
        embedding = generator.generate("")
        
        # Should return zero vector
        assert len(embedding) == 384
        assert all(x == 0.0 for x in embedding)
    
    def test_similarity(self, generator):
        """Test similarity calculation."""
        text1 = "Machine learning with Python"
        text2 = "Python for machine learning"
        text3 = "Cooking recipes"
        
        # Similar texts should have high similarity
        sim_high = generator.similarity(text1, text2, metric="cosine")
        sim_low = generator.similarity(text1, text3, metric="cosine")
        
        assert sim_high > 0.7  # High similarity
        assert sim_low < sim_high  # Lower similarity
    
    def test_model_info(self, generator):
        """Test getting model info."""
        info = generator.get_model_info()
        
        assert "model_name" in info
        assert "embedding_dim" in info
        assert info["embedding_dim"] == 384