#!/usr/bin/env python
"""
Vector Search Example - Demonstrates semantic search with Qdrant.
"""

import sys

try:
    from mlcf.storage.vector_store import QdrantVectorStore
    from mlcf.embeddings.embedding_generator import EmbeddingGenerator
    from mlcf.retrieval.semantic_search import SemanticSearch
except ImportError as e:
    print(f"Error: {e}")
    print("Please install required dependencies:")
    print("  pip install qdrant-client sentence-transformers")
    sys.exit(1)


def main():
    """Demonstrate vector search capabilities."""
    print("=" * 60)
    print("Vector Search with Qdrant - Example")
    print("=" * 60)
    print()
    
    # Initialize components
    print("1. Initializing Qdrant vector store...")
    try:
        vector_store = QdrantVectorStore(
            collection_name="demo_collection",
            host="localhost",
            port=6333,
            embedding_dim=384
        )
        print("   ✓ Connected to Qdrant")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        print("   Make sure Qdrant is running: docker-compose up -d qdrant")
        return
    
    print()
    
    # Add sample documents
    print("2. Adding sample documents...")
    
    documents = [
        (
            "ml_python",
            "Machine learning with Python is powerful for data science",
            {"category": "AI", "language": "Python"}
        ),
        (
            "dl_networks",
            "Deep learning neural networks can solve complex problems",
            {"category": "AI", "language": "Python"}
        ),
        (
            "java_enterprise",
            "Java is widely used for building enterprise applications",
            {"category": "Programming", "language": "Java"}
        ),
        (
            "python_web",
            "Python web frameworks like FastAPI are great for APIs",
            {"category": "Web", "language": "Python"}
        ),
        (
            "data_science",
            "Data science involves statistics, ML, and data visualization",
            {"category": "Data", "language": "Python"}
        )
    ]
    
    vector_store.add_batch(documents)
    print(f"   ✓ Added {len(documents)} documents")
    print()
    
    # Initialize semantic search
    print("3. Initializing semantic search...")
    semantic_search = SemanticSearch(vector_store=vector_store)
    print("   ✓ Semantic search ready")
    print()
    
    # Perform searches
    print("4. Running semantic searches...")
    print()
    
    queries = [
        "Python machine learning",
        "artificial intelligence",
        "web development"
    ]
    
    for query in queries:
        print(f"Query: '{query}'")
        print("-" * 60)
        
        results = semantic_search.search(
            query=query,
            max_results=3,
            score_threshold=0.3
        )
        
        for i, result in enumerate(results, 1):
            print(f"{i}. [Score: {result['score']:.3f}] {result['id']}")
            print(f"   {result['content'][:60]}...")
            print(f"   Metadata: {result['metadata']}")
            print()
        
        if not results:
            print("   No results found.")
            print()
    
    # Test with filters
    print("5. Search with metadata filters...")
    print()
    
    print("Query: 'programming' (Python only)")
    print("-" * 60)
    
    results = semantic_search.search(
        query="programming",
        max_results=5,
        filters={"language": "Python"}
    )
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['id']}: {result['content'][:50]}...")
    print()
    
    # Show collection stats
    print("6. Collection statistics:")
    print("-" * 60)
    
    info = vector_store.get_collection_info()
    print(f"Collection: {info.get('name')}")
    print(f"Vectors: {info.get('vectors_count', 0)}")
    print(f"Points: {info.get('points_count', 0)}")
    print(f"Dimension: {info.get('config', {}).get('dimension', 0)}")
    print()
    
    # Cleanup
    print("7. Cleaning up...")
    vector_store.clear_collection()
    print("   ✓ Collection cleared")
    print()
    
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()