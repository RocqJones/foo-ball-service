#!/bin/bash
# start_server.sh - Helper script to start the Foo Ball Service
#
# Usage:
#   ./start_server.sh [PORT]
#   PORT=9000 ./start_server.sh
#
# Examples:
#   ./start_server.sh           # Start on default port 8000
#   ./start_server.sh 9000      # Start on port 9000
#   PORT=9000 ./start_server.sh # Start on port 9000 via env var

# Default port, can be overridden via environment variable or command-line argument
PORT="${1:-${PORT:-8000}}"

# Validate port number
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "Error: PORT must be a valid port number (1-65535), got: $PORT"
    exit 1
fi

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

# Check for existing process on the specified port
echo "Checking for existing processes on port $PORT..."
PID=$(lsof -ti:"$PORT" 2>/dev/null)
if [ -n "$PID" ]; then
    echo "Found process (PID: $PID) on port $PORT."
    read -p "Do you want to terminate this process? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Attempting graceful shutdown (SIGTERM)..."
        kill -15 "$PID" 2>/dev/null
        
        # Wait up to 5 seconds for graceful shutdown
        for i in {1..5}; do
            if ! kill -0 "$PID" 2>/dev/null; then
                echo "Process terminated gracefully."
                break
            fi
            sleep 1
        done
        
        # If still running, escalate to SIGKILL
        if kill -0 "$PID" 2>/dev/null; then
            echo "Process did not terminate gracefully. Forcing shutdown (SIGKILL)..."
            kill -9 "$PID" 2>/dev/null
            sleep 1
            if kill -0 "$PID" 2>/dev/null; then
                echo "Warning: Failed to kill process $PID"
            else
                echo "Process forcefully terminated."
            fi
        fi
    else
        echo "Aborted. Cannot start server while port $PORT is in use."
        exit 1
    fi
fi

# Activate virtual environment and start server
echo "Starting Foo Ball Service on port $PORT..."
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload
