#!/bin/bash
# Start FastAPI server

set -e

echo "Starting Multi-Layer Context Foundation API..."
echo "============================================="

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not activated"
    echo "Run: source venv/bin/activate"
    exit 1
fi

# Check dependencies
echo "Checking dependencies..."
python -c "import fastapi" 2>/dev/null || {
    echo "❌ FastAPI not installed"
    echo "Install: pip install fastapi uvicorn"
    exit 1
}

echo "✓ Dependencies OK"
echo ""

# Check .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo "✓ Created .env file (please review and update)"
fi

echo ""

# Start API server
echo "Starting API server..."
echo "============================================="
echo ""

if [ "$1" == "--dev" ]; then
    echo "Running in development mode with auto-reload"
    uvicorn mlcf.api.main:app --host 0.0.0.0 --port 8000 --reload
else
    echo "Running in production mode"
    uvicorn mlcf.api.main:app --host 0.0.0.0 --port 8000
fi