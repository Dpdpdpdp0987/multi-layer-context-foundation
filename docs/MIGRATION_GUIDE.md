# Migration Guide - Vector Search Integration

## Overview

This guide helps you upgrade your Multi-Layer Context Foundation installation to include the new vector search capabilities.

## What's New

### ✅ **Implemented Features**

1. **Qdrant Vector Store** - High-performance vector database
2. **PostgreSQL with pgvector** - SQL-based vector search
3. **Supabase Integration** - Managed PostgreSQL with vectors
4. **Sentence Transformers** - Embedding generation
5. **Semantic Search** - Vector similarity search
6. **Hybrid Retrieval** - Combined semantic + keyword search
7. **Batch Operations** - Efficient bulk indexing

### 📦 **New Dependencies**

- `qdrant-client>=1.7.0`
- `sentence-transformers>=2.2.0`
- `psycopg2-binary>=2.9.9`
- `supabase>=2.0.0`

## Step-by-Step Migration

### 1. Update Dependencies

```bash
# Update requirements
pip install --upgrade -r requirements.txt

# Or install new dependencies individually
pip install qdrant-client sentence-transformers psycopg2-binary supabase
```

### 2. Start Vector Database

Choose one option:

**Option A: Qdrant (Recommended)**

```bash
# Update docker-compose.yml (already updated)
docker-compose up -d qdrant

# Verify
curl http://localhost:6333/
```

**Option B: PostgreSQL with pgvector**

```bash
docker-compose up -d postgres

# The pgvector extension is enabled automatically
```

**Option C: Use Supabase**

- Create project at supabase.com
- Enable pgvector in SQL Editor
- Get credentials

### 3. Update Configuration

Create or update `config/vector_config.yaml`:

```yaml
vector_store:
  provider: "qdrant"
  
  qdrant:
    host: "localhost"
    port: 6333
    collection_name: "mlcf_vectors"

embeddings:
  model: "sentence-transformers/all-MiniLM-L6-v2"
  dimension: 384
  device: "cpu"
```

### 4. Update Your Code

#### Before (No Vector Search)

```python
from mlcf import ContextOrchestrator

orchestrator = ContextOrchestrator()
orchestrator.add_context("Content here")
results = orchestrator.retrieve_context("query")
```

#### After (With Vector Search)

```python
from mlcf import ContextOrchestrator
from mlcf.memory.persistent_memory import PersistentMemory

# Initialize with vector store
orchestrator = ContextOrchestrator()

# Enable persistent memory with vectors
orchestrator.persistent_memory = PersistentMemory(
    vector_store_type="qdrant",
    qdrant_config={
        "host": "localhost",
        "port": 6333
    }
)

# Same API - now with semantic search!
orchestrator.add_context("Content here")
results = orchestrator.retrieve_context("query")
```

### 5. Use Direct Vector Search (Optional)

For direct vector search without orchestrator:

```python
from mlcf.storage.vector_store import QdrantVectorStore

# Initialize
vector_store = QdrantVectorStore(
    collection_name="my_docs",
    host="localhost",
    port=6333
)

# Add documents
vector_store.add(
    doc_id="doc1",
    content="Machine learning content",
    metadata={"category": "AI"}
)

# Search
results = vector_store.search(
    query="machine learning",
    max_results=5
)
```

### 6. Use Hybrid Search (Recommended)

```python
from mlcf.retrieval.hybrid_engine import HybridRetrievalEngine
from mlcf.storage.vector_store import QdrantVectorStore

# Setup
vector_store = QdrantVectorStore(
    collection_name="hybrid_search",
    host="localhost",
    port=6333
)

engine = HybridRetrievalEngine(
    config={
        "semantic_weight": 0.6,
        "keyword_weight": 0.4
    },
    vector_store=vector_store
)

# Index
engine.index_document(
    doc_id="doc1",
    content="Your content",
    index_in_vector_store=True
)

# Search (combines BM25 + vector search)
results = engine.retrieve(
    query="your query",
    strategy="hybrid"
)
```

## Database-Specific Migration

### From No Database to Qdrant

1. Install Qdrant:
```bash
docker-compose up -d qdrant
```

