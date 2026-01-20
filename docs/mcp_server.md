# MCP Server Documentation

## Overview

The Multi-Layer Context Foundation (MLCF) MCP server provides a standardized Model Context Protocol interface for accessing context retrieval capabilities. It exposes resources, tools, and prompts for semantic search, keyword matching, and knowledge graph traversal.

## Features

- **Resources**: Access stored contexts (conversations, documents, entities, relationships)
- **Tools**: Search and manipulate contexts using various retrieval methods
- **Prompts**: Pre-configured prompts for common context operations
- **Async Support**: Full async/await support for efficient operations
- **Hybrid Search**: Combines semantic, keyword, and graph-based retrieval

## Installation

### Prerequisites

```bash
pip install mcp
```

### Configuration

Configure the MCP server in your MCP settings file (e.g., `mcp_config.json`):

```json
{
  "mcpServers": {
    "mlcf-context": {
      "command": "python",
      "args": ["-m", "mlcf.mcp.server"],
      "env": {
        "MLCF_CONFIG_PATH": "./config/mlcf_config.yaml"
      }
    }
  }
}
```

## Resources

The server exposes the following resources:

### 1. Conversations (`context://conversations`)

Access stored conversation contexts.

**Example**:
```python
conversations = await session.read_resource("context://conversations")
```

**Response**:
```json
[
  {
    "id": "conv_123",
    "type": "conversation",
    "content": "Discussion about machine learning...",
    "metadata": {...}
  }
]
```

### 2. Documents (`context://documents`)

Access stored document contexts.

**Example**:
```python
documents = await session.read_resource("context://documents")
```

### 3. Entities (`context://entities`)

Access extracted entities from the knowledge graph (requires Neo4j).

**Example**:
```python
entities = await session.read_resource("context://entities")
```

### 4. Relationships (`context://relationships`)

Access entity relationships from the knowledge graph (requires Neo4j).

**Example**:
```python
relationships = await session.read_resource("context://relationships")
```

## Tools

### 1. search_semantic

Search contexts using semantic similarity.

**Parameters**:
- `query` (string, required): Search query
- `top_k` (integer, optional): Number of results (default: 5)
- `context_type` (string, optional): Filter by type (conversation, document, code, task)

**Example**:
```python
result = await session.call_tool(
    "search_semantic",
    arguments={
        "query": "machine learning optimization",
        "top_k": 3,
        "context_type": "document"
    }
)
```

### 2. search_keyword

Search contexts using keyword matching.

**Parameters**:
- `query` (string, required): Search query with keywords
- `top_k` (integer, optional): Number of results (default: 5)

**Example**:
```python
result = await session.call_tool(
    "search_keyword",
    arguments={
        "query": "neural networks deep learning",
        "top_k": 5
    }
)
```

### 3. search_hybrid

Search using hybrid approach (semantic + keyword + graph).

**Parameters**:
- `query` (string, required): Search query
- `top_k` (integer, optional): Number of results (default: 5)
- `weights` (object, optional): Weights for each method
  - `semantic` (number, default: 0.5)
  - `keyword` (number, default: 0.3)
  - `graph` (number, default: 0.2)

**Example**:
```python
result = await session.call_tool(
    "search_hybrid",
    arguments={
        "query": "machine learning",
        "top_k": 10,
        "weights": {
            "semantic": 0.6,
            "keyword": 0.2,
            "graph": 0.2
        }
    }
)
```

### 4. add_context

Add new context to the system.

**Parameters**:
- `content` (string, required): Context content
- `context_type` (string, required): Type (conversation, document, code, task)
- `metadata` (object, optional): Additional metadata

**Example**:
```python
result = await session.call_tool(
    "add_context",
    arguments={
        "content": "Deep learning models require large datasets...",
        "context_type": "document",
        "metadata": {
            "source": "ML Textbook",
            "chapter": "Neural Networks"
        }
    }
)
```

### 5. search_graph (Neo4j only)

Search using knowledge graph traversal.

**Parameters**:
- `query` (string, required): Search query
- `max_depth` (integer, optional): Maximum traversal depth (default: 2)

**Example**:
```python
result = await session.call_tool(
    "search_graph",
    arguments={
        "query": "Python",
        "max_depth": 3
    }
)
```

### 6. get_entity_relationships (Neo4j only)

Get relationships for a specific entity.

**Parameters**:
- `entity_name` (string, required): Name of the entity
- `relationship_types` (array, optional): Filter by relationship types

