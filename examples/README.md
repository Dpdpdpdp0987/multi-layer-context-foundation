# Multi-Layer Context Foundation - Examples

This directory contains practical examples demonstrating the capabilities of MLCF.

## Running Examples

```bash
# Make sure you're in the project root and have installed dependencies
pip install -r requirements.txt

# Run basic usage examples
python examples/basic_usage.py

# Run advanced examples (coming soon)
# python examples/advanced_usage.py
```

## Available Examples

### `basic_usage.py`

Demonstrates core functionality:

1. **Basic Storage and Retrieval**
   - Storing context items
   - Retrieving relevant context
   - Viewing metrics

2. **Conversation Tracking**
   - Managing multiple conversations
   - Filtering by conversation ID
   - Conversation isolation

3. **Importance-Based Retention**
   - Different importance levels
   - Intelligent eviction
   - Priority preservation

4. **Layer Management**
   - Explicit layer targeting
   - Layer-specific retrieval
   - Selective clearing

5. **Retrieval Strategies**
   - Recency-based retrieval
   - Relevance-based retrieval
   - Hybrid strategies

## Example Output

When you run `basic_usage.py`, you'll see:

```
=== Basic Usage Example ===

Storing context...
✓ Stored 3 context items

Retrieving context...

Found 3 relevant items:

1. [task]
   Content: Currently working on a machine learning project using TensorFlow
   Relevance: 0.857
   Importance: 1.200

2. [task]
   Content: Deadline for ML project is next Friday
   Relevance: 0.714
   Importance: 1.500

...
```

## Key Concepts Demonstrated

### Context Items

Context items are the basic unit of information:

```python
item = await orchestrator.store(
    content="Your content here",
    metadata={
        "type": "preference",
        "importance": "high",
        "category": "programming"
    },
    conversation_id="conv_1"
)
```

### Retrieval Requests

Requests specify what context to retrieve:

```python
request = ContextRequest(
    query="What am I working on?",
    max_results=5,
    conversation_id="conv_1",
    strategy=RetrievalStrategy.HYBRID
)

response = await orchestrator.retrieve(request)
```

### Memory Layers

- **Immediate Buffer**: Recent conversation (10 items, 1 hour TTL)
- **Session Memory**: Active tasks and context (50 items, LRU eviction)
- **Long-Term**: Persistent storage (unlimited, vector + graph)

### Importance Levels

- `critical`: Must retain, highest priority
- `high`: Important, prefer to retain
- `normal`: Default importance
- `low`: Can evict if needed
- `minimal`: Evict first

## Best Practices

1. **Use Conversation IDs** for related exchanges
2. **Set Importance** for critical information
3. **Add Metadata** for better filtering and retrieval
4. **Choose Appropriate Layers** based on retention needs
5. **Monitor Metrics** to optimize performance

## Next Steps

- Explore advanced examples (coming soon)
- Read the [Architecture Documentation](../docs/ARCHITECTURE.md)
- Check out the [API Reference](../docs/API.md)
- Try building your own context-aware application!