#!/usr/bin/env python
"""
Basic usage examples for Multi-Layer Context Foundation.
"""

import asyncio
from mlcf import (
    ContextOrchestrator,
    OrchestratorConfig,
    ContextRequest,
    LayerType,
    RetrievalStrategy
)


async def basic_example():
    """Basic storage and retrieval example."""
    print("\n=== Basic Usage Example ===")
    
    # Initialize orchestrator
    config = OrchestratorConfig(
        immediate_buffer_size=10,
        session_max_size=50
    )
    orchestrator = ContextOrchestrator(config=config, enable_long_term=False)
    
    # Store some context
    print("\nStoring context...")
    
    await orchestrator.store(
        content="User prefers Python for backend development",
        metadata={"type": "preference", "category": "programming"},
        conversation_id="conv_1"
    )
    
    await orchestrator.store(
        content="Currently working on a machine learning project using TensorFlow",
        metadata={"type": "task", "importance": "high"},
        conversation_id="conv_1"
    )
    
    await orchestrator.store(
        content="Deadline for ML project is next Friday",
        metadata={"type": "task", "importance": "critical"},
        conversation_id="conv_1"
    )
    
    print("✓ Stored 3 context items")
    
    # Retrieve relevant context
    print("\nRetrieving context...")
    
    request = ContextRequest(
        query="What am I working on?",
        max_results=5,
        conversation_id="conv_1"
    )
    
    response = await orchestrator.retrieve(request)
    
    print(f"\nFound {len(response.items)} relevant items:")
    for i, item in enumerate(response.items, 1):
        print(f"\n{i}. [{item.metadata.get('type', 'unknown')}]")
        print(f"   Content: {item.content}")
        print(f"   Relevance: {item.relevance_score:.3f}")
        print(f"   Importance: {item.importance_score:.3f}")
    
    # Show metrics
    print("\n=== Metrics ===")
    metrics = orchestrator.get_metrics()
    print(f"Total stores: {metrics['storage']['total_stores']}")
    print(f"Total retrievals: {metrics['retrieval']['total_retrievals']}")
    print(f"Avg retrieval time: {metrics['retrieval']['avg_retrieval_time']:.3f}s")


async def conversation_tracking_example():
    """Example of tracking multiple conversations."""
    print("\n\n=== Conversation Tracking Example ===")
    
    orchestrator = ContextOrchestrator(enable_long_term=False)
    
    # Conversation 1: Programming help
    print("\nConversation 1: Programming Help")
    await orchestrator.store(
        "How do I handle exceptions in Python?",
        conversation_id="programming_conv"
    )
    await orchestrator.store(
        "Use try-except blocks for exception handling",
        conversation_id="programming_conv"
    )
    
    # Conversation 2: Project planning
    print("Conversation 2: Project Planning")
    await orchestrator.store(
        "What are the milestones for Q1?",
        conversation_id="planning_conv"
    )
    await orchestrator.store(
        "Q1 milestones: Launch MVP, Onboard 100 users, Achieve 95% uptime",
        metadata={"type": "planning", "importance": "high"},
        conversation_id="planning_conv"
    )
    
    # Retrieve from specific conversation
    print("\nRetrieving from planning conversation only...")
    
    request = ContextRequest(
        query="milestones",
        conversation_id="planning_conv",
        max_results=10
    )
    
    response = await orchestrator.retrieve(request)
    
    print(f"\nFound {len(response.items)} items in planning conversation:")
    for item in response.items:
        print(f"  - {item.content[:60]}...")


