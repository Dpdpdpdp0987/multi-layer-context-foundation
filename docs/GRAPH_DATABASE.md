# Neo4j Graph Database Integration

## Overview

The Multi-Layer Context Foundation includes complete Neo4j graph database integration for semantic knowledge representation through entity extraction, relationship mapping, and intelligent graph traversal.

## Features

### ✅ Implemented

1. **Neo4j Store** - Complete graph database operations
2. **Entity Extraction** - NLP-based entity recognition
3. **Relationship Mapping** - Automatic relationship discovery
4. **Knowledge Graph Builder** - Integrated graph construction
5. **Graph Search** - Relationship-based retrieval
6. **Hybrid Integration** - Combined with vector and keyword search

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Knowledge Graph Layer                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │   Entity     │  │ Relationship │  │   Graph     │  │
│  │  Extractor   │─▶│    Mapper    │─▶│   Builder   │  │
│  └──────────────┘  └──────────────┘  └─────────────┘  │
│         │                  │                  │         │
│         └──────────────────┴──────────────────┘         │
│                           │                             │
│                           ▼                             │
│                  ┌─────────────────┐                    │
│                  │   Neo4j Store   │                    │
│                  │   - Entities    │                    │
│                  │   - Relations   │                    │
│                  │   - Traversal   │                    │
│                  └─────────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

## Installation

### 1. Install Dependencies

```bash
pip install neo4j spacy
python -m spacy download en_core_web_sm
```

### 2. Start Neo4j

```bash
# Using Docker Compose
docker-compose up -d neo4j

# Or using Docker directly
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.14
```

### 3. Verify Connection

```bash
# Browser interface
open http://localhost:7474

# Or test connection
curl http://localhost:7474
```

## Quick Start

### Basic Usage

```python
from mlcf.graph.knowledge_graph import KnowledgeGraph
from mlcf.graph.neo4j_store import Neo4jStore

# Initialize
kg = KnowledgeGraph()

# Process text and build knowledge graph
text = "Steve Jobs founded Apple in 1976 in California."
result = kg.process_text(text)

# View extracted entities
for entity in result['entities']:
    print(f"{entity['text']} ({entity['type']})")

# View extracted relationships
for rel in result['relationships']:
    print(f"{rel['source']['text']} -> {rel['type']} -> {rel['target']['text']}")
```

### Query Knowledge Graph

```python
# Search for entities
results = kg.query("Apple", max_results=5)

for result in results:
    print(f"{result['name']} ({result['type']}) - Score: {result['score']}")

# Get entity neighborhood
subgraph = kg.get_entity_graph(entity_id, max_depth=2)
print(f"Nodes: {len(subgraph['nodes'])}")
print(f"Relationships: {len(subgraph['relationships'])}")
```

## Components

### 1. Neo4j Store

Low-level graph database operations.

```python
from mlcf.graph.neo4j_store import Neo4jStore

# Connect to Neo4j
store = Neo4jStore(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)

# Add entity
store.add_entity(
    entity_id="person_123",
    entity_type="Person",
    name="John Doe",
    properties={"role": "developer"}
)

# Add relationship
store.add_relationship(
    from_id="person_123",
    to_id="org_456",
    relationship_type="WORKS_FOR",
    properties={"since": 2020}
)

# Query
entity = store.get_entity("person_123")
relationships = store.get_relationships("person_123")
```

### 2. Entity Extractor

Extracts named entities from text using spaCy.

**Supported Entity Types:**
- PERSON - People, including fictional
- ORGANIZATION - Companies, agencies, institutions
- LOCATION - Countries, cities, states
- PRODUCT - Objects, vehicles, foods
- EVENT - Named events
- DATE - Absolute or relative dates
- EMAIL - Email addresses
- URL - Web URLs
- PHONE - Phone numbers

```python
from mlcf.graph.entity_extractor import EntityExtractor

# Initialize
extractor = EntityExtractor(model_name="en_core_web_sm")

# Extract entities
text = "Apple Inc. was founded by Steve Jobs in California."
entities = extractor.extract(text)

for entity in entities:
    print(f"{entity.text} ({entity.entity_type})")
    print(f"  Position: {entity.start}-{entity.end}")
    print(f"  Confidence: {entity.confidence}")
```

**Advanced Usage:**

```python
# Extract with context
results = extractor.extract_with_context(text, context_window=50)

for result in results:
    print(f"Entity: {result['text']}")
    print(f"Context: {result['context']}")

# Batch extraction
texts = ["Text 1", "Text 2", "Text 3"]
all_entities = extractor.extract_batch(texts)

# Filter by entity type
extractor = EntityExtractor(
    entity_types=["PERSON", "ORG"],
    min_confidence=0.7
)
```

### 3. Relationship Mapper

Identifies relationships between entities.

**Relationship Types Detected:**
- WORKS_FOR - Employment relationships
- LOCATED_IN - Location relationships
- FOUNDED - Creation relationships
- MANAGES - Management relationships
- OWNS - Ownership relationships
- CREATED - Creation relationships
- COLLABORATES_WITH - Partnership
- And more...

