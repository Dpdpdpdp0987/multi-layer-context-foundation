"""
Tests for Session Memory.
"""

import pytest
from mlcf.memory.session_memory import SessionMemory
from mlcf.core.context_models import ContextItem


@pytest.fixture
def session():
    """Create session memory instance."""
    return SessionMemory(
        max_size=10,
        consolidation_threshold=20,
        relevance_threshold=0.5,
        enable_consolidation=False  # Disable for tests
    )


def test_session_initialization(session):
    """Test session memory initializes correctly."""
    assert session is not None
    assert session.max_size == 10
    assert session.size == 0


def test_add_item(session):
    """Test adding items."""
    item = ContextItem(
        content="Test task",
        metadata={"type": "task"}
    )
    
    result = session.add(item)
    
    assert result is True
    assert session.size == 1


def test_eviction_when_full(session):
    """Test eviction when session is full."""
    # Fill session
    for i in range(12):  # More than max_size
        session.add(ContextItem(
            content=f"Item {i}",
            metadata={"importance": "normal"}
        ))
    
    # Should have evicted least important
    assert session.size == 10


def test_importance_based_eviction(session):
    """Test that importance affects eviction."""
    # Add low importance item
    low_item = ContextItem(
        content="Low priority",
        metadata={"importance": "low"}
    )
    session.add(low_item)
    
    # Add high importance items
    for i in range(10):
        session.add(ContextItem(
            content=f"High {i}",
            metadata={"importance": "high"}
        ))
    
    # Low importance should be evicted
    all_items = list(session._items.values())
    contents = [item.content for item in all_items]
    assert "Low priority" not in contents


def test_search_with_query(session):
    """Test searching with query."""
    # Add items
    session.add(ContextItem(content="Python programming guide"))
    session.add(ContextItem(content="Java development tips"))
    session.add(ContextItem(content="Python best practices"))
    
    # Search
    results = session.search(query="Python", max_results=5)
    
    assert len(results) > 0
    assert all("python" in r.content.lower() for r in results)


def test_search_with_filters(session):
    """Test searching with metadata filters."""
    # Add items with different types
    session.add(ContextItem(
        content="Task 1",
        metadata={"type": "task", "priority": "high"}
    ))
    session.add(ContextItem(
        content="Note 1",
        metadata={"type": "note", "priority": "low"}
    ))
    session.add(ContextItem(
        content="Task 2",
        metadata={"type": "task", "priority": "low"}
    ))
    
    # Search for tasks only
    results = session.search(
        filters={"type": "task"},
        max_results=10
    )
    
    assert len(results) == 2
    assert all(r.metadata["type"] == "task" for r in results)


def test_conversation_context(session):
    """Test getting conversation context."""
    # Add items for different conversations
    for i in range(3):
        session.add(ContextItem(
            content=f"Conv1 Message {i}",
            conversation_id="conv_1"
        ))
    
    for i in range(2):
        session.add(ContextItem(
            content=f"Conv2 Message {i}",
            conversation_id="conv_2"
        ))
    
    # Get conversation context
    conv1_items = session.get_conversation_context("conv_1")
    
    assert len(conv1_items) == 3
    assert all(item.conversation_id == "conv_1" for item in conv1_items)


def test_task_context(session):
    """Test getting task context."""
    # Add task-related items
    for i in range(3):
        session.add(ContextItem(
            content=f"Task step {i}",
            metadata={"task_id": "task_123"}
        ))
    
    # Get task context
    task_items = session.get_task_context("task_123")
    
    assert len(task_items) == 3
    assert all(item.metadata.get("task_id") == "task_123" for item in task_items)


def test_clear(session):
    """Test clearing session."""
    # Add items
    for i in range(5):
        session.add(ContextItem(content=f"Item {i}"))
    
    session.clear()
    
    assert session.size == 0


def test_clear_conversation(session):
    """Test clearing specific conversation."""
    # Add mixed conversations
    session.add(ContextItem(content="Conv1", conversation_id="conv_1"))
    session.add(ContextItem(content="Conv2", conversation_id="conv_2"))
    
    session.clear_conversation("conv_1")
    
    # Only conv_2 should remain
    all_items = list(session._items.values())
    assert len(all_items) == 1
    assert all_items[0].conversation_id == "conv_2"


def test_relevance_calculation(session):
    """Test relevance calculation."""
    item = ContextItem(content="Python programming tutorial")
    
    # Exact match
    relevance = session._calculate_relevance(item, "Python programming")
    assert relevance > 0.7
    
    # Partial match
    relevance = session._calculate_relevance(item, "Python")
    assert 0.3 < relevance < 0.8
    
    # No match
    relevance = session._calculate_relevance(item, "Java")
    assert relevance < 0.3


def test_metrics(session):
    """Test metrics reporting."""
    # Perform operations
    for i in range(12):  # Will trigger evictions
        session.add(ContextItem(content=f"Item {i}"))
    
    metrics = session.get_metrics()
    
    assert metrics["current_size"] == 10
    assert metrics["max_size"] == 10
    assert metrics["total_adds"] == 12
    assert metrics["total_evictions"] == 2