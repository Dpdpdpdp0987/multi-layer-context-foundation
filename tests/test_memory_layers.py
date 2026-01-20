"""
Tests for memory layers.
"""

import pytest
from mlcf.memory.memory_layers import ShortTermMemory, WorkingMemory


def test_short_term_memory():
    """Test ShortTermMemory functionality."""
    stm = ShortTermMemory(max_size=3)
    
    # Add items
    for i in range(5):
        stm.add(f"Item {i}")
    
    # Should only keep last 3
    all_items = stm.get_all()
    assert len(all_items) == 3
    assert all_items[-1]["content"] == "Item 4"


def test_short_term_search():
    """Test ShortTermMemory search."""
    stm = ShortTermMemory(max_size=10)
    
    stm.add("Python programming")
    stm.add("Java development")
    stm.add("Python is great")
    
    results = stm.search("Python")
    
    assert len(results) > 0
    assert any("Python" in r["content"] for r in results)


def test_working_memory():
    """Test WorkingMemory functionality."""
    wm = WorkingMemory(max_size=5)
    
    # Add items
    for i in range(7):
        wm.add(f"Task {i}")
    
    # Should evict LRU items
    all_items = wm.get_all()
    assert len(all_items) == 5


def test_working_memory_search():
    """Test WorkingMemory search with relevance."""
    wm = WorkingMemory(relevance_threshold=0.0)
    
    wm.add(
        "Machine learning project",
        metadata={"relevance": 0.9}
    )
    wm.add(
        "Web development task",
        metadata={"relevance": 0.5}
    )
    
    results = wm.search("machine learning")
    
    assert len(results) > 0
    # Higher relevance should rank higher
    if len(results) > 1:
        assert results[0]["relevance_score"] >= results[1]["relevance_score"]


def test_memory_clear():
    """Test memory clearing."""
    stm = ShortTermMemory()
    stm.add("Test")
    
    assert len(stm.get_all()) == 1
    
    stm.clear()
    
    assert len(stm.get_all()) == 0