**Example**:
```python
result = await session.call_tool(
    "get_entity_relationships",
    arguments={
        "entity_name": "Python",
        "relationship_types": ["USED_FOR", "RELATED_TO"]
    }
)
```

## Prompts

### 1. summarize_context

Summarize retrieved context.

**Arguments**:
- `query` (required): Search query to retrieve context
- `max_results` (optional): Maximum number of results to include

**Example**:
```python
result = await session.get_prompt(
    "summarize_context",
    arguments={
        "query": "machine learning",
        "max_results": "5"
    }
)
```

### 2. find_related

Find related contexts using graph relationships.

**Arguments**:
- `entity` (required): Entity name to find relationships for

**Example**:
```python
result = await session.get_prompt(
    "find_related",
    arguments={
        "entity": "Python"
    }
)
```

### 3. context_analysis

Analyze context with semantic and keyword search.

**Arguments**:
- `topic` (required): Topic to analyze

**Example**:
```python
result = await session.get_prompt(
    "context_analysis",
    arguments={
        "topic": "neural networks"
    }
)
```

## Running the Server

### Standalone Mode

```bash
python -m mlcf.mcp.server
```

### With Custom Configuration

```bash
export MLCF_CONFIG_PATH=/path/to/config.yaml
python -m mlcf.mcp.server
```

### Programmatic Usage

```python
import asyncio
from mlcf.mcp.server import MCPContextServer
from mlcf.config import Config

async def main():
    config = Config.from_yaml("config.yaml")
    server = MCPContextServer(config)
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
```

## Client Example

See `examples/mcp_client_example.py` for a complete client implementation.

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mlcf.mcp.server"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Use the server
            result = await session.call_tool(
                "search_semantic",
                arguments={"query": "machine learning", "top_k": 5}
            )
            print(result.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())
```

## Architecture

```
┌─────────────────────────────────────────┐
│         MCP Client (LLM/App)           │
└────────────────┬────────────────────────┘
                 │ MCP Protocol
                 ▼
┌─────────────────────────────────────────┐
│         MCPContextServer                │
├─────────────────────────────────────────┤
│ - Resources (contexts, entities)        │
│ - Tools (search, add)                   │
│ - Prompts (templates)                   │
└────┬──────────┬──────────┬──────────────┘
     │          │          │
     ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌──────────┐
│Semantic │ │Keyword  │ │Graph     │
│Retriever│ │Retriever│ │Retriever │
└─────────┘ └─────────┘ └──────────┘
     │          │          │
     └──────────┴──────────┘
                │
                ▼
     ┌──────────────────────┐
     │  Context Manager     │
     │  + Storage Layer     │
     └──────────────────────┘
```

## Performance Considerations

1. **Async Operations**: All operations are async for efficiency
2. **Caching**: Embedding model is cached in memory
3. **Batch Processing**: Use hybrid search for efficient multi-method retrieval
4. **Connection Pooling**: Neo4j connections are pooled when enabled

## Error Handling

The server returns structured error responses:

```json
{
  "error": "Error description"
}
```

Common errors:
- `Neo4j not enabled`: Graph features require Neo4j configuration
- `Unknown tool`: Invalid tool name
- `Unknown resource`: Invalid resource URI
- `Invalid arguments`: Missing or invalid tool parameters

## Security

- **Environment Variables**: Use environment variables for sensitive configuration
- **Access Control**: Implement access control in your MCP client
- **Input Validation**: All inputs are validated before processing
- **Resource Limits**: Configure limits in `mlcf_config.yaml`

## Testing

Run MCP server tests:

```bash
pytest tests/test_mcp_server.py -v
```

Test with coverage:

```bash
pytest tests/test_mcp_server.py --cov=mlcf.mcp --cov-report=html
```

## Troubleshooting

### Server Won't Start

1. Check configuration file path
2. Verify all dependencies are installed
3. Check Python version (3.8+ required)

### Neo4j Features Not Available

1. Ensure `neo4j_enabled: true` in config
2. Verify Neo4j connection details
3. Check Neo4j server is running

### Search Returns No Results

1. Verify contexts are added to the system
2. Check embedding model is loaded
3. Try different search queries or methods

## Next Steps

- See [Examples](../examples/) for more usage examples
- Check [Architecture](architecture.md) for system design
- Review [API Reference](api_reference.md) for detailed API docs