```python
from mlcf.graph.relationship_mapper import RelationshipMapper
from mlcf.graph.entity_extractor import EntityExtractor

# Initialize
extractor = EntityExtractor()
mapper = RelationshipMapper()

# Extract entities first
text = "Alice works at Google in California."
entities = extractor.extract(text)

# Extract relationships
relationships = mapper.extract(text, entities)

for rel in relationships:
    print(f"{rel.source.text} --[{rel.relationship_type}]--> {rel.target.text}")
    print(f"  Confidence: {rel.confidence}")
```

**Relationship Extraction Methods:**

1. **Dependency-based**: Uses syntactic dependencies
2. **Pattern-based**: Matches common patterns
3. **Co-occurrence**: Based on entity proximity

### 4. Knowledge Graph Builder

Integrated entity extraction and graph building.

```python
from mlcf.graph.knowledge_graph import KnowledgeGraph

# Initialize with custom components
kg = KnowledgeGraph(
    neo4j_store=neo4j_store,
    entity_extractor=entity_extractor,
    relationship_mapper=relationship_mapper,
    auto_commit=True  # Automatically commit to graph
)

# Process multiple documents
documents = [
    "Steve Jobs founded Apple.",
    "Tim Cook is CEO of Apple.",
    "Apple develops the iPhone."
]

for doc in documents:
    result = kg.process_text(
        text=doc,
        document_id=f"doc_{i}",
        metadata={"source": "example"}
    )
    
    print(f"Entities: {result['entity_count']}")
    print(f"Relationships: {result['relationship_count']}")
```

### 5. Graph Search

Retrieval using graph traversal.

```python
from mlcf.retrieval.graph_search import GraphSearch

# Initialize
graph_search = GraphSearch(
    neo4j_store=store,
    max_depth=3,
    max_results=10
)

# Search by entity
results = graph_search.search(
    query="Apple",
    entity_types=["Organization"],
    max_results=5
)

# Find path between entities
path = graph_search.find_path(
    from_entity="Steve Jobs",
    to_entity="iPhone"
)

if path:
    print(f"Path length: {len(path['nodes'])}")
    for node in path['nodes']:
        print(f"  - {node['name']} ({node['type']})")

# Explore neighborhood
neighborhood = graph_search.explore_neighborhood(
    entity_id="person_123",
    depth=2
)
```

## Graph Schema

### Node Labels

- `Entity` (base label for all entities)
- `Person`
- `Organization`
- `Location`
- `Product`
- `Event`
- `Concept`
- `Document`

### Node Properties

- `id` (unique identifier)
- `name` (entity name)
- `type` (entity type)
- `created_at` (timestamp)
- `updated_at` (timestamp)
- Custom properties from extraction

### Relationship Types

- `WORKS_FOR`
- `LOCATED_IN`
- `FOUNDED`
- `MANAGES`
- `OWNS`
- `CREATED`
- `DEVELOPED`
- `USES`
- `RELATED_TO`
- `CO_OCCURS_WITH`

### Relationship Properties

- `confidence` (extraction confidence)
- `created_at` (timestamp)
- `source_document` (origin)
- Custom properties

## Advanced Usage

### Custom Entity Types

```python
extractor = EntityExtractor(
    model_name="en_core_web_sm",
    entity_types=["PERSON", "ORG"],  # Filter types
    min_confidence=0.7
)

# Add custom type mapping
extractor.type_mapping["CUSTOM"] = "CustomType"
```

### Custom Relationship Patterns

```python
mapper = RelationshipMapper()

# Add custom verb patterns
mapper.verb_patterns["acquire"] = "ACQUIRED"
mapper.verb_patterns["merge"] = "MERGED_WITH"

# Add custom preposition patterns
mapper.prep_patterns["during"] = "DURING"
```

### Graph Traversal Queries

```python
# Find all companies a person worked for
query = """
MATCH (p:Person {id: $person_id})-[r:WORKS_FOR]->(o:Organization)
RETURN o.name as company, r.since as start_date
ORDER BY r.since DESC
"""

with store.driver.session() as session:
    result = session.run(query, person_id="person_123")
    for record in result:
        print(f"{record['company']} (since {record['start_date']})")

# Find connection paths
query = """
MATCH path = shortestPath(
  (a:Person {name: $name1})-[*..5]-(b:Person {name: $name2})
)
RETURN path
"""
```

### Cypher Query Examples

```python
# Most connected entities
query = """
MATCH (n:Entity)-[r]-()
RETURN n.name, n.type, count(r) as connections
ORDER BY connections DESC
LIMIT 10
"""

# Find communities
query = """
CALL gds.louvain.stream('myGraph')
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).name as name, communityId
ORDER BY communityId
"""

# Centrality analysis
query = """
CALL gds.pageRank.stream('myGraph')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).name as name, score
ORDER BY score DESC
LIMIT 10
"""
```

## Integration with Hybrid Retrieval

