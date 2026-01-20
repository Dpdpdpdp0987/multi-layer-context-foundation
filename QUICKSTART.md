# Quick Start Guide

## Installation

```bash
# Clone repository
git clone https://github.com/Dpdpdpdp0987/multi-layer-context-foundation.git
cd multi-layer-context-foundation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Basic Usage

### 1. Import and Initialize

```python
import asyncio
from mlcf import ContextOrchestrator, ContextRequest

# Create orchestrator
orchestrator = ContextOrchestrator(enable_long_term=False)
```

### 2. Store Context

```python
# Store information
await orchestrator.store(
    content="User prefers Python for development",
    metadata={"type": "preference"},
    conversation_id="conv_1"
)

await orchestrator.store(
    content="Working on ML project with deadline next week",
    metadata={"type": "task", "importance": "high"},
    conversation_id="conv_1"
)
```

### 3. Retrieve Context

```python
# Create retrieval request
request = ContextRequest(
    query="What am I working on?",
    max_results=5,
    conversation_id="conv_1"
)

# Retrieve relevant context
response = await orchestrator.retrieve(request)

# Use the results
for item in response.items:
    print(f"- {item.content}")
    print(f"  Relevance: {item.relevance_score:.2f}")
```

## Complete Example

```python
import asyncio
from mlcf import ContextOrchestrator, ContextRequest

async def main():
    # Initialize
    orchestrator = ContextOrchestrator(enable_long_term=False)
    
    # Store context
    await orchestrator.store(
        "User wants to learn FastAPI",
        metadata={"type": "goal"},
        conversation_id="learning"
    )
    
    await orchestrator.store(
        "Recommended: Build a REST API project",
        metadata={"type": "recommendation"},
        conversation_id="learning"
    )
    
    # Retrieve
    request = ContextRequest(
        query="learning goals",
        conversation_id="learning",
        max_results=10
    )
    
    response = await orchestrator.retrieve(request)
    
    print(f"Found {len(response.items)} relevant items:")
    for item in response.items:
        print(f"\n- {item.content}")
        print(f"  Type: {item.metadata.get('type')}")
        print(f"  Relevance: {item.relevance_score:.2f}")
    
    # Check metrics
    metrics = orchestrator.get_metrics()
    print(f"\nTotal stores: {metrics['storage']['total_stores']}")
    print(f"Total retrievals: {metrics['retrieval']['total_retrievals']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Run Examples

```bash
# Basic usage examples
python examples/basic_usage.py

# Run tests
pytest tests/ -v
```

## Key Concepts

### Memory Layers

1. **Immediate Buffer** (10 items, 1 hour)
   - Recent conversation
   - Fast access
   - Auto-expiring

2. **Session Memory** (50 items)
   - Active tasks
   - Importance-based retention
   - Conversation grouping

3. **Long-Term Storage** (unlimited)
   - Persistent knowledge
   - Vector + Graph databases
   - Hybrid retrieval

### Metadata Fields

- `type`: Content type (task, preference, fact, etc.)
- `importance`: Priority (critical, high, normal, low)
- `category`: Custom categorization
- `task_id`: Task grouping
- `tags`: List of tags

### Retrieval Strategies

- `RECENCY`: Most recent items first
- `RELEVANCE`: Best matching items
- `HYBRID`: Combined recency + relevance
- `SEMANTIC`: Vector similarity (long-term)
- `KEYWORD`: Keyword matching
- `GRAPH`: Relationship-based

## Next Steps

1. ✅ Run the basic examples
2. 📖 Read [Architecture](docs/ARCHITECTURE.md)
3. 🔧 Explore [Configuration](config/config.yaml)
4. 🧪 Write your own tests
5. 🚀 Build something awesome!

## Need Help?

- 📚 Check the [Documentation](docs/)
- 💬 Open an [Issue](https://github.com/Dpdpdpdp0987/multi-layer-context-foundation/issues)
- 🤝 Read [Contributing Guide](CONTRIBUTING.md)