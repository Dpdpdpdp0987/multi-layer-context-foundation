# Implementation Guide - Multi-Layer Context Foundation

## Overview

This document provides details about the implemented components of the Multi-Layer Context Foundation system.

## Implemented Components

### ✅ Core Components

#### 1. Context Orchestrator (`mlcf/core/orchestrator.py`)

The central coordinator for multi-layer context management.

**Features:**
- Intelligent layer routing (immediate/session/persistent)
- Context budget management with token tracking
- Multi-layer retrieval with result fusion
- Time-based relevance decay
- Automatic context promotion based on access patterns
- Priority-based context management

**Key Classes:**
- `ContextOrchestrator`: Main orchestration class
- `ContextItem`: Unified context representation
- `ContextType`: Enumeration of context types
- `ContextPriority`: Priority levels for context items

**Usage:**
```python
from mlcf import ContextOrchestrator, ContextType

orchestrator = ContextOrchestrator()
orchestrator.start_new_session()

# Add context
orchestrator.add_context(
    "User prefers Python",
    context_type=ContextType.PREFERENCE
)

# Retrieve
results = orchestrator.retrieve_context("programming language")
```

#### 2. Immediate Context Buffer (`mlcf/memory/immediate_buffer.py`)

High-speed in-memory buffer for recent context.

**Features:**
- Circular buffer with automatic eviction
- Token budget management
- Recency-based retrieval bias
- Fast O(1) append operations

**Characteristics:**
- Max items: Configurable (default: 10)
- Max tokens: Configurable (default: 2048)
- Eviction: FIFO when token budget exceeded
- Search: Keyword matching with recency boost

#### 3. Session Memory (`mlcf/memory/session_memory.py`)

Working memory with LRU eviction and relevance tracking.

**Features:**
- LRU (Least Recently Used) eviction policy
- Relevance-based filtering
- Multi-session support
- Automatic session cleanup
- Thread-safe operations

**Characteristics:**
- Max items per session: Configurable (default: 50)
- Relevance threshold: 0.7
- Session timeout: 2 hours (configurable)
- Metadata filtering support

### ✅ Retrieval Components

#### 4. BM25 Keyword Search (`mlcf/retrieval/bm25_search.py`)

Probabilistic ranking for keyword-based retrieval.

**Features:**
- Standard BM25 algorithm implementation
- Inverted index for fast lookup
- IDF (Inverse Document Frequency) caching
- Document length normalization
- Metadata filtering

**Parameters:**
- k1: 1.5 (term frequency saturation)
- b: 0.75 (length normalization)
- epsilon: 0.25 (IDF floor value)

**Algorithm:**
```
BM25(q, d) = Σ IDF(qi) * [(f(qi, d) * (k1 + 1)) / 
             (f(qi, d) + k1 * (1 - b + b * |d| / avgdl))]
```

**Performance:**
- Indexing: O(n) per document
- Search: O(k * m) where k = query terms, m = matching docs

#### 5. Adaptive Chunking (`mlcf/retrieval/adaptive_chunking.py`)

Intelligent document chunking with context preservation.

**Features:**
- Sentence boundary preservation
- Paragraph-aware chunking
- Adaptive overlap calculation
- Content-aware chunk sizing
- Metadata propagation

**Algorithm:**
1. Detect structural boundaries (paragraphs, sentences)
2. Find optimal chunk boundaries near target size
3. Calculate adaptive overlap based on content density
4. Create overlapping chunks with metadata

**Parameters:**
- chunk_size: 512 characters (target)
- min_chunk_size: 100 characters
- max_chunk_size: 1024 characters
- base_overlap: 50 characters
- adaptive_overlap: true

**Overlap Strategy:**
- Few sentences (<= 2): 50% base overlap
- Medium sentences (3-5): 100% base overlap
- Many sentences (> 5): 150% base overlap
- Maximum: 1/3 of chunk size or 200 chars

#### 6. Hybrid Retrieval Engine (`mlcf/retrieval/hybrid_engine.py`)

