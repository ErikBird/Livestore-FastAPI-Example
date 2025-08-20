#!/bin/bash
set -e

echo "🚀 LiveStore FastAPI Development Server"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "   or: pip install uv"
    exit 1
fi

# Sync dependencies using uv (if pyproject.toml exists)
if [ -f "pyproject.toml" ]; then
    echo "📦 Syncing dependencies from pyproject.toml..."
    uv sync
fi

# Load environment variables from project root .env file
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "📄 Loading environment from: $PROJECT_ROOT/.env"
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Set additional defaults for development if not already set
export DATABASE_URL=${DATABASE_URL:-"postgresql://postgres:password@localhost:5432/livestore"}
export AUTH_TOKEN=${AUTH_TOKEN:-"dev-auth-token"}
export ADMIN_SECRET=${ADMIN_SECRET:-"dev-admin-secret"}
export JWT_SECRET=${JWT_SECRET:-"dev-jwt-secret-key"}
export LOG_LEVEL=${LOG_LEVEL:-"DEBUG"}

echo "📊 Development Configuration:"
echo "  DATABASE_URL: $DATABASE_URL"
echo "  AUTH_TOKEN: ${AUTH_TOKEN:0:8}..."
echo "  LOG_LEVEL: $LOG_LEVEL"

# Admin user will be automatically initialized by FastAPI startup event

# Start the development server with hot reload
echo "🌐 Starting development server with hot reload..."
echo "📍 Server will be available at: http://localhost:8000"
echo "📍 API docs will be available at: http://localhost:8000/docs"

exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload