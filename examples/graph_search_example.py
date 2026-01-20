#!/usr/bin/env python
"""
Graph Search Example - Demonstrates graph-based retrieval.
"""

import sys

try:
    from mlcf.graph.neo4j_store import Neo4jStore
    from mlcf.retrieval.graph_search import GraphSearch
    from mlcf.graph.knowledge_graph import KnowledgeGraph
except ImportError as e:
    print(f"Error: {e}")
    print("Install: pip install neo4j spacy")
    sys.exit(1)


def main():
    """Demonstrate graph-based search."""
    print("\n" + "="*60)
    print("Graph Search Example")
    print("="*60 + "\n")
    
    try:
        # Initialize Neo4j
        print("1. Connecting to Neo4j...")
        neo4j_store = Neo4jStore(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        print("   ✓ Connected\n")
        
        # Build knowledge graph
        print("2. Building knowledge graph...")
        kg = KnowledgeGraph(neo4j_store=neo4j_store)
        
        # Add sample data
        sample_data = [
            "Python is a programming language created by Guido van Rossum.",
            "TensorFlow is a machine learning framework developed by Google.",
            "PyTorch is used for deep learning and was created by Facebook.",
            "Scikit-learn is a Python library for machine learning.",
            "FastAPI is a modern Python web framework."
        ]
        
        for i, text in enumerate(sample_data):
            kg.process_text(text, document_id=f"sample_{i}")
        
        print(f"   ✓ Processed {len(sample_data)} documents\n")
        
        # Initialize graph search
        print("3. Initializing graph search...")
        graph_search = GraphSearch(neo4j_store=neo4j_store)
        print("   ✓ Graph search ready\n")
        
        # Perform searches
        print("4. Performing graph searches...\n")
        
        queries = [
            "Python",
            "machine learning",
            "Google"
        ]
        
        for query in queries:
            print(f"Query: '{query}'")
            print("-" * 60)
            
            results = graph_search.search(query, max_results=5)
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"{i}. [Score: {result['score']:.2f}]")
                    print(f"   {result['content'][:80]}...")
                    
                    # Show entity info if available
                    entity = result.get('metadata', {}).get('entity', {})
                    if entity:
                        print(f"   Entity: {entity.get('name')} ({entity.get('type')})")
                    
                    print()
            else:
                print("   No results found.\n")
        
        # Find paths
        print("5. Finding paths between entities...\n")
        
        print("Finding path: Python -> Google")
        print("-" * 60)
        
        path = graph_search.find_path("Python", "Google")
        
        if path:
            nodes = path.get('nodes', [])
            relationships = path.get('relationships', [])
            
            print(f"Found path with {len(nodes)} nodes:\n")
            
            for i, node in enumerate(nodes):
                print(f"  {i+1}. {node.get('name', 'Unknown')} ({node.get('type', 'Unknown')})")
                
                if i < len(relationships):
                    rel = relationships[i]
                    print(f"      ↓ [{dict(rel).get('type', 'RELATED')}]")
            
            print()
        else:
            print("  No path found between entities.\n")
        
        # Explore neighborhood
        print("6. Exploring entity neighborhoods...\n")
        
        python_results = neo4j_store.semantic_search("Python", max_results=1)
        
        if python_results:
            python_id = python_results[0]['id']
            print(f"Exploring: {python_results[0]['name']}")
            print("-" * 60)
            
            neighborhood = graph_search.explore_neighborhood(python_id, depth=1)
            
            print(f"Nodes in neighborhood: {len(neighborhood.get('nodes', []))}")
            for node in neighborhood.get('nodes', [])[:5]:
                print(f"  - {node.get('name')} ({node.get('type')})")
            
            print(f"\nRelationships: {len(neighborhood.get('relationships', []))}")
            for rel in neighborhood.get('relationships', [])[:5]:
                print(f"  - {dict(rel).get('type', 'RELATED')}")
            
            print()
        
        # Show statistics
        print("7. Graph Statistics:")
        print("-" * 60)
        
        stats = neo4j_store.get_statistics()
        
        print("Nodes by type:")
        for node_type, count in stats.get('nodes_by_type', {}).items():
            print(f"  - {node_type}: {count}")
        
        print("\nRelationships by type:")
        for rel_type, count in stats.get('relationships_by_type', {}).items():
            print(f"  - {rel_type}: {count}")
        
        print()
        
        neo4j_store.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "="*60)
    print("Example completed! Explore graph at http://localhost:7474")
    print("Username: neo4j, Password: password")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()