2. Create index:
```python
from mlcf.storage.vector_store import QdrantVectorStore

store = QdrantVectorStore()
# Collection created automatically
```

3. Migrate existing data:
```python
# If you have existing context items
for item in existing_items:
    store.add(item.id, item.content, item.metadata)
```

### From In-Memory to PostgreSQL

1. Start PostgreSQL:
```bash
docker-compose up -d postgres
```

2. Use PostgreSQL vector store:
```python
from mlcf.storage.postgres_vector import PostgresVectorStore

store = PostgresVectorStore(
    connection_string="postgresql://mlcf:mlcf_password@localhost:5432/mlcf",
    table_name="context_vectors"
)

# Table created automatically with pgvector
```

### To Supabase

1. Setup Supabase project
2. Run SQL:
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE context_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(384),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON context_items USING ivfflat (embedding vector_cosine_ops);
```

3. Use Supabase store:
```python
from mlcf.storage.supabase_store import SupabaseStore

store = SupabaseStore(
    url="https://your-project.supabase.co",
    key="your-anon-key"
)
```

## Testing Your Migration

### 1. Run Tests

```bash
# Test vector store
pytest tests/test_vector_store.py -v

# Test embeddings
pytest tests/test_embeddings.py -v

# Test semantic search
pytest tests/test_semantic_search.py -v
```

### 2. Run Examples

```bash
# Basic vector search
python examples/vector_search_example.py

# Hybrid search
python examples/hybrid_search_example.py
```

### 3. Verify Performance

```python
import time
from mlcf.storage.vector_store import QdrantVectorStore

store = QdrantVectorStore()

# Add test data
start = time.time()
store.add_batch([
    (f"doc{i}", f"Test content {i}", {})
    for i in range(1000)
])
print(f"Indexed 1000 docs in {time.time()-start:.2f}s")

# Test search
start = time.time()
results = store.search("test query", max_results=10)
print(f"Search took {(time.time()-start)*1000:.2f}ms")
```

## Breaking Changes

### None!

The vector search integration is **fully backward compatible**. Your existing code will continue to work without modifications.

### Optional Enhancements

To leverage new features:

1. **Add persistent memory** to orchestrator
2. **Enable semantic search** in hybrid engine
3. **Use vector store directly** for advanced use cases

## Performance Considerations

### Before (Keyword-only)

- Search: 10-50ms for 10K documents
- Storage: In-memory only
- Scalability: Limited by RAM

### After (With Vectors)

- Search: 50-200ms for 1M+ documents
- Storage: Persistent with backups
- Scalability: Horizontal scaling supported

### Optimization Tips

1. **Use GPU for embeddings** (10x faster)
```python
generator = EmbeddingGenerator(device="cuda")
```

2. **Batch operations** (5x faster)
```python
store.add_batch(documents)  # vs individual adds
```

3. **Adjust chunk size**
```python
chunker = AdaptiveChunker(chunk_size=256)  # smaller = faster
```

## Rollback Plan

If you need to rollback:

1. **Stop vector database**:
```bash
docker-compose stop qdrant postgres
```

2. **Remove new dependencies**:
```bash
pip uninstall qdrant-client sentence-transformers psycopg2-binary supabase
```

3. **Use previous version**:
```bash
git checkout <previous-commit>
pip install -r requirements.txt
```

## Support

### Common Issues

**Issue**: "Qdrant connection refused"
```bash
# Solution
docker-compose restart qdrant
# or
docker-compose up -d qdrant
```

**Issue**: "Out of memory during embedding"
```python
# Solution: Reduce batch size
generator = EmbeddingGenerator(batch_size=16)
```

**Issue**: "Slow search performance"
```python
# Solution: Increase score threshold
results = store.search(query, score_threshold=0.7)
```

### Getting Help

- Documentation: `docs/VECTOR_SEARCH.md`
- Examples: `examples/vector_search_example.py`
- Issues: https://github.com/Dpdpdpdp0987/multi-layer-context-foundation/issues

## Next Steps

1. ✅ Complete migration
2. 📖 Read `docs/VECTOR_SEARCH.md`
3. 🧪 Run examples
4. 🚀 Enable hybrid search in production
5. 📊 Monitor performance

Congratulations! Your system now has semantic search capabilities! 🎉
