"""
Basic usage examples for the Multi-Layer Context Foundation system.

This file demonstrates:
1. Basic setup and initialization
2. Adding and retrieving context
3. Using different retrieval strategies
4. Session management and memory consolidation
5. Monitoring system metrics
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any

from context_foundation.orchestrator import ContextOrchestrator
from context_foundation.layers.immediate import ImmediateContextBuffer
from context_foundation.layers.session import SessionMemory
from context_foundation.layers.longterm import LongTermStore
from context_foundation.search.bm25 import BM25Search
from context_foundation.search.chunking import AdaptiveChunker
from context_foundation.search.hybrid import HybridRetrieval


async def basic_example():
    """Basic example of storing and retrieving context."""
    print("=== Basic Example ===\n")
    
    # Initialize the orchestrator
    orchestrator = ContextOrchestrator()
    
    # Add some context items
    items = [
        {
            "content": "User is working on a Python project with async/await patterns.",
            "metadata": {
                "type": "conversation",
                "timestamp": datetime.now().isoformat(),
                "priority": "high"
            }
        },
        {
            "content": "The project uses PostgreSQL with pgvector for similarity search.",
            "metadata": {
                "type": "technical_detail",
                "timestamp": datetime.now().isoformat()
            }
        },
        {
            "content": "User prefers detailed code comments and type hints.",
            "metadata": {
                "type": "preference",
                "timestamp": datetime.now().isoformat()
            }
        }
    ]
    
    for item in items:
        context_id = await orchestrator.add_context(
            content=item["content"],
            metadata=item["metadata"]
        )
        print(f"Added context: {context_id}")
    
    print()
    
    # Retrieve relevant context
    query = "What database does the user prefer?"
    results = await orchestrator.get_context(query, max_results=5)
    
    print(f"Query: {query}")
    print(f"Found {len(results)} relevant items:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result['score']:.3f}")
        print(f"   Content: {result['content']}")
        print(f"   Layer: {result['layer']}")
    
    # Get system metrics
    metrics = orchestrator.get_metrics()
    print(f"\nSystem Metrics:")
    print(f"  Total items: {metrics['total_items']}")
    print(f"  Cache hits: {metrics['cache_hits']}")
    print(f"  Cache misses: {metrics['cache_misses']}")


async def session_management_example():
    """Example of session-based context management."""
    print("\n\n=== Session Management Example ===\n")
    
    orchestrator = ContextOrchestrator()
    session_id = "user_session_123"
    
    # Add conversation turns to a session
    conversation = [
        "Hello, I need help with my Python project.",
        "I'm building a RAG system with vector search.",
        "I want to use PostgreSQL with pgvector.",
        "Can you help me design the database schema?",
    ]
    
    for i, message in enumerate(conversation):
        await orchestrator.add_context(
            content=message,
            metadata={
                "session_id": session_id,
                "turn": i,
                "type": "conversation",
                "timestamp": datetime.now().isoformat()
            }
        )
        print(f"Added turn {i}: {message[:50]}...")
    
    # Retrieve session-specific context
    results = await orchestrator.get_context(
        query="database design",
        max_results=3,
        filters={"session_id": session_id}
    )
    
    print(f"\nRetrieved {len(results)} items from session {session_id}:")
    for result in results:
        print(f"  - {result['content'][:60]}... (score: {result['score']:.3f})")


async def layer_specific_example():
    """Example of working with specific context layers."""
    print("\n\n=== Layer-Specific Example ===\n")
    
    # Initialize individual layers
    immediate_buffer = ImmediateContextBuffer(
        max_size=10,
        ttl_seconds=300  # 5 minutes
    )
    
    session_memory = SessionMemory(
        max_size=50,
        consolidation_threshold=20
    )
    
    # Add to immediate buffer (hot context)
    immediate_items = [
        "The current task is implementing user authentication.",
        "Using JWT tokens for session management.",
        "Password hashing with bcrypt.",
    ]
    
    for content in immediate_items:
        item_id = await immediate_buffer.add_item(
            content=content,
            metadata={"layer": "immediate"}
        )
        print(f"Added to immediate buffer: {item_id}")
    
    # Add to session memory (conversation history)
    session_items = [
        "User asked about authentication best practices.",
        "Discussed OAuth2 vs JWT trade-offs.",
        "Decided to use JWT for simplicity.",
    ]
    
    for content in session_items:
        item_id = await session_memory.add_item(
            content=content,
            metadata={"layer": "session", "session_id": "auth_discussion"}
        )
        print(f"Added to session memory: {item_id}")
    
    # Retrieve from specific layers
    print("\nRetrieving from immediate buffer:")
    immediate_results = await immediate_buffer.get_items(
        query="authentication implementation",
        max_results=3
    )
    for result in immediate_results:
        print(f"  - {result['content']}")
    
    print("\nRetrieving from session memory:")
    session_results = await session_memory.get_items(
        query="authentication discussion",
        max_results=3
    )
    for result in session_results:
        print(f"  - {result['content']}")


async def retrieval_strategies_example():
    """Example of different retrieval strategies."""
    print("\n\n=== Retrieval Strategies Example ===\n")
    
    # Initialize BM25 for keyword search
    bm25 = BM25Search()
    
    # Sample documents
    documents = [
        {
            "id": "doc1",
            "content": "Python is a high-level programming language known for its simplicity.",
            "metadata": {"category": "programming"}
        },
        {
            "id": "doc2",
            "content": "PostgreSQL is a powerful open-source relational database system.",
            "metadata": {"category": "database"}
        },
        {
            "id": "doc3",
            "content": "Vector search enables semantic similarity matching in databases.",
            "metadata": {"category": "search"}
        },
        {
            "id": "doc4",
            "content": "Python has excellent support for database connectivity with libraries like psycopg2.",
            "metadata": {"category": "programming"}
        }
    ]
    
    # Add documents to BM25 index
    for doc in documents:
        await bm25.index_document(doc["id"], doc["content"], doc["metadata"])
    
    print("Indexed documents for BM25 search\n")
    
    # Keyword search
    query = "Python database"
    results = await bm25.search(query, top_k=3)
    
    print(f"BM25 keyword search for '{query}':")
    for i, result in enumerate(results, 1):
        print(f"{i}. Score: {result['score']:.3f}")
        print(f"   Content: {result['content'][:60]}...")
    
    # Demonstrate adaptive chunking
    print("\n\nAdaptive Chunking Example:")
    
    chunker = AdaptiveChunker(
        target_chunk_size=100,
        min_chunk_size=50,
        max_chunk_size=200
    )
    
    long_text = """
    The Multi-Layer Context Foundation is a sophisticated system for managing conversational context.
    It implements multiple storage layers with different retention policies and access patterns.
    
    The immediate buffer stores hot, frequently accessed context with short TTL.
    Session memory maintains conversation history with automatic consolidation.
    Long-term storage preserves important information across sessions.
    
    The system uses hybrid retrieval combining semantic search, keyword matching, and graph-based traversal.
    This ensures comprehensive context recall while maintaining performance.
    """
    
    chunks = await chunker.chunk_text(long_text, metadata={"source": "documentation"})
    
    print(f"Split text into {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i}:")
        print(f"  Size: {chunk['chunk_size']} chars")
        print(f"  Overlap: {chunk['overlap_size']} chars")
        print(f"  Content: {chunk['content'][:80]}...")


async def metrics_and_monitoring_example():
    """Example of monitoring system performance."""
    print("\n\n=== Metrics and Monitoring Example ===\n")
    
    orchestrator = ContextOrchestrator()
    
    # Perform various operations
    for i in range(10):
        await orchestrator.add_context(
            content=f"Test item {i} with various keywords and content.",
            metadata={"index": i}
        )
    
    # Multiple queries (some will hit cache)
    queries = [
        "test keywords",
        "various content",
        "test keywords",  # Duplicate - should hit cache
        "item content",
        "test keywords",  # Duplicate - should hit cache
    ]
    
    for query in queries:
        await orchestrator.get_context(query, max_results=3)
    
    # Get detailed metrics
    metrics = orchestrator.get_metrics()
    
    print("System Metrics:")
    print(f"  Total items across all layers: {metrics['total_items']}")
    print(f"  Immediate buffer: {metrics['immediate_buffer']['size']}")
    print(f"  Session memory: {metrics['session_memory']['size']}")
    print(f"  Long-term store: {metrics['long_term_store']['size']}")
    print(f"\nCache Performance:")
    print(f"  Cache hits: {metrics['cache_hits']}")
    print(f"  Cache misses: {metrics['cache_misses']}")
    
    if metrics['cache_hits'] + metrics['cache_misses'] > 0:
        hit_rate = metrics['cache_hits'] / (metrics['cache_hits'] + metrics['cache_misses'])
        print(f"  Hit rate: {hit_rate:.1%}")
    
    print(f"\nRetrieval Stats:")
    print(f"  Total queries: {metrics['total_queries']}")
    print(f"  Avg results per query: {metrics['avg_results_per_query']:.1f}")


async def consolidation_example():
    """Example of session memory consolidation."""
    print("\n\n=== Memory Consolidation Example ===\n")
    
    session_memory = SessionMemory(
        max_size=20,
        consolidation_threshold=10
    )
    
    # Add many items to trigger consolidation
    print("Adding 15 items to trigger consolidation...")
    for i in range(15):
        await session_memory.add_item(
            content=f"Conversation turn {i}: discussing various topics and ideas.",
            metadata={
                "turn": i,
                "session_id": "consolidation_test",
                "importance": 0.5 + (i % 3) * 0.2  # Varying importance
            }
        )
    
    # Check if consolidation occurred
    stats = session_memory.get_stats()
    print(f"\nSession Memory Stats:")
    print(f"  Current size: {stats['current_size']}")
    print(f"  Max size: {stats['max_size']}")
    print(f"  Consolidation count: {stats['consolidation_count']}")
    print(f"  Total accesses: {stats['total_accesses']}")
    
    # Query to see consolidated results
    results = await session_memory.get_items(
        query="conversation topics",
        max_results=5
    )
    
    print(f"\nRetrieved {len(results)} items after consolidation:")
    for result in results:
        print(f"  - {result['content'][:50]}...")


async def main():
    """Run all examples."""
    print("Multi-Layer Context Foundation - Usage Examples")
    print("=" * 60)
    
    try:
        await basic_example()
        await session_management_example()
        await layer_specific_example()
        await retrieval_strategies_example()
        await metrics_and_monitoring_example()
        await consolidation_example()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
