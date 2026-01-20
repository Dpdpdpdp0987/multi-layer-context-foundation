"""
Tests for Immediate Context Buffer.
"""

import pytest
from mlcf.memory.immediate_buffer import ImmediateContextBuffer
from mlcf.core.orchestrator import ContextItem, ContextType


@pytest.fixture
def buffer():
    """Create buffer for testing."""
    return ImmediateContextBuffer(max_size=5, max_tokens=500)


def test_buffer_initialization(buffer):
    """Test buffer initializes correctly."""
    assert buffer.max_size == 5
    assert buffer.max_tokens == 500
    assert len(buffer) == 0


def test_add_item(buffer):
    """Test adding items to buffer."""
    item = ContextItem(content="Test content")
    item_id = buffer.add(item)
    
    assert item_id == item.id
    assert len(buffer) == 1


def test_buffer_overflow(buffer):
    """Test buffer handles overflow correctly."""
    # Add more items than max_size
    for i in range(10):
        item = ContextItem(content=f"Item {i}")
        buffer.add(item)
    
    # Should only keep last 5
    assert len(buffer) == 5


def test_token_budget(buffer):
    """Test token budget management."""
    # Add items until token budget is exceeded
    for i in range(10):
        item = ContextItem(content="Long content " * 50)
        buffer.add(item)
    
    usage = buffer.get_token_usage()
    assert usage["current_tokens"] <= buffer.max_tokens


def test_search(buffer):
    """Test buffer search functionality."""
    # Add items
    buffer.add(ContextItem(content="Python programming"))
    buffer.add(ContextItem(content="Java development"))
    buffer.add(ContextItem(content="Python is great"))
    
    # Search
    results = buffer.search("Python")
    
    assert len(results) > 0
    assert all("python" in r.content.lower() for r in results)


def test_recency_bias(buffer):
    """Test that recent items get higher scores."""
    # Add items in order
    buffer.add(ContextItem(content="Python old"))
    buffer.add(ContextItem(content="Python new"))
    
    results = buffer.search("Python")
    
    # Most recent should have higher score
    assert len(results) == 2
    assert results[0].content == "Python new"


def test_get_recent(buffer):
    """Test getting recent items."""
    for i in range(5):
        buffer.add(ContextItem(content=f"Item {i}"))
    
    recent = buffer.get_recent(n=3)
    
    assert len(recent) == 3
    # Should be most recent
    assert recent[-1].content == "Item 4"


def test_clear(buffer):
    """Test clearing buffer."""
    buffer.add(ContextItem(content="Test"))
    assert len(buffer) > 0
    
    buffer.clear()
    assert len(buffer) == 0
    assert buffer.current_tokens == 0


def test_token_estimation(buffer):
    """Test token count estimation."""
    item = ContextItem(content="a" * 400)  # 400 characters
    buffer.add(item)
    
    usage = buffer.get_token_usage()
    # Should be ~100 tokens (4 chars per token)
    assert 80 <= usage["current_tokens"] <= 120