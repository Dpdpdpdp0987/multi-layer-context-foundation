"""
Tests for Immediate Context Buffer.
"""

import pytest
from datetime import datetime, timedelta
import time

from mlcf.memory.immediate_buffer import ImmediateContextBuffer
from mlcf.core.context_models import ContextItem


@pytest.fixture
def buffer():
    """Create buffer instance."""
    return ImmediateContextBuffer(max_size=5, ttl_seconds=10)


def test_buffer_initialization(buffer):
    """Test buffer initializes correctly."""
    assert buffer is not None
    assert buffer.max_size == 5
    assert buffer.ttl_seconds == 10
    assert buffer.size == 0
    assert buffer.is_empty


def test_add_item(buffer):
    """Test adding items to buffer."""
    item = ContextItem(content="Test content")
    
    result = buffer.add(item)
    
    assert result is True
    assert buffer.size == 1
    assert not buffer.is_empty


def test_fifo_eviction(buffer):
    """Test FIFO eviction when buffer is full."""
    # Add more than max_size
    for i in range(7):
        item = ContextItem(content=f"Item {i}")
        buffer.add(item)
    
    # Should only keep last 5
    assert buffer.size == 5
    assert buffer.is_full
    
    # Oldest items (0, 1) should be evicted
    items = buffer.get_all()
    contents = [item.content for item in items]
    assert "Item 0" not in contents
    assert "Item 1" not in contents
    assert "Item 6" in contents


def test_get_recent(buffer):
    """Test getting recent items."""
    # Add items
    for i in range(4):
        item = ContextItem(content=f"Item {i}")
        buffer.add(item)
    
    # Get recent (should be in reverse order)
    recent = buffer.get_recent(max_items=2)
    
    assert len(recent) == 2
    assert recent[0].content == "Item 3"  # Most recent
    assert recent[1].content == "Item 2"


def test_conversation_filtering(buffer):
    """Test filtering by conversation ID."""
    # Add items for different conversations
    for i in range(3):
        buffer.add(ContextItem(
            content=f"Conv1 Item {i}",
            conversation_id="conv_1"
        ))
    
    for i in range(2):
        buffer.add(ContextItem(
            content=f"Conv2 Item {i}",
            conversation_id="conv_2"
        ))
    
    # Get items for conv_1 only
    conv1_items = buffer.get_recent(conversation_id="conv_1")
    
    assert all(item.conversation_id == "conv_1" for item in conv1_items)
    assert len(conv1_items) == 3


def test_ttl_expiration(buffer):
    """Test TTL-based expiration."""
    # Create item with old timestamp
    old_item = ContextItem(content="Old item")
    old_item.timestamp = datetime.utcnow() - timedelta(seconds=15)
    
    buffer.add(old_item)
    buffer.add(ContextItem(content="New item"))
    
    # Get recent (should trigger expiration cleanup)
    recent = buffer.get_recent()
    
    # Old item should be expired
    contents = [item.content for item in recent]
    assert "Old item" not in contents
    assert "New item" in contents


def test_clear(buffer):
    """Test clearing buffer."""
    # Add items
    for i in range(3):
        buffer.add(ContextItem(content=f"Item {i}"))
    
    assert buffer.size == 3
    
    buffer.clear()
    
    assert buffer.size == 0
    assert buffer.is_empty


def test_clear_conversation(buffer):
    """Test clearing specific conversation."""
    # Add mixed conversations
    buffer.add(ContextItem(content="Conv1-A", conversation_id="conv_1"))
    buffer.add(ContextItem(content="Conv2-A", conversation_id="conv_2"))
    buffer.add(ContextItem(content="Conv1-B", conversation_id="conv_1"))
    
    buffer.clear(conversation_id="conv_1")
    
    all_items = buffer.get_all()
    assert len(all_items) == 1
    assert all_items[0].conversation_id == "conv_2"


def test_access_tracking(buffer):
    """Test that access is tracked."""
    item = ContextItem(content="Test")
    buffer.add(item)
    
    # Access the item
    recent = buffer.get_recent()
    
    assert recent[0].access_count > 0
    assert recent[0].last_accessed is not None


def test_metrics(buffer):
    """Test metrics reporting."""
    # Add and evict items
    for i in range(7):  # More than max_size
        buffer.add(ContextItem(content=f"Item {i}"))
    
    metrics = buffer.get_metrics()
    
    assert metrics["current_size"] == 5
    assert metrics["max_size"] == 5
    assert metrics["total_adds"] == 7
    assert metrics["total_evictions"] == 2
    assert metrics["oldest_item_age"] is not None
    assert metrics["newest_item_age"] is not None