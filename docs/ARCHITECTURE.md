# Architecture Documentation

## System Overview

The Multi-Layer Context Foundation (MLCF) is designed as a modular, scalable system for managing AI assistant context across multiple memory layers with hybrid retrieval capabilities.

## Core Components

### 1. Memory Architecture

#### Short-Term Memory
- **Purpose**: Store recent conversation context
- **Implementation**: FIFO queue (deque)
- **Capacity**: 5-10 entries
- **Retention**: Session-based, cleared on session end
- **Use Case**: Immediate conversational coherence

#### Working Memory
- **Purpose**: Active task and session context
- **Implementation**: LRU cache with relevance scoring
- **Capacity**: 30-50 entries
- **Retention**: Task-based, cleared when task completes
- **Use Case**: Multi-turn task execution

#### Long-Term Memory
- **Purpose**: Persistent knowledge storage
- **Implementation**: Dual storage (Vector DB + Graph DB)
- **Capacity**: Unlimited
- **Retention**: Permanent with versioning
- **Use Case**: Facts, preferences, learned patterns

### 2. Retrieval System

#### Semantic Search (Vector-based)
```python
# Uses embeddings for semantic similarity
Query: "What programming language do I prefer?"
Vector: [0.12, -0.34, 0.56, ...]  # 384-dim
Similarity: Cosine distance
```

#### Keyword Search (BM25)
```python
# Traditional IR ranking
Terms: ["programming", "language", "prefer"]
Scoring: TF-IDF weighted with document length normalization
```

#### Graph Traversal
```cypher
// Neo4j example
MATCH (u:User)-[:PREFERS]->(l:Language)
WHERE u.id = $user_id
RETURN l.name
```

#### Hybrid Fusion
```python
final_score = (
    0.5 * semantic_score +
    0.3 * keyword_score +
    0.2 * graph_score
)
```

### 3. Data Flow

```
User Query
    ↓
Context Manager
    ↓
    ├──> Short-Term Memory (recent context)
    ├──> Working Memory (active tasks)
    └──> Long-Term Memory
            ↓
        Hybrid Retriever
            ├──> Vector Search
            ├──> Keyword Search
            └──> Graph Traversal
                ↓
            Result Fusion
                ↓
            Reranking (optional)
                ↓
            Final Results
```

## Storage Layer

### Vector Database Options

1. **Qdrant** (Recommended)
   - Native vector operations
   - HNSW indexing
   - Metadata filtering
   - Distributed support

2. **Chroma**
   - Simple setup
   - Good for development
   - Embedded mode

3. **Milvus**
   - High performance
   - Production-grade
   - Complex setup

### Graph Database Options

1. **Neo4j** (Recommended)
   - Mature ecosystem
   - Cypher query language
   - Rich relationship modeling

2. **LibSQL**
   - Lightweight
   - SQLite-compatible
   - Edge computing friendly

## Scalability Considerations

### Horizontal Scaling
- **Vector DB**: Sharding by user/tenant
- **Graph DB**: Partitioning by entity type
- **API Layer**: Stateless design for load balancing

### Performance Optimization
- **Caching**: Redis for frequent queries
- **Batch Processing**: Async embedding generation
- **Index Optimization**: Regular HNSW graph rebuilding

### Resource Management
- **Memory**: Lazy loading of models
- **Disk**: Tiered storage (SSD for hot data)
- **Network**: Connection pooling

## Security & Privacy

### Data Isolation
- Multi-tenancy support
- User-level access controls
- Encrypted at rest

### PII Handling
- Automatic detection
- Redaction capabilities
- Audit logging

## Extension Points

### Custom Memory Layers
```python
class CustomMemory(BaseMemory):
    def add(self, content, metadata):
        # Custom implementation
        pass
```

### Custom Retrieval Strategies
```python
class CustomRetriever:
    def retrieve(self, query, **kwargs):
        # Custom implementation
        return results
```

### Plugin System
- Pre-processing hooks
- Post-processing filters
- Custom scorers

## Monitoring & Observability

### Metrics
- Query latency (p50, p95, p99)
- Retrieval accuracy
- Memory usage
- Cache hit rates

### Logging
- Structured logging (JSON)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Correlation IDs for tracing

### Alerts
- High latency
- Storage capacity
- Error rates

## Future Enhancements

1. **Multi-modal Support**
   - Image embeddings
   - Audio transcription
   - Video understanding

2. **Advanced Reasoning**
   - Chain-of-thought tracking
   - Inference graphs
   - Contradiction detection

3. **Federated Learning**
   - Privacy-preserving updates
   - Distributed training
   - Model personalization