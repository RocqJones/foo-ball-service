#!/bin/bash
# setup.sh - Setup script for Foo Ball Service

set -e  # Exit on error

echo "=== Foo Ball Service Setup ==="
echo ""

# Check Python installation
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Found Python $PYTHON_VERSION"

REQUIRED_PYTHON_VERSION="3.8"
# Enforce minimum Python version
if [ "$(printf '%s\n' "$REQUIRED_PYTHON_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_PYTHON_VERSION" ]; then
    echo "Error: Python $REQUIRED_PYTHON_VERSION or higher is required. Found Python $PYTHON_VERSION."
    exit 1
fi
# Create virtual environment
if [ -d "venv" ]; then
    echo "Virtual environment already exists."
    
    # Check if running in interactive mode
    if [[ ! -t 0 ]]; then
        echo "Running in non-interactive mode."
        if [[ "${RECREATE_VENV:-0}" == "1" ]]; then
            echo "RECREATE_VENV is set. Removing existing virtual environment..."
            rm -rf venv
            echo "Creating new virtual environment..."
            python3 -m venv venv
        else
            echo "Skipping venv recreation. To recreate, set RECREATE_VENV=1 environment variable."
        fi
    else
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Removing existing virtual environment..."
            rm -rf venv
            echo "Creating new virtual environment..."
            python3 -m venv venv
        fi
    fi
else
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found. Installing basic dependencies..."
    pip install fastapi uvicorn pymongo python-dotenv
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "Warning: .env file not found!"
    echo "Please create a .env file with your configuration."
    echo "Example:"
    echo "  MONGO_URI=mongodb://localhost:27017"
    echo "  DB_NAME=foo_ball_db"
    echo ""
fi

# Create logs directory
if [ ! -d "logs" ]; then
    echo "Creating logs directory..."
    mkdir logs
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To start the server, run:"
echo "  ./start_server.sh"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo ""
