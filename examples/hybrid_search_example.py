#!/usr/bin/env python
"""
Hybrid Search Example - Combines semantic and keyword search.
"""

import sys

try:
    from mlcf.retrieval.hybrid_engine import HybridRetrievalEngine
    from mlcf.storage.vector_store import QdrantVectorStore
    from mlcf.embeddings.embedding_generator import EmbeddingGenerator
except ImportError as e:
    print(f"Error: {e}")
    print("Install: pip install qdrant-client sentence-transformers")
    sys.exit(1)


def main():
    """Demonstrate hybrid search."""
    print("\n" + "="*60)
    print("Hybrid Search Example - Semantic + Keyword")
    print("="*60 + "\n")
    
    # Initialize vector store
    print("1. Initializing vector store...")
    try:
        vector_store = QdrantVectorStore(
            collection_name="hybrid_demo",
            host="localhost",
            port=6333
        )
        print("   ✓ Vector store ready")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        print("   Run: docker-compose up -d qdrant")
        return
    
    # Initialize hybrid engine
    print("\n2. Initializing hybrid retrieval engine...")
    
    config = {
        "semantic_weight": 0.6,
        "keyword_weight": 0.4,
        "chunk_size": 200
    }
    
    engine = HybridRetrievalEngine(
        config=config,
        vector_store=vector_store
    )
    print("   ✓ Hybrid engine ready")
    
    # Index documents
    print("\n3. Indexing documents...")
    
    documents = [
        {
            "id": "python_ml",
            "content": "Python is excellent for machine learning. Libraries like scikit-learn, TensorFlow, and PyTorch make it easy to build ML models.",
            "metadata": {"category": "AI", "language": "python"}
        },
        {
            "id": "java_enterprise",
            "content": "Java remains the top choice for enterprise applications. Its stability and ecosystem make it ideal for large-scale systems.",
            "metadata": {"category": "Enterprise", "language": "java"}
        },
        {
            "id": "python_web",
            "content": "Python web frameworks like Django and FastAPI enable rapid development of web applications and RESTful APIs.",
            "metadata": {"category": "Web", "language": "python"}
        },
        {
            "id": "ml_algorithms",
            "content": "Machine learning algorithms include supervised learning (classification, regression) and unsupervised learning (clustering).",
            "metadata": {"category": "AI", "language": "general"}
        }
    ]
    
    for doc in documents:
        engine.index_document(
            doc_id=doc["id"],
            content=doc["content"],
            metadata=doc["metadata"],
            index_in_vector_store=True
        )
    
    print(f"   ✓ Indexed {len(documents)} documents")
    
    # Test different strategies
    print("\n4. Testing different retrieval strategies...")
    
    query = "Python machine learning"
    
    # Keyword search
    print(f"\nQuery: '{query}'")
    print("\nA) Keyword Search (BM25):")
    print("-" * 60)
    
    keyword_results = engine.retrieve(
        query=query,
        max_results=3,
        strategy="keyword"
    )
    
    for i, r in enumerate(keyword_results, 1):
        print(f"{i}. [{r['id']}] Score: {r['score']:.3f}")
        print(f"   {r['content'][:70]}...")
    
    # Semantic search
    print("\nB) Semantic Search (Vectors):")
    print("-" * 60)
    
    semantic_results = engine.retrieve(
        query=query,
        max_results=3,
        strategy="semantic"
    )
    
    for i, r in enumerate(semantic_results, 1):
        print(f"{i}. [{r['id']}] Score: {r['score']:.3f}")
        print(f"   {r['content'][:70]}...")
    
    # Hybrid search
    print("\nC) Hybrid Search (Combined):")
    print("-" * 60)
    
    hybrid_results = engine.retrieve(
        query=query,
        max_results=3,
        strategy="hybrid"
    )
    
    for i, r in enumerate(hybrid_results, 1):
        component_scores = r.get('component_scores', {})
        print(f"{i}. [{r['id']}] Combined: {r['score']:.3f}")
        if component_scores:
            print(f"   Semantic: {component_scores.get('semantic', 0):.3f}, "
                  f"Keyword: {component_scores.get('keyword', 0):.3f}")
        print(f"   {r['content'][:70]}...")
    
    # Statistics
    print("\n5. Retrieval Statistics:")
    print("-" * 60)
    
    stats = engine.get_statistics()
    print(f"Total documents: {stats['total_documents']}")
    print(f"BM25 indexed: {stats['bm25_stats']['total_documents']}")
    print(f"Semantic enabled: {stats['semantic_enabled']}")
    print(f"Weights: Semantic={stats['weights']['semantic']}, "
          f"Keyword={stats['weights']['keyword']}")
    
    # Cleanup
    print("\n6. Cleaning up...")
    vector_store.clear_collection()
    print("   ✓ Done")
    
    print("\n" + "="*60)
    print("Hybrid search example completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()