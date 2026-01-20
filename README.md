# Multi-Layer Context Foundation

A sophisticated Python system for managing conversational context across multiple storage layers with intelligent retrieval strategies.

## 🌟 Features

### Multi-Layer Architecture
- **Immediate Context Buffer**: High-speed FIFO buffer for hot, frequently accessed context
  - Configurable TTL for automatic expiration
  - Token budget management
  - Fast lookup with O(1) access

- **Session Memory**: LRU-based mid-term storage for conversation history
  - Automatic consolidation of older items
  - Relevance tracking and decay
  - Conversation and task grouping
  - Smart eviction based on access patterns

- **Long-Term Store**: Persistent storage for important context
  - Cross-session persistence
  - Importance-based retention
  - Scalable storage backend (extensible)

### Advanced Retrieval

- **Hybrid Retrieval Engine**: Combines multiple search strategies
  - Semantic similarity search (vector-based)
  - BM25 keyword search with proper IDF calculation
  - Graph-based context traversal
  - Intelligent result fusion and normalization

- **BM25 Keyword Search**
  - Industry-standard ranking algorithm
  - Document length normalization
  - Configurable k1 and b parameters
  - Efficient inverted index

- **Adaptive Chunking System**
  - Preserves sentence and paragraph boundaries
  - Intelligent overlap calculation
  - Configurable chunk sizes
  - Metadata preservation

### Performance & Monitoring

- Query result caching with TTL
- Comprehensive metrics tracking
- Layer-specific statistics
- Cache hit/miss monitoring
- Automatic performance optimization

## 📦 Installation

### Prerequisites
- Python 3.8+
- PostgreSQL with pgvector extension (for production deployment)

### Setup

```bash
# Clone the repository
git clone https://github.com/Dpdpdpdp0987/multi-layer-context-foundation.git
cd multi-layer-context-foundation

# Install dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
```

### Dependencies

```txt
# requirements.txt
numpy>=1.20.0
asyncio-extras>=1.3.2

# requirements-dev.txt (for testing)
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
```

## 🚀 Quick Start

### Basic Usage

```python
import asyncio
from context_foundation.orchestrator import ContextOrchestrator

async def main():
    # Initialize the orchestrator
    orchestrator = ContextOrchestrator()
    
    # Add context
    context_id = await orchestrator.add_context(
        content="User prefers Python for backend development.",
        metadata={
            "type": "preference",
            "importance": 0.8
        }
    )
    
    # Retrieve relevant context
    results = await orchestrator.get_context(
        query="What programming language does the user like?",
        max_results=5
    )
    
    for result in results:
        print(f"Score: {result['score']:.3f}")
        print(f"Content: {result['content']}")
        print(f"Layer: {result['layer']}\n")

asyncio.run(main())
```

### Session Management

```python
async def session_example():
    orchestrator = ContextOrchestrator()
    session_id = "user_123"
    
    # Add conversation turns
    await orchestrator.add_context(
        content="I'm working on a database migration.",
        metadata={"session_id": session_id, "turn": 0}
    )
    
    await orchestrator.add_context(
        content="Moving from MySQL to PostgreSQL.",
        metadata={"session_id": session_id, "turn": 1}
    )
    
    # Retrieve session-specific context
    results = await orchestrator.get_context(
        query="database migration details",
        filters={"session_id": session_id}
    )
```

### Working with Specific Layers

```python
from context_foundation.layers.immediate import ImmediateContextBuffer
from context_foundation.layers.session import SessionMemory

async def layer_example():
    # Immediate buffer for hot context
    immediate = ImmediateContextBuffer(
        max_size=10,
        ttl_seconds=300  # 5 minutes
    )
    
    await immediate.add_item(
        content="Current task: implementing authentication",
        metadata={"priority": "high"}
    )
    
    # Session memory for conversation history
    session = SessionMemory(
        max_size=50,
        consolidation_threshold=20
    )
    
    await session.add_item(
        content="User asked about OAuth2 implementation",
        metadata={"session_id": "auth_conv"}
    )
```

