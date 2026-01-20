"""
Tests for Session Memory.
"""

import pytest
from datetime import timedelta
from mlcf.memory.session_memory import SessionMemory
from mlcf.core.orchestrator import ContextItem, ContextType, ContextPriority


@pytest.fixture
def session_memory():
    """Create session memory for testing."""
    return SessionMemory(
        max_size=10,
        relevance_threshold=0.5,
        session_timeout=timedelta(hours=1)
    )


def test_session_memory_initialization(session_memory):
    """Test session memory initializes correctly."""
    assert session_memory.max_size == 10
    assert session_memory.relevance_threshold == 0.5


def test_start_session(session_memory):
    """Test starting a new session."""
    session_id = session_memory.start_session("test_session")
    
    assert session_id == "test_session"
    assert session_memory._active_session == "test_session"


def test_add_item(session_memory):
    """Test adding items to session."""
    session_memory.start_session("test")
    
    item = ContextItem(content="Test content")
    item_id = session_memory.add(item)
    
    assert item_id == item.id
    assert len(session_memory) == 1


def test_lru_eviction(session_memory):
    """Test LRU eviction when over capacity."""
    session_memory.start_session("test")
    
    # Add more items than max_size
    items = []
    for i in range(15):
        item = ContextItem(content=f"Item {i}")
        session_memory.add(item)
        items.append(item)
    
    # Should only keep last 10
    assert len(session_memory) == 10
    
    # First items should be evicted
    all_items = session_memory.get_all()
    assert items[0] not in all_items
    assert items[-1] in all_items


def test_search(session_memory):
    """Test searching session memory."""
    session_memory.start_session("test")
    
    # Add items
    session_memory.add(ContextItem(content="Machine learning", relevance_score=0.9))
    session_memory.add(ContextItem(content="Deep learning", relevance_score=0.8))
    session_memory.add(ContextItem(content="Data science", relevance_score=0.7))
    
    # Search
    results = session_memory.search("learning", max_results=5)
    
    assert len(results) > 0
    # Results should be sorted by relevance
    assert results[0].relevance_score >= results[-1].relevance_score


def test_relevance_threshold(session_memory):
    """Test relevance threshold filtering."""
    session_memory.start_session("test")
    
    # Add item with low relevance
    session_memory.add(
        ContextItem(content="Irrelevant content", relevance_score=0.2)
    )
    
    # Search - should not return low relevance items
    results = session_memory.search("content", max_results=5)
    
    # May or may not return based on query match and threshold
    # Just verify threshold is applied
    assert all(r.relevance_score >= session_memory.relevance_threshold for r in results)


def test_filters(session_memory):
    """Test metadata filtering."""
    session_memory.start_session("test")
    
    # Add items with different metadata
    session_memory.add(
        ContextItem(
            content="Python code",
            metadata={"language": "python", "type": "code"}
        )
    )
    session_memory.add(
        ContextItem(
            content="Java code",
            metadata={"language": "java", "type": "code"}
        )
    )
    
    # Search with filter
    results = session_memory.search(
        "code",
        filters={"language": "python"}
    )
    
    assert len(results) > 0
    assert all(r.metadata.get("language") == "python" for r in results)


def test_get_active_items(session_memory):
    """Test getting most active items."""
    session_memory.start_session("test")
    
    # Add items with different access patterns
    item1 = ContextItem(content="Frequently accessed", relevance_score=0.9)
    item1.access_count = 10
    session_memory.add(item1)
    
    item2 = ContextItem(content="Rarely accessed", relevance_score=0.5)
    item2.access_count = 1
    session_memory.add(item2)
    
    # Get active items
    active = session_memory.get_active_items(top_k=5)
    
    assert len(active) > 0
    # Most active should be first
    assert active[0].access_count >= active[-1].access_count


def test_multiple_sessions(session_memory):
    """Test managing multiple sessions."""
    # Start first session
    session_memory.start_session("session1")
    session_memory.add(ContextItem(content="Session 1 content"))
    
    # Start second session
    session_memory.start_session("session2")
    session_memory.add(ContextItem(content="Session 2 content"))
    
    # Get items from different sessions
    session1_items = session_memory.get_all("session1")
    session2_items = session_memory.get_all("session2")
    
    assert len(session1_items) == 1
    assert len(session2_items) == 1
    assert session1_items[0].content != session2_items[0].content


def test_clear_session(session_memory):
    """Test clearing a session."""
    session_memory.start_session("test")
    session_memory.add(ContextItem(content="Test"))
    
    assert len(session_memory) > 0
    
    session_memory.clear("test")
    assert len(session_memory.get_all("test")) == 0


def test_session_stats(session_memory):
    """Test session statistics."""
    session_memory.start_session("test")
    
    # Add items
    for i in range(5):
        session_memory.add(ContextItem(content=f"Item {i}", relevance_score=0.8))
    
    stats = session_memory.get_session_stats("test")
    
    assert stats["session_id"] == "test"
    assert stats["item_count"] == 5
    assert "average_relevance" in stats
    assert "usage_percent" in stats