Combines semantic, keyword, and graph search.

**Features:**
- Multi-strategy retrieval (semantic, keyword, graph)
- Weighted result fusion
- Score normalization
- Automatic chunking integration
- Reranking support (placeholder)

**Strategy Weights:**
- Semantic: 0.5
- Keyword: 0.3
- Graph: 0.2

**Fusion Algorithm:**
1. Retrieve from each strategy (2x max_results)
2. Normalize scores to [0, 1]
3. Apply weighted fusion
4. Deduplicate and sort
5. Optional reranking
6. Return top-k results

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  ContextOrchestrator                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Layer Routing & Budget Management              │   │
│  └─────────────────────────────────────────────────┘   │
└───────┬─────────────────┬─────────────────┬───────────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐  ┌──────────────┐  ┌──────────────┐
│   Immediate   │  │   Session    │  │  Persistent  │
│    Buffer     │  │   Memory     │  │    Memory    │
│   (Circular)  │  │    (LRU)     │  │ (Vec+Graph)  │
└───────────────┘  └──────────────┘  └──────────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ HybridRetrievalEngine│
                ├──────────────────────┤
                │  ┌────────────────┐  │
                │  │  BM25 Search   │  │
                │  ├────────────────┤  │
                │  │ Vector Search  │  │ (TODO)
                │  ├────────────────┤  │
                │  │ Graph Search   │  │ (TODO)
                │  └────────────────┘  │
                └──────────────────────┘
```

## Testing

All implemented components have comprehensive test coverage:

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=mlcf tests/

# Run specific component tests
pytest tests/test_orchestrator.py -v
pytest tests/test_bm25_search.py -v
pytest tests/test_adaptive_chunking.py -v
```

**Test Coverage:**
- `test_orchestrator.py`: 15+ tests
- `test_immediate_buffer.py`: 10+ tests
- `test_session_memory.py`: 12+ tests
- `test_bm25_search.py`: 12+ tests
- `test_adaptive_chunking.py`: 8+ tests

## Usage Examples

See `examples/basic_usage.py` for a comprehensive demonstration:

```bash
python examples/basic_usage.py
```

## Performance Characteristics

| Component | Operation | Time Complexity | Space Complexity |
|-----------|-----------|-----------------|------------------|
| Immediate Buffer | Add | O(1) | O(n) |
| Immediate Buffer | Search | O(n) | O(1) |
| Session Memory | Add | O(1) | O(n) |
| Session Memory | Search | O(n) | O(1) |
| BM25 | Index | O(m) | O(v) |
| BM25 | Search | O(k*d) | O(d) |
| Chunker | Chunk | O(n) | O(c) |

*n = items, m = doc length, v = vocabulary, k = query terms, d = matching docs, c = chunks*

## TODO: Remaining Implementation

### High Priority

1. **Vector Search Integration**
   - Qdrant client implementation
   - Embedding generation pipeline
   - Semantic similarity search

2. **Graph Database Integration**
   - Neo4j client implementation
   - Entity extraction
   - Relationship mapping

3. **Cross-Encoder Reranking**
   - Model loading and inference
   - Batch reranking
   - Score calibration

### Medium Priority

4. **Persistent Storage**
   - Document persistence
   - State serialization
   - Database migrations

5. **MCP Server**
   - Server implementation
   - API endpoints
   - WebSocket support

6. **Advanced Features**
   - Conflict resolution
   - Version tracking
   - Multi-modal support

## Configuration

All components are configurable via `Config` class:

```python
from mlcf import Config

config = Config(
    short_term_max_size=10,
    working_memory_max_size=50,
    retrieval_config={
        "semantic_weight": 0.5,
        "keyword_weight": 0.3,
        "graph_weight": 0.2
    }
)
```

Or via YAML:

```yaml
memory:
  short_term:
    max_size: 10
  working:
    max_size: 50

retrieval:
  weights:
    semantic: 0.5
    keyword: 0.3
    graph: 0.2
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.