```python
from mlcf.retrieval.hybrid_retriever import HybridRetriever
from mlcf.storage.vector_store import QdrantVectorStore
from mlcf.graph.neo4j_store import Neo4jStore

# Initialize all stores
vector_store = QdrantVectorStore()
graph_store = Neo4jStore()

# Create hybrid retriever
retriever = HybridRetriever(
    vector_store=vector_store,
    graph_store=graph_store,
    config={
        "semantic_weight": 0.5,  # Vector search
        "keyword_weight": 0.3,   # BM25 search
        "graph_weight": 0.2      # Graph search
    }
)

# Hybrid search combines all methods
results = retriever.retrieve(
    query="Python machine learning",
    strategy="hybrid",
    max_results=10
)

for result in results:
    print(f"{result['id']}: {result['score']:.3f}")
    
    # Show component scores
    scores = result.get('component_scores', {})
    print(f"  Semantic: {scores.get('semantic', 0):.3f}")
    print(f"  Keyword: {scores.get('keyword', 0):.3f}")
    print(f"  Graph: {scores.get('graph', 0):.3f}")
```

## Performance Optimization

### Indexing

```python
# Indexes are created automatically in Neo4jStore
# Additional custom indexes:

with store.driver.session() as session:
    # Full-text index for entity names
    session.run("""
        CREATE FULLTEXT INDEX entity_names IF NOT EXISTS
        FOR (e:Entity)
        ON EACH [e.name, e.description]
    """)
    
    # Composite index
    session.run("""
        CREATE INDEX entity_type_name IF NOT EXISTS
        FOR (e:Entity)
        ON (e.type, e.name)
    """)
```

### Batch Processing

```python
# Process documents in batch
documents = load_documents()  # Load many documents

for batch in chunks(documents, size=100):
    for doc in batch:
        kg.process_text(
            text=doc['content'],
            document_id=doc['id'],
            metadata=doc['metadata']
        )
    
    # Optional: Periodic commit for large batches
    # session.commit()
```

### Query Optimization

```python
# Use EXPLAIN to analyze queries
with store.driver.session() as session:
    result = session.run("""
        EXPLAIN
        MATCH (p:Person)-[r:WORKS_FOR]->(o:Organization)
        WHERE o.name = 'Apple'
        RETURN p.name
    """)
    
    print(result.plan())

# Use PROFILE for execution stats
result = session.run("""
    PROFILE
    MATCH (p:Person)-[r:WORKS_FOR]->(o:Organization)
    WHERE o.name = 'Apple'
    RETURN p.name
""")
```

## Monitoring

### Graph Statistics

```python
# Get overall statistics
stats = store.get_statistics()

print("Nodes by type:")
for node_type, count in stats['nodes_by_type'].items():
    print(f"  {node_type}: {count}")

print("\nRelationships by type:")
for rel_type, count in stats['relationships_by_type'].items():
    print(f"  {rel_type}: {count}")
```

### Entity Extraction Metrics

```python
# Track extraction performance
import time

start = time.time()
entities = extractor.extract(text)
elapsed = time.time() - start

print(f"Extracted {len(entities)} entities in {elapsed*1000:.2f}ms")
print(f"Average: {elapsed/len(entities)*1000:.2f}ms per entity")
```

## Troubleshooting

### Connection Issues

```python
try:
    store = Neo4jStore(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password"
    )
except Exception as e:
    print(f"Connection failed: {e}")
    print("\nTroubleshooting:")
    print("1. Check Neo4j is running: docker ps | grep neo4j")
    print("2. Verify credentials")
    print("3. Check port 7687 is accessible")
```

### Spacy Model Issues

```bash
# Download model if missing
python -m spacy download en_core_web_sm

# Or use larger model for better accuracy
python -m spacy download en_core_web_lg
```

### Memory Issues

```python
# Process in smaller batches
for batch in chunks(large_text_list, size=10):
    results = extractor.extract_batch(batch)
    process_results(results)
    
    # Clear cache periodically
    gc.collect()
```

## Examples

See complete working examples in `examples/`:

- `knowledge_graph_example.py` - Entity extraction and graph building
- `graph_search_example.py` - Graph-based retrieval
- `complete_hybrid_example.py` - Full hybrid search

```bash
python examples/knowledge_graph_example.py
python examples/graph_search_example.py
```

## Best Practices

1. **Entity ID Generation**: Use consistent ID generation for deduplication
2. **Relationship Confidence**: Filter by confidence threshold
3. **Batch Processing**: Process large datasets in batches
4. **Index Strategy**: Create indexes for frequently queried properties
5. **Query Optimization**: Use EXPLAIN/PROFILE for complex queries
6. **Memory Management**: Clear caches for long-running processes
7. **Error Handling**: Implement retry logic for transient failures

## References

- [Neo4j Documentation](https://neo4j.com/docs/)
- [spaCy Documentation](https://spacy.io/)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/)
- [Graph Data Science Library](https://neo4j.com/docs/graph-data-science/)