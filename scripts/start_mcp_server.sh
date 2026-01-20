#!/bin/bash
# Start MCP Context Server

set -e

echo "Starting Multi-Layer Context Foundation MCP Server..."
echo "================================================"

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not activated"
    echo "Run: source venv/bin/activate"
    exit 1
fi

# Check dependencies
echo "Checking dependencies..."
python -c "import mcp" 2>/dev/null || {
    echo "❌ MCP not installed"
    echo "Install: pip install mcp"
    exit 1
}

echo "✓ Dependencies OK"
echo ""

# Check if services are running
echo "Checking services..."

# Check Qdrant
if curl -s http://localhost:6333 > /dev/null 2>&1; then
    echo "✓ Qdrant running"
else
    echo "⚠️  Qdrant not running (vector search disabled)"
fi

# Check Neo4j
if curl -s http://localhost:7474 > /dev/null 2>&1; then
    echo "✓ Neo4j running"
else
    echo "⚠️  Neo4j not running (graph search disabled)"
fi

echo ""

# Start server
echo "Starting MCP server..."
echo "================================================"
echo ""

# Use config file if provided
if [ -n "$1" ]; then
    CONFIG_FILE="$1"
    echo "Using config: $CONFIG_FILE"
    python -m mlcf.mcp.server --config "$CONFIG_FILE"
else
    echo "Using default config"
    python -m mlcf.mcp.server --config config/mcp_config.yaml
fi