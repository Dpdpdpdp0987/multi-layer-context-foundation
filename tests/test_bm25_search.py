"""
Tests for BM25 Search.
"""

import pytest
from mlcf.retrieval.bm25_search import BM25Search, tokenize


@pytest.fixture
def bm25():
    """Create BM25 search for testing."""
    return BM25Search(k1=1.5, b=0.75)


def test_tokenization():
    """Test text tokenization."""
    text = "Hello, world! This is a test."
    tokens = tokenize(text)
    
    assert "hello" in tokens
    assert "world" in tokens
    assert "test" in tokens
    assert "," not in tokens  # Punctuation removed


def test_add_document(bm25):
    """Test adding documents."""
    bm25.add_document(
        doc_id="doc1",
        content="Python programming language",
        metadata={"type": "tech"}
    )
    
    assert len(bm25) == 1
    assert "doc1" in bm25.documents


def test_add_multiple_documents(bm25):
    """Test batch document addition."""
    docs = [
        ("doc1", "Python programming", {"lang": "python"}),
        ("doc2", "Java development", {"lang": "java"}),
        ("doc3", "Python data science", {"lang": "python"}),
    ]
    
    bm25.add_documents(docs)
    
    assert len(bm25) == 3


def test_search_basic(bm25):
    """Test basic search functionality."""
    # Add documents
    bm25.add_document("doc1", "Python is a programming language")
    bm25.add_document("doc2", "Java is also a programming language")
    bm25.add_document("doc3", "Python is great for data science")
    
    # Search
    results = bm25.search("Python programming")
    
    assert len(results) > 0
    assert results[0]["score"] > 0
    # Should rank doc with both terms higher
    assert "python" in results[0]["content"].lower()


def test_search_ranking(bm25):
    """Test BM25 ranking quality."""
    # Add documents with different relevance
    bm25.add_document("doc1", "machine learning algorithms")
    bm25.add_document("doc2", "machine learning and deep learning")
    bm25.add_document("doc3", "learning to code")
    
    results = bm25.search("machine learning", max_results=3)
    
    assert len(results) >= 2
    # Document with both terms should rank highest
    assert "machine" in results[0]["content"].lower()
    assert "learning" in results[0]["content"].lower()


def test_search_with_filters(bm25):
    """Test search with metadata filters."""
    bm25.add_document("doc1", "Python code", {"lang": "python"})
    bm25.add_document("doc2", "Java code", {"lang": "java"})
    bm25.add_document("doc3", "Python script", {"lang": "python"})
    
    # Search with filter
    results = bm25.search("code", filters={"lang": "python"})
    
    assert len(results) > 0
    assert all(r["metadata"]["lang"] == "python" for r in results)


def test_idf_calculation(bm25):
    """Test IDF score calculation."""
    # Add documents
    bm25.add_document("doc1", "common word")
    bm25.add_document("doc2", "common term")
    bm25.add_document("doc3", "rare word")
    
    # "common" appears in 2/3 docs, "rare" in 1/3
    # "rare" should have higher IDF
    common_idf = bm25._get_idf("common")
    rare_idf = bm25._get_idf("rare")
    
    assert rare_idf > common_idf


def test_document_length_normalization(bm25):
    """Test document length normalization."""
    # Add short and long documents
    bm25.add_document("short", "Python")
    bm25.add_document("long", "Python " * 100)  # Long document
    
    results = bm25.search("Python")
    
    # Both should be returned
    assert len(results) == 2
    # Shorter document should not be penalized too much
    scores = {r["id"]: r["score"] for r in results}
    assert scores["short"] > 0


def test_remove_document(bm25):
    """Test document removal."""
    bm25.add_document("doc1", "Test content")
    assert len(bm25) == 1
    
    removed = bm25.remove_document("doc1")
    assert removed is True
    assert len(bm25) == 0
    
    # Try removing non-existent
    removed = bm25.remove_document("doc2")
    assert removed is False


def test_statistics(bm25):
    """Test statistics gathering."""
    bm25.add_document("doc1", "Test document one")
    bm25.add_document("doc2", "Another test document")
    
    stats = bm25.get_statistics()
    
    assert stats["total_documents"] == 2
    assert stats["avg_doc_length"] > 0
    assert stats["vocabulary_size"] > 0
    assert "parameters" in stats