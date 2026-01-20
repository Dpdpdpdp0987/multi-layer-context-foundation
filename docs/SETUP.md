# Setup Guide

## Prerequisites

### System Requirements
- **OS**: Linux, macOS, or Windows (with WSL2)
- **Python**: 3.10 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 5GB free space
- **Docker**: 20.10+ (optional)

### External Services

You'll need to set up at least one vector database and optionally a graph database:

#### Option 1: Docker Compose (Recommended)
All services bundled together.

#### Option 2: Cloud Services
- **Qdrant Cloud**: Free tier available
- **Neo4j Aura**: Free tier available

## Installation Steps

### 1. Clone Repository

```bash
git clone https://github.com/Dpdpdpdp0987/multi-layer-context-foundation.git
cd multi-layer-context-foundation
```

### 2. Create Virtual Environment

```bash
# Using venv
python -m venv venv

# Activate on Linux/macOS
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# Development dependencies (optional)
pip install -r requirements-dev.txt
```

### 4. Configure Environment

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Application
APP_NAME=Multi-Layer Context Foundation
DEBUG=true

# Vector Database
VECTOR_DB_PROVIDER=qdrant
VECTOR_DB_HOST=localhost
VECTOR_DB_PORT=6333

# Graph Database
GRAPH_DB_PROVIDER=neo4j
GRAPH_DB_URI=bolt://localhost:7687
GRAPH_DB_USER=neo4j
GRAPH_DB_PASSWORD=your_password

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Retrieval
RETRIEVAL_STRATEGY=hybrid
SEMANTIC_WEIGHT=0.5
KEYWORD_WEIGHT=0.3
GRAPH_WEIGHT=0.2
```

### 5. Start External Services

#### Using Docker Compose

```bash
docker-compose up -d
```

This will start:
- Qdrant (Vector DB) on port 6333
- Neo4j (Graph DB) on port 7687
- Neo4j Browser on port 7474

#### Manual Setup

**Qdrant:**
```bash
docker run -p 6333:6333 \
  -v $(pwd)/qdrant_data:/qdrant/storage \
  qdrant/qdrant
```

**Neo4j:**
```bash
docker run -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -v $(pwd)/neo4j_data:/data \
  neo4j:latest
```

### 6. Initialize Databases

```bash
python scripts/init_databases.py
```

This will:
- Create necessary collections in Qdrant
- Set up graph schema in Neo4j
- Create indexes

### 7. Run Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=mlcf tests/
```

### 8. Start the Application

```bash
# CLI mode
python -m mlcf

# MCP Server mode
python -m mlcf.server --port 3000

# API mode
uvicorn mlcf.api:app --reload
```

## Verification

### Check Services

```bash
# Qdrant
curl http://localhost:6333/

# Neo4j (requires authentication)
curl -u neo4j:password http://localhost:7474/
```

### Test Basic Functionality

```python
from mlcf import ContextManager

# Initialize
cm = ContextManager()

# Store
doc_id = cm.store(
    "Python is my favorite language",
    metadata={"type": "preference"}
)

# Retrieve
results = cm.retrieve("What language do I like?")
print(results)
```

## Troubleshooting

### Issue: Import errors

```bash
# Ensure you're in the virtual environment
which python  # Should point to venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Issue: Cannot connect to databases

```bash
# Check if containers are running
docker ps

# Check logs
docker logs <container_id>

# Restart services
docker-compose restart
```

### Issue: Out of memory

```bash
# Use smaller embedding model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2  # 384 dim
# Instead of
# EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2  # 768 dim

# Reduce batch size
EMBEDDING_BATCH_SIZE=8
```

## Next Steps

1. Read the [Architecture Documentation](ARCHITECTURE.md)
2. Check out [Usage Examples](EXAMPLES.md)
3. Review the [API Documentation](API.md)
4. Join our [Community Discussions](https://github.com/Dpdpdpdp0987/multi-layer-context-foundation/discussions)