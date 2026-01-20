# Multi-Layer Context Foundation - API Documentation

## Overview

Complete REST API for the Multi-Layer Context Foundation system, providing intelligent context management with multi-layer storage, hybrid retrieval, and knowledge graph capabilities.

## Base URL

```
http://localhost:8000
```

## Authentication

The API supports multiple authentication methods:

1. **Bearer Token (JWT)** - Recommended for production
   ```
   Authorization: Bearer <token>
   ```

2. **API Key** - For programmatic access
   ```
   X-API-Key: your-api-key
   ```

3. **Development Mode** - No authentication required (default for development)

## Endpoints

### Health & Status

#### GET /health
Check API health and component status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600.5,
  "components": {
    "orchestrator": "healthy",
    "vector_store": "healthy",
    "graph_store": "healthy"
  }
}
```

#### GET /health/ready
Readiness check for orchestration (Kubernetes).

#### GET /health/live
Liveness check for orchestration.

---

### Context Management

#### POST /api/v1/context/store
Store a context item.

**Request Body:**
```json
{
  "content": "User prefers Python for backend development",
  "context_type": "preference",
  "priority": "high",
  "metadata": {
    "category": "programming"
  },
  "conversation_id": "conv_123",
  "tags": ["python", "backend"]
}
```

**Response:**
```json
{
  "id": "ctx_abc123",
  "layer": "session",
  "message": "Context stored successfully",
  "created_at": "2024-01-20T10:00:00Z"
}
```

#### POST /api/v1/context/retrieve
Retrieve relevant context based on a query.

**Request Body:**
```json
{
  "query": "What programming languages does the user prefer?",
  "max_results": 5,
  "strategy": "hybrid",
  "min_score": 0.5
}
```

**Response:**
```json
{
  "query": "What programming languages does the user prefer?",
  "results": [
    {
      "id": "ctx_abc123",
      "content": "User prefers Python",
      "context_type": "preference",
      "priority": "high",
      "relevance_score": 0.95,
      "metadata": {},
      "layer": "session",
      "created_at": "2024-01-20T10:00:00Z",
      "access_count": 5
    }
  ],
  "total_results": 1,
  "strategy": "hybrid",
  "execution_time_ms": 45.3
}
```

#### POST /api/v1/context/batch
Batch store multiple context items.

**Request Body:**
```json
{
  "items": [
    {
      "content": "First context item",
      "context_type": "fact"
    },
    {
      "content": "Second context item",
      "context_type": "preference"
    }
  ]
}
```

**Response:**
```json
{
  "total_items": 2,
  "successful": 2,
  "failed": 0,
  "item_ids": ["ctx_1", "ctx_2"],
  "errors": []
}
```

#### GET /api/v1/context/{context_id}
Get a specific context item by ID.

#### DELETE /api/v1/context/{context_id}
Delete a context item.

#### POST /api/v1/context/clear
Clear context from specified layers.

**Query Parameters:**
- `layer`: "immediate", "session", or "all"
- `conversation_id`: (optional) specific conversation to clear

---

### Search

#### POST /api/v1/search/hybrid
Hybrid search combining semantic, keyword, and graph strategies.

#### POST /api/v1/search/semantic
Vector-based semantic similarity search.

#### POST /api/v1/search/keyword
BM25-based keyword search.

---

### Knowledge Graph

#### POST /api/v1/graph/extract
Extract entities and relationships from text.

**Request Body:**
```json
{
  "text": "Steve Jobs founded Apple Inc. in 1976 in California.",
  "entity_types": ["PERSON", "ORG", "GPE"]
}
```

**Response:**
```json
{
  "entities": [
    {
      "text": "Steve Jobs",
      "entity_type": "Person",
      "start": 0,
      "end": 10,
      "confidence": 0.98
    },
    {
      "text": "Apple Inc.",
      "entity_type": "Organization",
      "start": 19,
      "end": 29,
      "confidence": 0.95
    }
  ],
  "relationships": [
    {
      "source": {...},
      "target": {...},
      "relationship_type": "FOUNDED",
      "confidence": 0.85
    }
  ],
  "entity_count": 4,
  "relationship_count": 2
}
```

#### POST /api/v1/graph/query
Query the knowledge graph for entities.

#### GET /api/v1/graph/entity/{entity_id}/neighborhood
Get the neighborhood subgraph around an entity.

**Query Parameters:**
- `depth`: traversal depth (default: 1)

#### GET /api/v1/graph/path/{from_entity}/{to_entity}
Find shortest path between two entities.

---

### Admin

#### GET /api/v1/admin/metrics
Get comprehensive system metrics (admin only).

**Response:**
```json
{
  "total_items": 1500,
  "immediate_buffer_size": 10,
  "session_memory_size": 45,
  "cache_hit_rate": 0.75,
  "total_queries": 1000,
  "avg_response_time_ms": 45.5,
  "uptime_seconds": 86400
}
```

#### POST /api/v1/admin/consolidate
Manually trigger session memory consolidation.

#### POST /api/v1/admin/cache/clear
Clear the query result cache.

---

## Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (success with no body) |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 413 | Request Entity Too Large |
| 422 | Unprocessable Entity (validation error) |
| 429 | Too Many Requests (rate limit) |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

## Error Response Format

All errors follow this format:

```json
{
  "error": "ErrorType",
  "message": "Human-readable error message",
  "detail": "Additional error details",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-20T10:00:00Z"
}
```

## Rate Limiting

- Default: 60 requests per minute per IP
- Headers included in response:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Reset timestamp

## Request/Response Headers

### Common Request Headers
```
Authorization: Bearer <token>
X-API-Key: <api-key>
Content-Type: application/json
```

### Common Response Headers
```
X-Request-ID: <unique-request-id>
X-Process-Time: <processing-time-seconds>
X-RateLimit-Limit: <limit>
X-RateLimit-Remaining: <remaining>
```

## Examples

### Store and Retrieve Context

```bash
# Store context
curl -X POST http://localhost:8000/api/v1/context/store \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User prefers Python",
    "context_type": "preference",
    "priority": "high"
  }'

