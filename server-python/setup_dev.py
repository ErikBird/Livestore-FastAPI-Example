#!/usr/bin/env python3
"""
Development setup script for LiveStore FastAPI backend
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, description: str) -> bool:
    """Run a shell command and return success status"""
    print(f"\n🔧 {description}")
    print(f"Running: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False


def main():
    """Setup development environment"""
    print("🚀 Setting up LiveStore FastAPI development environment")
    
    project_root = Path(__file__).parent
    venv_path = project_root / "venv"
    
    # Check if virtual environment exists
    if not venv_path.exists():
        print("\n📦 Creating virtual environment...")
        if not run_command(f"python3 -m venv {venv_path}", "Creating virtual environment"):
            print("❌ Failed to create virtual environment")
            sys.exit(1)
    else:
        print("\n✅ Virtual environment already exists")
    
    # Determine pip path
    if os.name == 'nt':  # Windows
        pip_path = venv_path / "Scripts" / "pip"
        python_path = venv_path / "Scripts" / "python"
    else:  # Unix-like
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"
    
    # Install requirements
    print("\n📚 Installing Python dependencies...")
    if not run_command(f"{pip_path} install -r requirements.txt", "Installing requirements"):
        print("❌ Failed to install requirements")
        sys.exit(1)
    
    # Start PostgreSQL container
    print("\n🐘 Starting PostgreSQL container...")
    if not run_command("docker-compose up -d postgres", "Starting PostgreSQL"):
        print("❌ Failed to start PostgreSQL container")
        sys.exit(1)
    
    # Wait for PostgreSQL to be ready
    print("\n⏳ Waiting for PostgreSQL to be ready...")
    import time
    time.sleep(5)
    
    print("\n✅ Development environment setup complete!")
    print("\n📋 Next steps:")
    print("1. Open this project in VS Code")
    print("2. Select the Python interpreter: ./venv/bin/python (or ./venv/Scripts/python.exe on Windows)")
    print("3. Press F5 to start debugging, or")
    print("4. Use Ctrl+Shift+P and search for 'Debug: Start Debugging'")
    print("\n🔧 Available debug configurations:")
    print("  - 'Debug FastAPI Server': Direct debugging")
    print("  - 'Debug FastAPI Server (Production Mode)': Via uvicorn")
    print("\n🌐 The server will be available at: http://localhost:8000")
    print("📊 Health check: http://localhost:8000/health")
    print("🔗 WebSocket endpoint: ws://localhost:8000/websocket?storeId=test_store")


if __name__ == "__main__":
    main()