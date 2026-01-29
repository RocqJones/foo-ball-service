#!/bin/bash
# start_server.sh - Helper script to start the Foo Ball Service
#
# Usage:
#   ./start_server.sh [PORT] [HOST]
#   PORT=9000 ./start_server.sh
#   HOST=127.0.0.1 PORT=9000 ./start_server.sh
#
# Examples:
#   ./start_server.sh                    # Start on default port 8000 and host 127.0.0.1
#   ./start_server.sh 9000               # Start on port 9000 and host 127.0.0.1
#   ./start_server.sh 9000 0.0.0.0       # Start on port 9000, all interfaces
#   PORT=9000 ./start_server.sh          # Start on port 9000 via env var
#   HOST=0.0.0.0 ./start_server.sh       # Start on all interfaces

# Default port and host, can be overridden via environment variable or command-line argument
PORT="${1:-${PORT:-8000}}"
HOST="${2:-${HOST:-127.0.0.1}}"

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
PIDS=$(lsof -ti:"$PORT" 2>/dev/null)
if [ -n "$PIDS" ]; then
    # Convert PIDs to array for proper handling using mapfile
    mapfile -t PID_ARRAY <<< "$PIDS"
    PID_COUNT=${#PID_ARRAY[@]}
    
    if [ "$PID_COUNT" -eq 1 ]; then
        echo "Found process (PID: ${PID_ARRAY[0]}) on port $PORT."
    else
        echo "Found $PID_COUNT processes on port $PORT:"
        for pid in "${PID_ARRAY[@]}"; do
            echo "  - PID: $pid"
        done
    fi
    
    # Check if running in interactive mode
    if [[ ! -t 0 ]]; then
        echo "Error: Script is running in non-interactive mode, but port $PORT is in use."
        echo "Cannot prompt for confirmation. Please free the port manually or use a different port."
        exit 1
    fi
    
    read -p "Do you want to terminate ${PID_COUNT} process(es)? (y/N): " -n 1 -r USER_REPLY
    echo
    if [[ $USER_REPLY =~ ^[Yy]$ ]]; then
        for PID in "${PID_ARRAY[@]}"; do
            echo "Attempting graceful shutdown of PID $PID (SIGTERM)..."
            if kill -15 "$PID" 2>/dev/null; then
                # Wait up to 5 seconds for graceful shutdown
                TERMINATED=false
                for i in {1..5}; do
                    if ! kill -0 "$PID" 2>/dev/null; then
                        echo "Process $PID terminated gracefully."
                        TERMINATED=true
                        break
                    fi
                    sleep 1
                done
                
                # If still running, escalate to SIGKILL
                if [ "$TERMINATED" = false ]; then
                    # Double-check if process still exists before sending SIGKILL
                    if kill -0 "$PID" 2>/dev/null; then
                        echo "Process $PID did not terminate gracefully. Forcing shutdown (SIGKILL)..."
                        if kill -9 "$PID" 2>/dev/null; then
                            sleep 1
                            if kill -0 "$PID" 2>/dev/null; then
                                echo "Warning: Failed to kill process $PID"
                            else
                                echo "Process $PID forcefully terminated."
                            fi
                        else
                            echo "Warning: Failed to send SIGKILL to process $PID (may have already terminated)"
                        fi
                    fi
                fi
            else
                echo "Warning: Failed to send SIGTERM to process $PID (may have already terminated)"
            fi
        done
    else
        echo "Aborted. Cannot start server while port $PORT is in use."
        exit 1
    fi
fi

# Activate virtual environment and start server
echo "Starting Foo Ball Service on $HOST:$PORT..."
source venv/bin/activate
uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
