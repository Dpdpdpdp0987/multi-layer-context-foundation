# Usage Examples

## Basic Usage

### Simple Storage and Retrieval

```python
from mlcf import ContextManager

# Initialize context manager
cm = ContextManager(
    vector_db="qdrant",
    graph_db="neo4j"
)

# Store information
cm.store(
    content="User prefers Python for backend development",
    metadata={"type": "preference", "category": "programming"}
)

cm.store(
    content="User is working on a machine learning project",
    metadata={"type": "task", "priority": "high"}
)

# Retrieve relevant context
results = cm.retrieve(
    query="What programming language should I use?",
    max_results=3,
    strategy="hybrid"
)

for result in results:
    print(f"Score: {result['score']:.3f}")
    print(f"Content: {result['content']}")
    print(f"Layer: {result['layer']}")
    print("---")
```

### Using Different Retrieval Strategies

```python
# Semantic search only
semantic_results = cm.retrieve(
    query="machine learning",
    strategy="semantic"
)

# Keyword search only
keyword_results = cm.retrieve(
    query="python programming",
    strategy="keyword"
)

# Graph-based search
graph_results = cm.retrieve(
    query="related preferences",
    strategy="graph"
)

# Hybrid (default)
hybrid_results = cm.retrieve(
    query="what should I work on?",
    strategy="hybrid"
)
```

## Advanced Usage

### Custom Configuration

```python
from mlcf import ContextManager
from mlcf.core.config import Config

# Create custom config
config = Config.from_yaml("custom_config.yaml")

# Or programmatically
config = Config(
    short_term_max_size=20,
    working_memory_max_size=100,
    retrieval_config={
        "semantic_weight": 0.6,
        "keyword_weight": 0.3,
        "graph_weight": 0.1,
        "reranking_enabled": True
    }
)

cm = ContextManager(config=config)
```

### Memory Layer Management

```python
# Explicitly target specific layers

# Short-term (recent conversation)
cm.store(
    "The user just asked about deployment",
    layer="short"
)

# Working memory (active task)
cm.store(
    "Current task: Deploy ML model to production",
    layer="working",
    metadata={"task_id": "task_123"}
)

# Long-term (persistent knowledge)
cm.store(
    "User's deployment platform is AWS",
    layer="long",
    metadata={"type": "fact", "confidence": 0.95}
)

# Clear specific layers
cm.clear_short_term()
cm.clear_working()
```

### Metadata Filtering

```python
# Store with rich metadata
cm.store(
    "Completed feature X on 2026-01-15",
    metadata={
        "type": "achievement",
        "project": "project_alpha",
        "date": "2026-01-15",
        "tags": ["completed", "feature"]
    }
)

# Retrieve with filters
results = cm.retrieve(
    query="project progress",
    filters={
        "type": "achievement",
        "project": "project_alpha"
    }
)
```

## MCP Server Integration

### Starting the Server

```bash
# Basic startup
python -m mlcf.server --port 3000

# With custom config
python -m mlcf.server --config config/production.yaml --port 3000

# With logging
python -m mlcf.server --port 3000 --log-level DEBUG
```

### Client Usage

```python
import requests

# Store via API
response = requests.post(
    "http://localhost:3000/store",
    json={
        "content": "Important information",
        "metadata": {"type": "note"}
    }
)

doc_id = response.json()["id"]

# Retrieve via API
response = requests.post(
    "http://localhost:3000/retrieve",
    json={
        "query": "important info",
        "max_results": 5
    }
)

results = response.json()["results"]
```

## Real-World Scenarios

### Scenario 1: Personal Assistant

```python
from mlcf import ContextManager
import datetime

cm = ContextManager()

# Store user preferences
cm.store(
    "User prefers meetings in the morning",
    metadata={"type": "preference", "category": "schedule"}
)

# Store facts
cm.store(
    "User's birthday is March 15th",
    metadata={"type": "fact", "category": "personal"}
)

# Store current context
cm.store(
    "Planning a team meeting for next week",
    layer="working",
    metadata={"type": "task", "status": "in_progress"}
)

# Query for scheduling
results = cm.retrieve(
    "When should I schedule the team meeting?"
)

# Response incorporates: preference for morning + current task context
```

### Scenario 2: Code Assistant

```python
cm = ContextManager()

# Store code preferences
cm.store(
    "User prefers functional programming style",
    metadata={"type": "coding_style", "language": "python"}
)

cm.store(
    "Project uses pytest for testing",
    metadata={"type": "project_config", "category": "testing"}
)

# Store recent activity
cm.store(
    "Just refactored authentication module",
    layer="short",
    metadata={"type": "activity", "module": "auth"}
)

# Query for coding guidance
results = cm.retrieve(
    "How should I write this test?"
)

# Response incorporates: testing framework + coding style + recent context
```

### Scenario 3: Research Assistant

```python
cm = ContextManager()

# Store papers
cm.store(
    "Paper: 'Attention Is All You Need' - Introduces transformer architecture",
    metadata={
        "type": "paper",
        "year": 2017,
        "authors": ["Vaswani", "et al."],
        "topic": "transformers"
    }
)

# Store notes
cm.store(
    "Transformers use self-attention mechanism for sequence processing",
    metadata={
        "type": "note",
        "source": "Paper: Attention Is All You Need",
        "topic": "transformers"
    }
)

# Query for research
results = cm.retrieve(
    "How do transformers process sequences?",
    filters={"topic": "transformers"}
)
```

## Performance Optimization

### Batch Operations

```python
# Store multiple items efficiently
contents = [
    "Fact 1", "Fact 2", "Fact 3"
]

for content in contents:
    cm.store(content, layer="long")

# Better: Use batch API (when implemented)
# cm.store_batch(contents, layer="long")
```

### Caching

```python
from functools import lru_cache

# Cache frequent queries
@lru_cache(maxsize=100)
def get_user_preferences(user_id: str):
    return cm.retrieve(
        f"user {user_id} preferences",
        filters={"type": "preference"}
    )
```

## Async Usage

```python
import asyncio
from mlcf import ContextManager

async def main():
    async with ContextManager() as cm:
        # Async operations
        await cm.store_async("content")
        results = await cm.retrieve_async("query")

asyncio.run(main())
```