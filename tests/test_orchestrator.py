"""
Tests for Context Orchestrator.
"""

import pytest
from datetime import datetime, timedelta
from mlcf.core.orchestrator import (
    ContextOrchestrator,
    ContextItem,
    ContextType,
    ContextPriority
)
from mlcf.core.config import Config


@pytest.fixture
def orchestrator():
    """Create orchestrator for testing."""
    config = Config(
        short_term_max_size=5,
        working_memory_max_size=10
    )
    return ContextOrchestrator(config=config)


def test_orchestrator_initialization(orchestrator):
    """Test orchestrator initializes correctly."""
    assert orchestrator is not None
    assert orchestrator.immediate_buffer is not None
    assert orchestrator.session_memory is not None
    assert orchestrator.persistent_memory is not None
    assert orchestrator.retrieval_engine is not None


def test_add_context_immediate(orchestrator):
    """Test adding context to immediate buffer."""
    item_id = orchestrator.add_context(
        content="Recent conversation message",
        context_type=ContextType.CONVERSATION,
        layer="immediate"
    )
    
    assert item_id is not None
    assert len(orchestrator.immediate_buffer) > 0


def test_add_context_session(orchestrator):
    """Test adding context to session memory."""
    orchestrator.start_new_session()
    
    item_id = orchestrator.add_context(
        content="Active task information",
        context_type=ContextType.TASK,
        layer="session"
    )
    
    assert item_id is not None
    assert len(orchestrator.session_memory) > 0


def test_add_context_auto_layer(orchestrator):
    """Test automatic layer determination."""
    # Fact should go to persistent
    fact_id = orchestrator.add_context(
        content="Python is a programming language",
        context_type=ContextType.FACT,
        layer="auto"
    )
    
    # Conversation should go to immediate
    conv_id = orchestrator.add_context(
        content="Hello, how are you?",
        context_type=ContextType.CONVERSATION,
        layer="auto"
    )
    
    assert fact_id is not None
    assert conv_id is not None


def test_retrieve_context(orchestrator):
    """Test context retrieval across layers."""
    orchestrator.start_new_session()
    
    # Add context to different layers
    orchestrator.add_context(
        "Python programming",
        context_type=ContextType.CONVERSATION,
        layer="immediate"
    )
    
    orchestrator.add_context(
        "Working on ML project",
        context_type=ContextType.TASK,
        layer="session"
    )
    
    # Retrieve
    results = orchestrator.retrieve_context(
        query="Python project",
        max_results=5
    )
    
    assert len(results) > 0
    assert all(hasattr(r, 'relevance_score') for r in results)


def test_get_active_context(orchestrator):
    """Test getting active context within budget."""
    orchestrator.start_new_session()
    
    # Add some context
    for i in range(5):
        orchestrator.add_context(
            f"Context item {i}",
            priority=ContextPriority.MEDIUM,
            layer="immediate"
        )
    
    items, tokens = orchestrator.get_active_context(max_tokens=500)
    
    assert len(items) > 0
    assert tokens <= 500


def test_context_budget_management(orchestrator):
    """Test context budget tracking."""
    orchestrator.start_new_session()
    
    # Add context until near budget
    for i in range(10):
        orchestrator.add_context(
            "This is a longer piece of context " * 20,
            layer="immediate"
        )
    
    stats = orchestrator.get_statistics()
    
    assert "context_budget_used" in stats
    assert "budget_usage_percent" in stats


def test_clear_operations(orchestrator):
    """Test clearing different memory layers."""
    orchestrator.start_new_session()
    
    # Add content
    orchestrator.add_context("Test", layer="immediate")
    orchestrator.add_context("Test", layer="session")
    
    # Clear immediate
    orchestrator.clear_immediate_buffer()
    assert len(orchestrator.immediate_buffer) == 0
    
    # Clear session
    orchestrator.clear_session()
    assert len(orchestrator.session_memory) == 0


def test_session_management(orchestrator):
    """Test session lifecycle."""
    session_id = orchestrator.start_new_session()
    
    assert session_id is not None
    assert orchestrator.current_session_id == session_id
    
    # Add some context
    orchestrator.add_context("Session context", layer="session")
    
    # Start new session
    new_session_id = orchestrator.start_new_session()
    assert new_session_id != session_id


def test_context_item_creation():
    """Test ContextItem creation and methods."""
    item = ContextItem(
        content="Test content",
        context_type=ContextType.FACT,
        priority=ContextPriority.HIGH
    )
    
    assert item.id is not None
    assert item.content == "Test content"
    assert item.context_type == ContextType.FACT
    assert item.priority == ContextPriority.HIGH
    assert not item.is_expired()
    
    # Test access tracking
    initial_count = item.access_count
    item.update_access()
    assert item.access_count == initial_count + 1


def test_context_item_expiration():
    """Test context item expiration."""
    # Create expired item
    item = ContextItem(
        content="Test",
        expires_at=datetime.utcnow() - timedelta(hours=1)
    )
    
    assert item.is_expired()
    
    # Create valid item
    item2 = ContextItem(
        content="Test",
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    
    assert not item2.is_expired()


def test_statistics(orchestrator):
    """Test statistics gathering."""
    orchestrator.start_new_session()
    
    # Add some context
    for i in range(3):
        orchestrator.add_context(f"Item {i}", layer="immediate")
    
    stats = orchestrator.get_statistics()
    
    assert "immediate_buffer_size" in stats
    assert "session_memory_size" in stats
    assert "current_session_id" in stats
    assert stats["immediate_buffer_size"] == 3