#!/bin/bash

echo "🚀 Starting LiveStore FastAPI Server..."

# Initialize admin user if environment variables are set
if [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
    echo "🔧 Initializing admin user..."
    python init_admin.py
    if [ $? -eq 0 ]; then
        echo "✅ Admin user initialization completed"
    else
        echo "⚠️ Admin user initialization failed, but continuing..."
    fi
else
    echo "ℹ️ Admin user environment variables not set, skipping admin initialization"
fi

# Start the FastAPI server
echo "🌐 Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000