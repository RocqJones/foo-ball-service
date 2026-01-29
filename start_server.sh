#!/bin/bash
# start_server.sh - Helper script to start the Foo Ball Service

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        exit 1
    fi
    echo "Virtual environment created successfully."
    
    # Install dependencies
    if [ -f "requirements.txt" ]; then
        echo "Installing dependencies from requirements.txt..."
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            echo "Error: Failed to install dependencies"
            exit 1
        fi
        echo "Dependencies installed successfully."
    fi
else
    echo "Virtual environment found."
fi

# Kill any existing process on port 8000
echo "Checking for existing processes on port 8000..."
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "Found process on port 8000. Killing it..."
    kill -9 $(lsof -ti:8000)
    sleep 1
fi

# Activate virtual environment and start server
echo "Starting Foo Ball Service..."
source venv/bin/activate
uvicorn app.main:app --reload