### BM25 Keyword Search

```python
from context_foundation.search.bm25 import BM25Search

async def bm25_example():
    bm25 = BM25Search(k1=1.5, b=0.75)
    
    # Index documents
    await bm25.index_document(
        doc_id="doc1",
        content="Python is great for web development",
        metadata={"category": "programming"}
    )
    
    # Search
    results = await bm25.search("Python web", top_k=5)
    for result in results:
        print(f"{result['content']} (score: {result['score']:.3f})")
```

### Adaptive Chunking

```python
from context_foundation.search.chunking import AdaptiveChunker

async def chunking_example():
    chunker = AdaptiveChunker(
        target_chunk_size=200,
        min_chunk_size=100,
        max_chunk_size=300
    )
    
    long_text = "Your long document here..."
    
    chunks = await chunker.chunk_text(
        text=long_text,
        metadata={"source": "documentation"}
    )
    
    for chunk in chunks:
        print(f"Chunk: {chunk['content'][:50]}...")
        print(f"Size: {chunk['chunk_size']}, Overlap: {chunk['overlap_size']}")
```

## 🏗️ Architecture

### Layer Hierarchy

```
┌─────────────────────────────────────┐
│     Context Orchestrator            │
│  (Coordinates all layers)           │
└─────────────┬───────────────────────┘
              │
    ┌─────────┴─────────┬──────────────┐
    │                   │              │
┌───▼────────┐  ┌──────▼──────┐  ┌───▼──────────┐
│ Immediate  │  │  Session    │  │  Long-term   │
│  Buffer    │  │  Memory     │  │    Store     │
│ (FIFO/TTL) │  │   (LRU)     │  │ (Persistent) │
└────────────┘  └─────────────┘  └──────────────┘
```

### Data Flow

1. **Write Path**
   - Context arrives at orchestrator
   - Orchestrator determines appropriate layer(s)
   - Item stored with metadata and embeddings
   - Indices updated (BM25, vector, graph)

2. **Read Path**
   - Query arrives at orchestrator
   - Check cache for recent identical queries
   - Query all relevant layers in parallel
   - Apply hybrid retrieval (semantic + keyword + graph)
   - Fuse and normalize results
   - Return ranked results

### Retrieval Strategies

The system supports multiple retrieval strategies that can be combined:

1. **Semantic Search**: Vector similarity using embeddings
2. **Keyword Search**: BM25 ranking for exact term matching
3. **Graph Traversal**: Following context relationships
4. **Hybrid Fusion**: Weighted combination of all strategies

## 📊 Configuration

### Orchestrator Configuration

```python
orchestrator = ContextOrchestrator(
    cache_ttl=300,              # Cache results for 5 minutes
    default_max_results=10       # Default number of results
)
```

### Layer Configuration

```python
# Immediate Buffer
immediate = ImmediateContextBuffer(
    max_size=20,                 # Maximum number of items
    ttl_seconds=600,             # 10 minutes TTL
    max_tokens=4000              # Token budget limit
)

# Session Memory
session = SessionMemory(
    max_size=100,                # Maximum items before eviction
    consolidation_threshold=50,  # Consolidate when this many items
    relevance_decay=0.1          # Relevance decay per consolidation
)

# Long-term Store
longterm = LongTermStore(
    persistence_threshold=0.7,   # Minimum importance to persist
    max_items=10000              # Maximum stored items
)
```

### Search Configuration

