#!/usr/bin/env python
"""
Knowledge Graph Example - Entity extraction and relationship mapping.
"""

import sys

try:
    from mlcf.graph.knowledge_graph import KnowledgeGraph
    from mlcf.graph.neo4j_store import Neo4jStore
    from mlcf.graph.entity_extractor import EntityExtractor
    from mlcf.graph.relationship_mapper import RelationshipMapper
except ImportError as e:
    print(f"Error: {e}")
    print("Please install required dependencies:")
    print("  pip install neo4j spacy")
    print("  python -m spacy download en_core_web_sm")
    sys.exit(1)


def main():
    """Demonstrate knowledge graph building."""
    print("\n" + "="*70)
    print("Knowledge Graph Example - Entity Extraction & Relationship Mapping")
    print("="*70 + "\n")
    
    # Initialize components
    print("1. Initializing Knowledge Graph components...")
    
    try:
        # Connect to Neo4j
        neo4j_store = Neo4jStore(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        print("   ✓ Connected to Neo4j")
        
        # Initialize entity extractor
        entity_extractor = EntityExtractor(model_name="en_core_web_sm")
        print("   ✓ Entity extractor ready")
        
        # Initialize relationship mapper
        relationship_mapper = RelationshipMapper(model_name="en_core_web_sm")
        print("   ✓ Relationship mapper ready")
        
        # Create knowledge graph
        kg = KnowledgeGraph(
            neo4j_store=neo4j_store,
            entity_extractor=entity_extractor,
            relationship_mapper=relationship_mapper,
            auto_commit=True
        )
        print("   ✓ Knowledge graph initialized\n")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        print("   Make sure Neo4j is running: docker-compose up -d neo4j")
        return
    
    # Sample texts to process
    sample_texts = [
        "Steve Jobs founded Apple Inc. in 1976 in California.",
        "Tim Cook became CEO of Apple in 2011.",
        "Apple develops the iPhone and MacBook products.",
        "Microsoft was founded by Bill Gates and Paul Allen.",
        "Satya Nadella is the current CEO of Microsoft.",
    ]
    
    print("2. Processing sample texts...\n")
    
    for i, text in enumerate(sample_texts, 1):
        print(f"Text {i}: {text}")
        print("-" * 70)
        
        # Process text
        result = kg.process_text(
            text=text,
            document_id=f"doc_{i}",
            metadata={"source": "example"}
        )
        
        # Display extracted entities
        print(f"Entities extracted: {result['entity_count']}")
        for entity in result['entities']:
            print(f"  - {entity['text']} ({entity['type']})")
        
        # Display extracted relationships
        print(f"Relationships extracted: {result['relationship_count']}")
        for rel in result['relationships']:
            source = rel['source']['text']
            target = rel['target']['text']
            rel_type = rel['type']
            print(f"  - {source} --[{rel_type}]--> {target}")
        
        print()
    
    # Query the knowledge graph
    print("3. Querying the knowledge graph...\n")
    
    queries = [
        "Apple",
        "Steve Jobs",
        "CEO"
    ]
    
    for query in queries:
        print(f"Query: '{query}'")
        print("-" * 70)
        
        results = kg.query(query, max_results=5)
        
        for result in results:
            name = result.get('name', 'Unknown')
            entity_type = result.get('type', 'Unknown')
            score = result.get('score', 0.0)
            print(f"  - {name} ({entity_type}) [score: {score:.2f}]")
        
        print()
    
    # Explore entity neighborhood
    print("4. Exploring entity relationships...\n")
    
    # Find Apple entity
    apple_results = kg.query("Apple", max_results=1)
    
    if apple_results:
        apple_id = apple_results[0]['id']
        print(f"Exploring relationships for: {apple_results[0]['name']}")
        print("-" * 70)
        
        # Get relationships
        relationships = neo4j_store.get_relationships(apple_id, direction="both")
        
        print(f"Found {len(relationships)} relationships:")
        for rel in relationships:
            source_name = rel['source'].get('name', 'Unknown')
            target_name = rel['target'].get('name', 'Unknown')
            rel_type = rel['type']
            print(f"  - {source_name} --[{rel_type}]--> {target_name}")
        
        print()
        
        # Get neighborhood subgraph
        print("Neighborhood subgraph:")
        print("-" * 70)
        
        neighborhood = kg.explore_neighborhood(apple_id, depth=1)
        print(f"  Nodes: {len(neighborhood.get('nodes', []))}")
        print(f"  Relationships: {len(neighborhood.get('relationships', []))}")
        
        print()
    
    # Find path between entities
    print("5. Finding paths between entities...\n")
    
    path = kg.find_path("Steve Jobs", "Apple")
    
    if path:
        print(f"Found path with {len(path.get('nodes', []))} nodes:")
        for i, node in enumerate(path.get('nodes', [])):
            print(f"  {i+1}. {node.get('name', 'Unknown')} ({node.get('type', 'Unknown')})")
    else:
        print("  No path found")
    
    print()
    
    # Show statistics
    print("6. Knowledge Graph Statistics:")
    print("-" * 70)
    
    stats = kg.get_statistics()
    graph_stats = stats.get('graph_stats', {})
    
    print("Nodes by type:")
    for node_type, count in graph_stats.get('nodes_by_type', {}).items():
        print(f"  - {node_type}: {count}")
    
    print("\nRelationships by type:")
    for rel_type, count in graph_stats.get('relationships_by_type', {}).items():
        print(f"  - {rel_type}: {count}")
    
    print()
    
    # Cleanup (optional)
    print("7. Cleaning up...")
    # In production, you might want to keep the data
    # For demo, we clean up
    print("   ℹ Data kept in Neo4j for exploration")
    print("   Access Neo4j Browser at: http://localhost:7474")
    
    neo4j_store.close()
    
    print("\n" + "="*70)
    print("Knowledge graph example completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()