"""
Tests for Semantic Search.
"""

import pytest

try:
    from mlcf.retrieval.semantic_search import SemanticSearch, SemanticSearchConfig
    from mlcf.storage.vector_store import QdrantVectorStore
    from mlcf.embeddings.embedding_generator import EmbeddingGenerator
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False


@pytest.mark.skipif(not SEMANTIC_AVAILABLE, reason="Dependencies not installed")
class TestSemanticSearch:
    """Test semantic search."""
    
    @pytest.fixture
    def semantic_search(self):
        """Create semantic search instance."""
        try:
            vector_store = QdrantVectorStore(
                collection_name="test_semantic",
                host="localhost",
                port=6333
            )
            
            search = SemanticSearch(vector_store=vector_store)
            
            # Add test data
            vector_store.add(
                "doc1",
                "Python is great for machine learning",
                {"topic": "ML"}
            )
            vector_store.add(
                "doc2",
                "Java is used for enterprise applications",
                {"topic": "Enterprise"}
            )
            
            yield search
            
            # Cleanup
            vector_store.clear_collection()
        except Exception:
            pytest.skip("Qdrant server not available")
    
    def test_search(self, semantic_search):
        """Test semantic search."""
        results = semantic_search.search(
            query="machine learning programming",
            max_results=5
        )
        
        assert len(results) > 0
        assert "id" in results[0]
        assert "content" in results[0]
        assert "score" in results[0]
    
    def test_search_with_filters(self, semantic_search):
        """Test search with metadata filters."""
        results = semantic_search.search(
            query="programming",
            filters={"topic": "ML"}
        )
        
        assert all(r["metadata"].get("topic") == "ML" for r in results)