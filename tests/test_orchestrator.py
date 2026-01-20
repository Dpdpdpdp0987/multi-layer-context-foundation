"""
Tests for Context Orchestrator.
"""

import pytest
import asyncio
from datetime import datetime

from mlcf.core.orchestrator import ContextOrchestrator, OrchestratorConfig
from mlcf.core.context_models import (
    ContextItem,
    ContextRequest,
    LayerType,
    RetrievalStrategy
)


@pytest.fixture
def orchestrator():
    """Create orchestrator instance."""
    config = OrchestratorConfig(
        immediate_buffer_size=5,
        session_max_size=20,
        enable_async=False
    )
    return ContextOrchestrator(config=config, enable_long_term=False)


@pytest.mark.asyncio
async def test_orchestrator_initialization(orchestrator):
    """Test orchestrator initializes correctly."""
    assert orchestrator is not None
    assert orchestrator.immediate_buffer is not None
    assert orchestrator.session_memory is not None
    assert orchestrator.long_term_store is None  # Disabled


@pytest.mark.asyncio
async def test_store_item(orchestrator):
    """Test storing an item."""
    item = await orchestrator.store(
        content="Test content",
        metadata={"type": "test"},
        conversation_id="conv_1"
    )
    
    assert item is not None
    assert item.content == "Test content"
    assert item.id is not None
    assert item.conversation_id == "conv_1"


@pytest.mark.asyncio
async def test_store_with_layer_hint(orchestrator):
    """Test storing with explicit layer hint."""
    item = await orchestrator.store(
        content="Important task",
        metadata={"type": "task"},
        layer_hint=LayerType.SESSION
    )
    
    assert item is not None
    # Verify it's in session memory
    assert orchestrator.session_memory.size > 0


@pytest.mark.asyncio
async def test_auto_layer_determination(orchestrator):
    """Test automatic layer determination."""
    # High importance should go to session
    item = await orchestrator.store(
        content="Critical decision",
        metadata={"importance": "critical", "type": "decision"}
    )
    
    layers = orchestrator._determine_storage_layers(item)
    assert LayerType.IMMEDIATE in layers
    assert LayerType.SESSION in layers


@pytest.mark.asyncio
async def test_retrieve_from_immediate(orchestrator):
    """Test retrieving from immediate buffer."""
    # Store some items
    await orchestrator.store("First message", conversation_id="conv_1")
    await orchestrator.store("Second message", conversation_id="conv_1")
    await orchestrator.store("Third message", conversation_id="conv_1")
    
    # Retrieve
    request = ContextRequest(
        query="message",
        max_results=5,
        conversation_id="conv_1",
        include_session=False,
        include_long_term=False
    )
    
    response = await orchestrator.retrieve(request)
    
    assert response is not None
    assert len(response.items) > 0
    assert "message" in response.items[0].content.lower()


@pytest.mark.asyncio
async def test_retrieve_hybrid(orchestrator):
    """Test hybrid retrieval from multiple layers."""
    # Store in immediate
    await orchestrator.store(
        "Recent conversation",
        conversation_id="conv_1"
    )
    
    # Store in session (high importance)
    await orchestrator.store(
        "Important decision made",
        metadata={"importance": "high", "type": "decision"},
        conversation_id="conv_1"
    )
    
    # Retrieve from all layers
    request = ContextRequest(
        query="decision",
        max_results=10,
        conversation_id="conv_1"
    )
    
    response = await orchestrator.retrieve(request)
    
    assert response is not None
    assert len(response.items) >= 1
    assert response.metadata["immediate_count"] >= 0
    assert response.metadata["session_count"] >= 0


@pytest.mark.asyncio
async def test_deduplication(orchestrator):
    """Test that duplicate items are handled correctly."""
    # Store same content twice
    await orchestrator.store("Duplicate content")
    await orchestrator.store("Duplicate content")
    
    request = ContextRequest(
        query="Duplicate",
        max_results=10
    )
    
    response = await orchestrator.retrieve(request)
    
    # Should have deduplicated
    contents = [item.content for item in response.items]
    assert len(contents) == len(set(contents))  # All unique


@pytest.mark.asyncio
async def test_relevance_scoring(orchestrator):
    """Test that items are scored by relevance."""
    # Store items with varying relevance
    await orchestrator.store("Python programming tutorial")
    await orchestrator.store("Java development guide")
    await orchestrator.store("Python is awesome")
    
    request = ContextRequest(
        query="Python programming",
        max_results=3
    )
    
    response = await orchestrator.retrieve(request)
    
    # First result should be most relevant
    assert len(response.items) > 0
    assert "python" in response.items[0].content.lower()


@pytest.mark.asyncio
async def test_metrics_tracking(orchestrator):
    """Test that metrics are tracked correctly."""
    # Perform operations
    await orchestrator.store("Test 1")
    await orchestrator.store("Test 2")
    
    request = ContextRequest(query="test", max_results=5)
    await orchestrator.retrieve(request)
    
    # Check metrics
    metrics = orchestrator.get_metrics()
    
    assert metrics["storage"]["total_stores"] == 2
    assert metrics["retrieval"]["total_retrievals"] == 1


@pytest.mark.asyncio
async def test_clear_immediate(orchestrator):
    """Test clearing immediate buffer."""
    await orchestrator.store("Test content")
    
    assert orchestrator.immediate_buffer.size > 0
    
    orchestrator.clear_immediate()
    
    assert orchestrator.immediate_buffer.size == 0


@pytest.mark.asyncio
async def test_clear_session_by_conversation(orchestrator):
    """Test clearing session by conversation."""
    await orchestrator.store(
        "Conv 1 message",
        metadata={"importance": "high"},
        conversation_id="conv_1"
    )
    await orchestrator.store(
        "Conv 2 message",
        metadata={"importance": "high"},
        conversation_id="conv_2"
    )
    
    initial_size = orchestrator.session_memory.size
    assert initial_size >= 2
    
    orchestrator.clear_session(conversation_id="conv_1")
    
    # Should have removed conv_1 items
    assert orchestrator.session_memory.size < initial_size