# Retrieve context
curl -X POST http://localhost:8000/api/v1/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "programming preferences",
    "max_results": 5,
    "strategy": "hybrid"
  }'
```

### Extract Entities

```bash
curl -X POST http://localhost:8000/api/v1/graph/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Steve Jobs founded Apple in California."
  }'
```

### Check Health

```bash
curl http://localhost:8000/health
```

## Interactive Documentation

The API includes interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## SDKs and Client Libraries

### Python

```python
import httpx

class MLCFClient:
    def __init__(self, base_url="http://localhost:8000", api_key=None):
        self.base_url = base_url
        self.headers = {}
        if api_key:
            self.headers["X-API-Key"] = api_key
    
    async def store_context(self, content, **kwargs):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/context/store",
                json={"content": content, **kwargs},
                headers=self.headers
            )
            return response.json()
    
    async def retrieve_context(self, query, max_results=5):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/context/retrieve",
                json={"query": query, "max_results": max_results},
                headers=self.headers
            )
            return response.json()

# Usage
client = MLCFClient()
await client.store_context("User prefers Python")
results = await client.retrieve_context("programming preferences")
```

### JavaScript/TypeScript

```typescript
class MLCFClient {
  constructor(
    private baseUrl = 'http://localhost:8000',
    private apiKey?: string
  ) {}

  async storeContext(content: string, options?: any) {
    const response = await fetch(`${this.baseUrl}/api/v1/context/store`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.apiKey && { 'X-API-Key': this.apiKey })
      },
      body: JSON.stringify({ content, ...options })
    });
    return response.json();
  }

  async retrieveContext(query: string, maxResults = 5) {
    const response = await fetch(`${this.baseUrl}/api/v1/context/retrieve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.apiKey && { 'X-API-Key': this.apiKey })
      },
      body: JSON.stringify({ query, max_results: maxResults })
    });
    return response.json();
  }
}

// Usage
const client = new MLCFClient();
await client.storeContext('User prefers Python');
const results = await client.retrieveContext('programming preferences');
```

## Production Deployment

### Environment Variables

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Key settings to configure:

```env
# Security
REQUIRE_AUTH=true
JWT_SECRET_KEY=<strong-secret-key>

# Services
QDRANT_HOST=qdrant.example.com
NEO4J_URI=bolt://neo4j.example.com:7687
NEO4J_PASSWORD=<secure-password>

# Performance
RATE_LIMIT_PER_MINUTE=100
ENABLE_CACHING=true
```

### Running with Docker

```bash
docker build -t mlcf-api .
docker run -p 8000:8000 --env-file .env mlcf-api
```

### Running with Docker Compose

```bash
docker-compose up -d
```

### Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests.

## Monitoring

The API provides metrics endpoints for monitoring:

- `/health` - Health check with component status
- `/api/v1/admin/metrics` - Detailed metrics (admin only)

Recommended monitoring tools:
- Prometheus for metrics collection
- Grafana for visualization
- ELK stack for log aggregation

## Security Best Practices

1. **Always use HTTPS in production**
2. **Enable authentication** (`REQUIRE_AUTH=true`)
3. **Use strong JWT secrets**
4. **Implement rate limiting**
5. **Validate and sanitize inputs**
6. **Keep dependencies updated**
7. **Use environment variables for secrets**
8. **Enable CORS only for trusted origins**

## Support

- Documentation: `/docs`
- GitHub Issues: https://github.com/Dpdpdpdp0987/multi-layer-context-foundation/issues
- API Status: `/health`
