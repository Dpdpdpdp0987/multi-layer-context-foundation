"""
Tests for Qdrant Vector Store.
"""

import pytest
import os

try:
    from mlcf.storage.vector_store import QdrantVectorStore, VectorSearchResult
    from mlcf.embeddings.embedding_generator import EmbeddingGenerator
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant not installed")
class TestQdrantVectorStore:
    """Test Qdrant vector store."""
    
    @pytest.fixture
    def vector_store(self):
        """Create vector store for testing."""
        # Skip if Qdrant server not available
        try:
            store = QdrantVectorStore(
                collection_name="test_collection",
                host="localhost",
                port=6333,
                embedding_dim=384
            )
            yield store
            # Cleanup
            store.clear_collection()
        except Exception:
            pytest.skip("Qdrant server not available")
    
    def test_initialization(self, vector_store):
        """Test vector store initializes correctly."""
        assert vector_store is not None
        assert vector_store.collection_name == "test_collection"
        assert vector_store.embedding_dim == 384
    
    def test_add_document(self, vector_store):
        """Test adding a document."""
        doc_id = vector_store.add(
            doc_id="doc1",
            content="Test document about machine learning",
            metadata={"category": "AI"}
        )
        
        assert doc_id == "doc1"
    
    def test_add_batch(self, vector_store):
        """Test batch adding documents."""
        documents = [
            ("doc1", "Python programming", {"lang": "python"}),
            ("doc2", "Java development", {"lang": "java"}),
            ("doc3", "Python machine learning", {"lang": "python"})
        ]
        
        doc_ids = vector_store.add_batch(documents)
        
        assert len(doc_ids) == 3
        assert "doc1" in doc_ids
    
    def test_search(self, vector_store):
        """Test vector search."""
        # Add documents
        vector_store.add(
            "doc1",
            "Machine learning with Python",
            {"category": "ML"}
        )
        vector_store.add(
            "doc2",
            "Deep learning neural networks",
            {"category": "DL"}
        )
        
        # Search
        results = vector_store.search(
            query="Python machine learning",
            max_results=5
        )
        
        assert len(results) > 0
        assert isinstance(results[0], VectorSearchResult)
        assert results[0].score > 0
    
    def test_search_with_filters(self, vector_store):
        """Test search with metadata filters."""
        vector_store.add("doc1", "Python ML", {"lang": "python"})
        vector_store.add("doc2", "Java ML", {"lang": "java"})
        
        # Search with filter
        results = vector_store.search(
            query="ML programming",
            filters={"lang": "python"}
        )
        
        assert all(r.metadata.get("lang") == "python" for r in results)
    
    def test_delete(self, vector_store):
        """Test document deletion."""
        vector_store.add("doc1", "Test content")
        
        deleted = vector_store.delete("doc1")
        assert deleted is True
    
    def test_collection_info(self, vector_store):
        """Test getting collection info."""
        info = vector_store.get_collection_info()
        
        assert "name" in info
        assert info["name"] == "test_collection"