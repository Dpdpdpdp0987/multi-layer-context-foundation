"""
Tests for Adaptive Chunking.
"""

import pytest
from mlcf.retrieval.adaptive_chunking import AdaptiveChunker


@pytest.fixture
def chunker():
    """Create adaptive chunker for testing."""
    return AdaptiveChunker(
        chunk_size=200,
        base_overlap=20,
        adaptive_overlap=True
    )


def test_chunker_initialization(chunker):
    """Test chunker initializes correctly."""
    assert chunker.chunk_size == 200
    assert chunker.base_overlap == 20
    assert chunker.adaptive_overlap is True


def test_chunk_short_text(chunker):
    """Test chunking short text."""
    text = "This is a short text."
    chunks = chunker.chunk_text(text)
    
    assert len(chunks) == 1
    assert chunks[0].content == text


def test_chunk_long_text(chunker):
    """Test chunking long text."""
    text = "This is a sentence. " * 50  # ~1000 characters
    chunks = chunker.chunk_text(text)
    
    assert len(chunks) > 1
    assert all(len(chunk) > 0 for chunk in chunks)


def test_sentence_preservation(chunker):
    """Test that sentence boundaries are preserved."""
    text = (
        "First sentence here. Second sentence follows. "
        "Third sentence is next. Fourth sentence concludes. " * 10
    )
    
    chunks = chunker.chunk_text(text)
    
    # Check that chunks generally end at sentence boundaries
    # (within some tolerance for adaptation)
    for chunk in chunks:
        if chunk != chunks[-1]:  # Except last chunk
            # Should end with period or be at text end
            assert chunk.content.rstrip().endswith('.') or chunk.end_pos == len(text)


def test_chunk_overlap(chunker):
    """Test that chunks have proper overlap."""
    text = "Word " * 200  # Long text
    chunks = chunker.chunk_text(text)
    
    if len(chunks) > 1:
        # Check overlap exists
        for i in range(len(chunks) - 1):
            chunk1 = chunks[i]
            chunk2 = chunks[i + 1]
            
            # There should be overlap
            overlap_size = chunk1.end_pos - chunk2.start_pos
            assert overlap_size > 0
            assert overlap_size <= chunker.base_overlap * 2  # Allow adaptive increase


def test_chunk_metadata(chunker):
    """Test chunk metadata."""
    text = "Test text " * 50
    metadata = {"source": "test", "type": "example"}
    
    chunks = chunker.chunk_text(text, metadata=metadata)
    
    assert all("source" in chunk.metadata for chunk in chunks)
    assert all(chunk.metadata["source"] == "test" for chunk in chunks)
    assert all("chunk_index" in chunk.metadata for chunk in chunks)


def test_adaptive_overlap_calculation(chunker):
    """Test adaptive overlap based on content."""
    # Text with many short sentences
    text1 = "Short. " * 100
    chunks1 = chunker.chunk_text(text1)
    
    # Text with few long sentences
    text2 = ("This is a very long sentence with many words " * 10 + ". ") * 5
    chunks2 = chunker.chunk_text(text2)
    
    # Both should create chunks, but may have different overlap patterns
    assert len(chunks1) > 0
    assert len(chunks2) > 0


def test_merge_chunks(chunker):
    """Test chunk merging."""
    # Create small chunks
    text = "Short. " * 20
    chunks = chunker.chunk_text(text)
    
    # Merge
    merged = chunker.merge_chunks(chunks, max_merged_size=500)
    
    # Should have fewer chunks after merging
    assert len(merged) <= len(chunks)