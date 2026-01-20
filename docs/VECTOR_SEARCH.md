# Vector Search Integration

## Overview

The Multi-Layer Context Foundation now includes full vector search capabilities through:

- **Qdrant** - High-performance vector database
- **PostgreSQL with pgvector** - Vector search in SQL
- **Supabase** - Managed PostgreSQL with vector support
- **Sentence Transformers** - State-of-the-art embeddings

## Setup

### 1. Install Dependencies

```bash
pip install qdrant-client sentence-transformers psycopg2-binary supabase
```

### 2. Start Vector Database

**Option A: Qdrant (Recommended)**

```bash
# Start Qdrant with Docker
docker-compose up -d qdrant

# Verify it's running
curl http://localhost:6333/
```

**Option B: PostgreSQL with pgvector**

```bash
# Start PostgreSQL with pgvector
docker-compose up -d postgres

# The pgvector extension is automatically enabled
```

**Option C: Supabase**

1. Create a project at [supabase.com](https://supabase.com)
2. Enable pgvector extension in SQL Editor:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Get your project URL and API key

### 3. Configure

Edit `config/vector_config.yaml`:

```yaml
vector_store:
  provider: "qdrant"  # or "postgres" or "supabase"
  
  qdrant:
    host: "localhost"
    port: 6333
    collection_name: "mlcf_vectors"
```

## Usage

### Basic Vector Search

```python
from mlcf.storage.vector_store import QdrantVectorStore
from mlcf.embeddings.embedding_generator import EmbeddingGenerator

# Initialize
vector_store = QdrantVectorStore(
    collection_name="my_collection",
    host="localhost",
    port=6333
)

# Add documents
vector_store.add(
    doc_id="doc1",
    content="Machine learning with Python",
    metadata={"category": "AI"}
)

# Search
results = vector_store.search(
    query="Python AI programming",
    max_results=5,
    score_threshold=0.5
)

for result in results:
    print(f"{result.id}: {result.score:.3f} - {result.content}")
```

### Batch Operations

```python
# Batch add for efficiency
documents = [
    ("doc1", "Python ML", {"lang": "python"}),
    ("doc2", "Java enterprise", {"lang": "java"}),
    ("doc3", "Python web dev", {"lang": "python"})
]

vector_store.add_batch(documents)
```

### Search with Filters

```python
results = vector_store.search(
    query="programming",
    filters={"lang": "python"},
    max_results=10
)
```

### Semantic Search

```python
from mlcf.retrieval.semantic_search import SemanticSearch

semantic = SemanticSearch(vector_store=vector_store)

results = semantic.search(
    query="machine learning algorithms",
    max_results=5
)
```

### Hybrid Search (Semantic + Keyword)

```python
from mlcf.retrieval.hybrid_engine import HybridRetrievalEngine

engine = HybridRetrievalEngine(
    config={
        "semantic_weight": 0.6,
        "keyword_weight": 0.4
    },
    vector_store=vector_store
)

# Index documents
engine.index_document(
    doc_id="doc1",
    content="Python is great for ML",
    index_in_vector_store=True
)

# Hybrid search
results = engine.retrieve(
    query="machine learning",
    strategy="hybrid"
)
```

## Embedding Models

### Available Models

| Model | Dimension | Speed | Quality | Use Case |
|-------|-----------|-------|---------|----------|
| all-MiniLM-L6-v2 | 384 | Fast | Good | Default, general purpose |
| all-mpnet-base-v2 | 768 | Medium | Excellent | High quality |
| paraphrase-multilingual-MiniLM-L12-v2 | 384 | Fast | Good | Multilingual |

### Change Model

```python
from mlcf.embeddings.embedding_generator import EmbeddingGenerator

generator = EmbeddingGenerator(
    model_name="sentence-transformers/all-mpnet-base-v2",
    device="cpu"  # or "cuda" for GPU
)
```

## PostgreSQL with pgvector

### Setup

```python
from mlcf.storage.postgres_vector import PostgresVectorStore

store = PostgresVectorStore(
    connection_string="postgresql://user:pass@localhost:5432/mlcf",
    table_name="context_vectors",
    embedding_dim=384
)

# Use same API as Qdrant
store.add("doc1", "Content here", {"meta": "data"})
results = store.search("query")
```

### Supabase

```python
from mlcf.storage.supabase_store import SupabaseStore

store = SupabaseStore(
    url="https://your-project.supabase.co",
    key="your-anon-key",
    table_name="context_items"
)

# Same API
store.add("doc1", "Content", {})
results = store.search_by_vector("query")
```

## Performance Tips

### 1. Batch Operations

```python
# Instead of:
for doc in documents:
    vector_store.add(doc.id, doc.content)

# Do:
vector_store.add_batch([
    (doc.id, doc.content, doc.metadata)
    for doc in documents
])
```

### 2. Use GPU for Embeddings

```python
generator = EmbeddingGenerator(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    device="cuda"  # Requires CUDA
)
```

### 3. Index Configuration

For Qdrant, create HNSW index:

```python
# Configured automatically with optimal parameters
# M=16, ef_construct=100 for good speed/quality tradeoff
```

### 4. Score Thresholds

```python
# Filter low-quality matches
results = vector_store.search(
    query="query",
    score_threshold=0.7  # Only high-confidence matches
)
```

## Monitoring

### Collection Statistics

```python
info = vector_store.get_collection_info()
print(f"Vectors: {info['vectors_count']}")
print(f"Points: {info['points_count']}")
```

### Search Performance

```python
import time

start = time.time()
results = vector_store.search("query")
elapsed = time.time() - start

print(f"Search took {elapsed*1000:.2f}ms")
```

## Troubleshooting

### Qdrant Connection Failed

```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Check logs
docker logs mlcf-qdrant

# Restart
docker-compose restart qdrant
```

### Out of Memory

```python
# Use smaller batch size
generator = EmbeddingGenerator(batch_size=16)

# Or use smaller model
generator = EmbeddingGenerator(
    model_name="sentence-transformers/all-MiniLM-L6-v2"  # 384 dim
)
```

### Slow Search

```python
# Reduce search space
results = vector_store.search(
    query="query",
    max_results=10,  # Reduce from 100
    filters={"category": "specific"}  # Add filters
)
```

## Examples

See full examples:
- `examples/vector_search_example.py`
- `examples/hybrid_search_example.py`

```bash
python examples/vector_search_example.py
python examples/hybrid_search_example.py
```