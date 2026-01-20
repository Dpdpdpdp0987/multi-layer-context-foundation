#!/usr/bin/env python
"""
Complete Hybrid Example - Semantic + Keyword + Graph search.
"""

import sys

try:
    from mlcf.retrieval.hybrid_retriever import HybridRetriever
    from mlcf.storage.vector_store import QdrantVectorStore
    from mlcf.graph.neo4j_store import Neo4jStore
    from mlcf.graph.knowledge_graph import KnowledgeGraph
except ImportError as e:
    print(f"Error: {e}")
    print("Install: pip install qdrant-client neo4j spacy sentence-transformers")
    sys.exit(1)


def main():
    """Demonstrate complete hybrid retrieval."""
    print("\n" + "="*70)
    print("Complete Hybrid Retrieval - Semantic + Keyword + Graph")
    print("="*70 + "\n")
    
    # Initialize all components
    print("1. Initializing all components...")
    
    try:
        # Vector store (Qdrant)
        vector_store = QdrantVectorStore(
            collection_name="hybrid_demo",
            host="localhost",
            port=6333
        )
        print("   ✓ Vector store ready (Qdrant)")
        
        # Graph store (Neo4j)
        graph_store = Neo4jStore(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        print("   ✓ Graph store ready (Neo4j)")
        
        # Initialize hybrid retriever
        retriever = HybridRetriever(
            vector_store=vector_store,
            graph_store=graph_store,
            config={
                "semantic_weight": 0.5,
                "keyword_weight": 0.3,
                "graph_weight": 0.2
            }
        )
        print("   ✓ Hybrid retriever ready\n")
        
        # Initialize knowledge graph for entity extraction
        kg = KnowledgeGraph(
            neo4j_store=graph_store,
            auto_commit=True
        )
        print("   ✓ Knowledge graph ready\n")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        print("\n   Make sure services are running:")
        print("   docker-compose up -d qdrant neo4j")
        return
    
    # Sample documents about AI and technology
    print("2. Indexing sample documents...\n")
    
    documents = [
        {
            "id": "doc1",
            "content": "Python is the most popular language for machine learning. Libraries like TensorFlow, PyTorch, and scikit-learn make it powerful for AI development.",
            "metadata": {"category": "AI", "language": "Python"}
        },
        {
            "id": "doc2",
            "content": "TensorFlow was developed by Google Brain team. It's an open-source machine learning framework used for deep learning applications.",
            "metadata": {"category": "AI", "framework": "TensorFlow"}
        },
        {
            "id": "doc3",
            "content": "FastAPI is a modern Python web framework for building APIs. It's fast, easy to use, and supports async operations.",
            "metadata": {"category": "Web", "language": "Python"}
        },
        {
            "id": "doc4",
            "content": "Natural language processing enables computers to understand human language. It's a key component of AI systems.",
            "metadata": {"category": "AI", "topic": "NLP"}
        },
        {
            "id": "doc5",
            "content": "Neural networks are inspired by biological neurons. Deep learning uses multi-layer neural networks for complex pattern recognition.",
            "metadata": {"category": "AI", "topic": "Deep Learning"}
        }
    ]
    
    for doc in documents:
        # Index in hybrid retriever (keyword + vector)
        retriever.bm25_search.add_document(
            doc["id"],
            doc["content"],
            doc["metadata"]
        )
        
        vector_store.add(
            doc["id"],
            doc["content"],
            doc["metadata"]
        )
        
        # Extract entities and build knowledge graph
        kg.process_text(
            doc["content"],
            document_id=doc["id"],
            metadata=doc["metadata"]
        )
        
        print(f"   ✓ Indexed: {doc['id']}")
    
    print(f"\n   Total indexed: {len(documents)} documents\n")
    
    # Test different retrieval strategies
    print("3. Testing retrieval strategies...\n")
    
    test_queries = [
        "Python machine learning",
        "Google AI framework",
        "web development"
    ]
    
    for query in test_queries:
        print(f"Query: '{query}'")
        print("=" * 70)
        
        # Keyword search
        print("\nA) Keyword Search (BM25):")
        keyword_results = retriever.retrieve(
            query=query,
            max_results=3,
            strategy="keyword"
        )
        
        for i, r in enumerate(keyword_results, 1):
            print(f"  {i}. [Score: {r['score']:.3f}] {r['id']}")
            print(f"     {r['content'][:60]}...")
        
        # Semantic search
        print("\nB) Semantic Search (Vectors):")
        semantic_results = retriever.retrieve(
            query=query,
            max_results=3,
            strategy="semantic"
        )
        
        for i, r in enumerate(semantic_results, 1):
            print(f"  {i}. [Score: {r['score']:.3f}] {r['id']}")
            print(f"     {r['content'][:60]}...")
        
        # Graph search
        print("\nC) Graph Search (Relationships):")
        graph_results = retriever.retrieve(
            query=query,
            max_results=3,
            strategy="graph"
        )
        
        for i, r in enumerate(graph_results, 1):
            print(f"  {i}. [Score: {r['score']:.3f}] {r['id']}")
            print(f"     {r['content'][:60]}...")
        
        # Hybrid search
        print("\nD) Hybrid Search (Combined):")
        hybrid_results = retriever.retrieve(
            query=query,
            max_results=3,
            strategy="hybrid"
        )
        
        for i, r in enumerate(hybrid_results, 1):
            scores = r.get('component_scores', {})
            print(f"  {i}. [Combined: {r['score']:.3f}] {r['id']}")
            
            if scores:
                score_parts = []
                if 'semantic' in scores:
                    score_parts.append(f"Sem:{scores['semantic']:.2f}")
                if 'keyword' in scores:
                    score_parts.append(f"Key:{scores['keyword']:.2f}")
                if 'graph' in scores:
                    score_parts.append(f"Grp:{scores['graph']:.2f}")
                
                print(f"     ({', '.join(score_parts)})")
            
            print(f"     {r['content'][:60]}...")
        
        print("\n" + "-" * 70 + "\n")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Show comparison
    print("4. Strategy Comparison:")
    print("=" * 70)
    print("\nKeyword Search:")
    print("  ✓ Fast (10-20ms)")
    print("  ✓ Exact matching")
    print("  ✗ Misses semantic similarity")
    
    print("\nSemantic Search:")
    print("  ✓ Understands meaning")
    print("  ✓ Finds conceptually similar")
    print("  ✗ Slower (50-100ms)")
    
    print("\nGraph Search:")
    print("  ✓ Finds related entities")
    print("  ✓ Discovers relationships")
    print("  ✗ Requires entity extraction")
    
    print("\nHybrid Search:")
    print("  ✓ Best of all worlds")
    print("  ✓ Balanced speed/quality")
    print("  ✓ Comprehensive coverage")
    print()
    
    # Cleanup
    vector_store.clear_collection()
    graph_store.close()
    
    print("\n" + "="*70)
    print("Complete hybrid example finished!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()