"""
Tests for ContextManager.
"""

import pytest
from mlcf import ContextManager


def test_context_manager_initialization(context_manager):
    """Test ContextManager initializes correctly."""
    assert context_manager is not None
    assert context_manager.short_term is not None
    assert context_manager.working is not None
    assert context_manager.long_term is not None


def test_store_and_retrieve(context_manager, sample_documents):
    """Test basic store and retrieve operations."""
    # Store documents
    for doc in sample_documents:
        doc_id = context_manager.store(
            content=doc["content"],
            metadata=doc["metadata"]
        )
        assert doc_id is not None
    
    # Retrieve
    results = context_manager.retrieve(
        query="programming",
        max_results=5
    )
    
    assert len(results) > 0


def test_layer_targeting(context_manager):
    """Test explicit layer targeting."""
    # Store in specific layers
    short_id = context_manager.store(
        "Recent conversation",
        layer="short"
    )
    
    working_id = context_manager.store(
        "Active task",
        layer="working"
    )
    
    long_id = context_manager.store(
        "Permanent fact",
        layer="long"
    )
    
    assert all([short_id, working_id, long_id])


def test_clear_operations(context_manager):
    """Test memory clearing."""
    # Add some data
    context_manager.store("Test data", layer="short")
    
    # Clear
    context_manager.clear_short_term()
    
    # Verify empty
    assert len(context_manager.short_term.get_all()) == 0


def test_auto_layer_determination(context_manager):
    """Test automatic layer determination."""
    # Permanent content should go to long-term
    doc_id = context_manager.store(
        "Important fact",
        metadata={"importance": "permanent", "type": "fact"}
    )
    
    assert doc_id is not None