```python
# BM25 Parameters
bm25 = BM25Search(
    k1=1.5,    # Term frequency saturation
    b=0.75     # Length normalization
)

# Chunking Parameters
chunker = AdaptiveChunker(
    target_chunk_size=500,     # Target characters per chunk
    min_chunk_size=200,        # Minimum chunk size
    max_chunk_size=1000,       # Maximum chunk size
    overlap_ratio=0.1          # 10% overlap between chunks
)

# Hybrid Retrieval Weights
hybrid = HybridRetrieval(
    semantic_weight=0.5,       # Weight for vector search
    keyword_weight=0.3,        # Weight for BM25 search
    graph_weight=0.2           # Weight for graph traversal
)
```

## 📈 Monitoring & Metrics

### Getting System Metrics

```python
metrics = orchestrator.get_metrics()

print(f"Total items: {metrics['total_items']}")
print(f"Cache hit rate: {metrics['cache_hits'] / (metrics['cache_hits'] + metrics['cache_misses']):.1%}")
print(f"Avg results per query: {metrics['avg_results_per_query']:.2f}")

# Layer-specific metrics
print(f"Immediate buffer size: {metrics['immediate_buffer']['size']}")
print(f"Session memory size: {metrics['session_memory']['size']}")
print(f"Consolidations: {metrics['session_memory']['consolidation_count']}")
```

### Performance Monitoring

The system tracks:
- Query latency
- Cache hit/miss ratio
- Layer distribution of results
- Consolidation frequency
- Memory usage per layer
- Retrieval strategy effectiveness

## 🧪 Testing

### Run All Tests

```bash
# Run test suite
pytest

# With coverage
pytest --cov=context_foundation --cov-report=html

# Run specific test file
pytest tests/test_orchestrator.py

# Run with verbose output
pytest -v
```

### Test Coverage

The project includes comprehensive tests for:
- ✅ Context Orchestrator coordination
- ✅ Immediate Buffer FIFO and TTL
- ✅ Session Memory LRU and consolidation
- ✅ BM25 keyword search
- ✅ Adaptive chunking
- ✅ Hybrid retrieval fusion
- ✅ Caching mechanisms
- ✅ Metrics tracking

## 📝 Examples

See the `examples/` directory for complete working examples:

- `basic_usage.py`: Core functionality demonstration
- More examples coming soon...

Run examples:

```bash
python examples/basic_usage.py
```

## 🛠️ Development

### Project Structure

```
multi-layer-context-foundation/
├── context_foundation/
│   ├── __init__.py
│   ├── orchestrator.py          # Main orchestrator
│   ├── layers/
│   │   ├── __init__.py
│   │   ├── immediate.py         # Immediate buffer
│   │   ├── session.py           # Session memory
│   │   └── longterm.py          # Long-term store
│   └── search/
│       ├── __init__.py
│       ├── bm25.py              # BM25 keyword search
│       ├── chunking.py          # Adaptive chunking
│       └── hybrid.py            # Hybrid retrieval
├── tests/
│   ├── test_orchestrator.py
│   ├── test_immediate.py
│   ├── test_session.py
│   ├── test_bm25.py
│   ├── test_chunking.py
│   └── test_hybrid.py
├── examples/
│   └── basic_usage.py
├── README.md
└── requirements.txt
```

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for all public methods
- Maintain test coverage above 80%

## 🔮 Roadmap

### Planned Features

- [ ] PostgreSQL + pgvector integration for production deployment
- [ ] GraphQL API for external access
- [ ] Real-time context streaming
- [ ] Advanced consolidation strategies
- [ ] Context versioning and rollback
- [ ] Multi-modal context support (images, audio)
- [ ] Distributed deployment support
- [ ] Context sharing across sessions
- [ ] Advanced privacy controls
- [ ] Plugin system for custom layers

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

Built with ❤️ by Daniela Mümken

Key technologies:
- Python asyncio for high-performance async operations
- BM25 algorithm for keyword search
- Vector embeddings for semantic search
- LRU/FIFO caching strategies

## 📞 Support

For questions, issues, or suggestions:
- Open an issue on GitHub
- Contact: [Your contact information]

---

**Note**: This is an active development project. APIs may change as new features are added and the system evolves.
