#!/bin/bash

echo "🚀 Starting LiveStore FastAPI Server..."

# Debug: Show admin configuration (masked)
echo "📊 Admin Configuration:"
if [ -n "$ADMIN_EMAIL" ]; then
    echo "  ADMIN_EMAIL: $ADMIN_EMAIL"
else
    echo "  ADMIN_EMAIL: ❌ NOT SET"
fi

if [ -n "$ADMIN_PASSWORD" ]; then
    echo "  ADMIN_PASSWORD: ${ADMIN_PASSWORD:0:8}..."
else
    echo "  ADMIN_PASSWORD: ❌ NOT SET"
fi

# Admin user will be automatically initialized by FastAPI startup event
echo "ℹ️ Admin user initialization handled automatically by FastAPI"

# Start the FastAPI server directly (packages already installed system-wide)
echo "🌐 Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000