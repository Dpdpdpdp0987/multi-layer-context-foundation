#!/usr/bin/env python
"""
Basic usage example for Multi-Layer Context Foundation.
"""

from mlcf.core.orchestrator import (
    ContextOrchestrator,
    ContextType,
    ContextPriority
)
from mlcf.core.config import Config


def main():
    """Demonstrate basic MLCF usage."""
    print("=" * 60)
    print("Multi-Layer Context Foundation - Basic Usage Example")
    print("=" * 60)
    print()
    
    # Initialize configuration
    config = Config(
        short_term_max_size=10,
        working_memory_max_size=50
    )
    
    # Create orchestrator
    print("1. Initializing Context Orchestrator...")
    orchestrator = ContextOrchestrator(config=config)
    print(f"   ✓ Orchestrator initialized")
    print()
    
    # Start a session
    print("2. Starting new session...")
    session_id = orchestrator.start_new_session()
    print(f"   ✓ Session started: {session_id}")
    print()
    
    # Add various types of context
    print("3. Adding context items...")
    
    # Add conversational context (goes to immediate buffer)
    orchestrator.add_context(
        content="User asked about Python programming",
        context_type=ContextType.CONVERSATION,
        priority=ContextPriority.MEDIUM
    )
    print("   ✓ Added conversation context")
    
    # Add task context (goes to session memory)
    orchestrator.add_context(
        content="User is working on a machine learning project using scikit-learn",
        context_type=ContextType.TASK,
        priority=ContextPriority.HIGH,
        metadata={"project": "ml_classifier", "framework": "scikit-learn"}
    )
    print("   ✓ Added task context")
    
    # Add factual knowledge (goes to persistent memory)
    orchestrator.add_context(
        content="User prefers Python over Java for data science tasks",
        context_type=ContextType.PREFERENCE,
        priority=ContextPriority.CRITICAL,
        metadata={"category": "programming", "topic": "language_preference"}
    )
    print("   ✓ Added preference (fact)")
    
    # Add more conversational context
    orchestrator.add_context(
        content="User mentioned experience with pandas and numpy",
        context_type=ContextType.CONVERSATION
    )
    print("   ✓ Added more conversation context")
    print()
    
    # Retrieve relevant context
    print("4. Retrieving relevant context...")
    query = "What programming language should I use for this project?"
    print(f"   Query: '{query}'")
    print()
    
    results = orchestrator.retrieve_context(
        query=query,
        max_results=5,
        strategy="hybrid"
    )
    
    print(f"   Found {len(results)} relevant items:")
    print()
    for i, item in enumerate(results, 1):
        print(f"   {i}. [{item.context_type.value}] (score: {item.relevance_score:.3f})")
        print(f"      {item.content[:80]}..." if len(item.content) > 80 else f"      {item.content}")
        print()
    
    # Get active context within token budget
    print("5. Getting active context (within token budget)...")
    active_items, token_count = orchestrator.get_active_context(max_tokens=1000)
    print(f"   ✓ Retrieved {len(active_items)} items using {token_count} tokens")
    print()
    
    # Show statistics
    print("6. System statistics:")
    stats = orchestrator.get_statistics()
    print(f"   Immediate buffer: {stats['immediate_buffer_size']} items")
    print(f"   Session memory: {stats['session_memory_size']} items")
    print(f"   Token budget: {stats['context_budget_used']}/{stats['context_budget_max']} "
          f"({stats['budget_usage_percent']:.1f}%)")
    print()
    
    # Demonstrate BM25 keyword search
    print("7. BM25 Keyword Search Example...")
    from mlcf.retrieval.bm25_search import BM25Search
    
    bm25 = BM25Search()
    
    # Index some documents
    bm25.add_document(
        "doc1",
        "Python is excellent for machine learning with libraries like scikit-learn",
        {"type": "tech"}
    )
    bm25.add_document(
        "doc2",
        "Java is widely used for enterprise applications",
        {"type": "tech"}
    )
    bm25.add_document(
        "doc3",
        "Machine learning requires understanding of algorithms and data",
        {"type": "tech"}
    )
    
    # Search
    bm25_results = bm25.search("Python machine learning", max_results=3)
    print(f"   Found {len(bm25_results)} documents:")
    for i, result in enumerate(bm25_results, 1):
        print(f"   {i}. (BM25 score: {result['score']:.3f})")
        print(f"      {result['content']}")
    print()
    
    # Demonstrate adaptive chunking
    print("8. Adaptive Chunking Example...")
    from mlcf.retrieval.adaptive_chunking import AdaptiveChunker
    
    chunker = AdaptiveChunker(chunk_size=100, base_overlap=20)
    
    long_text = (
        "Natural language processing is a subfield of artificial intelligence. "
        "It focuses on the interaction between computers and human language. "
        "NLP techniques are used in many applications today. "
        "Machine learning has greatly improved NLP capabilities. "
        "Deep learning models like transformers have revolutionized the field."
    )
    
    chunks = chunker.chunk_text(long_text)
    print(f"   Created {len(chunks)} chunks from {len(long_text)} characters")
    for i, chunk in enumerate(chunks, 1):
        print(f"   Chunk {i}: {len(chunk)} chars, overlap: {chunk.overlap_after}")
        print(f"      {chunk.content[:60]}...")
    print()
    
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()