async def importance_based_example():
    """Example showing importance-based retention."""
    print("\n\n=== Importance-Based Retention Example ===")
    
    config = OrchestratorConfig(
        immediate_buffer_size=5,
        session_max_size=10
    )
    orchestrator = ContextOrchestrator(config=config, enable_long_term=False)
    
    # Store items with different importance levels
    print("\nStoring items with varying importance...")
    
    importances = ["low", "normal", "high", "critical"]
    for i, importance in enumerate(importances):
        await orchestrator.store(
            f"Message with {importance} importance",
            metadata={"importance": importance}
        )
    
    # Add many low-importance items to trigger eviction
    print("Adding many low-importance items to trigger eviction...")
    for i in range(15):
        await orchestrator.store(
            f"Low priority item {i}",
            metadata={"importance": "low"}
        )
    
    # Retrieve all
    request = ContextRequest(
        query="importance",
        max_results=20,
        include_immediate=True,
        include_session=True
    )
    
    response = await orchestrator.retrieve(request)
    
    print(f"\nRetained {len(response.items)} items after eviction:")
    for item in response.items:
        imp = item.metadata.get('importance', 'unknown')
        print(f"  - {item.content[:50]}... [importance: {imp}]")
    
    # High importance items should still be present
    contents = [item.content for item in response.items]
    assert any("critical" in c.lower() for c in contents), "Critical item was evicted!"
    assert any("high" in c.lower() for c in contents), "High importance item was evicted!"
    print("\n✓ High importance items retained despite eviction")


async def layer_management_example():
    """Example of explicit layer management."""
    print("\n\n=== Layer Management Example ===")
    
    orchestrator = ContextOrchestrator(enable_long_term=False)
    
    # Explicitly target different layers
    print("\nStoring in different layers...")
    
    # Immediate buffer (recent conversation)
    await orchestrator.store(
        "Just now: User asked about deployment",
        layer_hint=LayerType.IMMEDIATE
    )
    print("  ✓ Stored in immediate buffer")
    
    # Session memory (active task)
    await orchestrator.store(
        "Current task: Deploy microservices to Kubernetes",
        layer_hint=LayerType.SESSION,
        metadata={"task_id": "deploy_123"}
    )
    print("  ✓ Stored in session memory")
    
    # Check buffer sizes
    print(f"\nImmediate buffer size: {orchestrator.immediate_buffer.size}")
    print(f"Session memory size: {orchestrator.session_memory.size}")
    
    # Retrieve from specific layer
    print("\nRetrieving from immediate buffer only...")
    request = ContextRequest(
        query="deployment",
        include_immediate=True,
        include_session=False,
        include_long_term=False
    )
    
    response = await orchestrator.retrieve(request)
    print(f"Found {len(response.items)} items in immediate buffer")
    
    # Clear specific layer
    print("\nClearing immediate buffer...")
    orchestrator.clear_immediate()
    print(f"Immediate buffer size after clear: {orchestrator.immediate_buffer.size}")
    print(f"Session memory size (unchanged): {orchestrator.session_memory.size}")


async def retrieval_strategies_example():
    """Example of different retrieval strategies."""
    print("\n\n=== Retrieval Strategies Example ===")
    
    orchestrator = ContextOrchestrator(enable_long_term=False)
    
    # Store some test data
    test_data = [
        "Python is great for data science",
        "Machine learning with Python and scikit-learn",
        "Building REST APIs with FastAPI",
        "Deep learning using TensorFlow and PyTorch",
        "Data analysis with pandas and numpy"
    ]
    
    for content in test_data:
        await orchestrator.store(content)
    
    print("\nStored 5 items about Python and data science")
    
    # Try different strategies
    query = "Python machine learning"
    
    # Recency-based
    print(f"\nQuery: '{query}'")
    print("\nStrategy 1: RECENCY (most recent first)")
    request = ContextRequest(
        query=query,
        strategy=RetrievalStrategy.RECENCY,
        max_results=3
    )
    response = await orchestrator.retrieve(request)
    for item in response.items:
        print(f"  - {item.content}")
    
    # Relevance-based
    print("\nStrategy 2: RELEVANCE (best match)")
    request = ContextRequest(
        query=query,
        strategy=RetrievalStrategy.RELEVANCE,
        max_results=3
    )
    response = await orchestrator.retrieve(request)
    for item in response.items:
        print(f"  - {item.content}")


async def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("Multi-Layer Context Foundation - Usage Examples")
    print("="*60)
    
    try:
        await basic_example()
        await conversation_tracking_example()
        await importance_based_example()
        await layer_management_example()
        await retrieval_strategies_example()
        
        print("\n" + "="*60)
        print("All examples completed successfully!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())