#!/usr/bin/env bash
# stop_server.sh - stop the RowCast API server

PID_FILE="logs/rowcast.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Stopping RowCast API server (PID: $PID)..."
        kill "$PID"
        
        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! ps -p "$PID" > /dev/null 2>&1; then
                echo "✅ Server stopped successfully."
                rm -f "$PID_FILE"
                exit 0
            fi
            sleep 1
        done
        
        # Force kill if still running
        echo "Force killing server..."
        kill -9 "$PID" 2>/dev/null
        rm -f "$PID_FILE"
        echo "✅ Server stopped (force killed)."
    else
        echo "Server is not running (PID $PID not found)."
        rm -f "$PID_FILE"
    fi
else
    echo "No PID file found. Server may not be running."
    # Try to kill any gunicorn processes as fallback
    pkill -f "gunicorn wsgi:app" && echo "Killed remaining gunicorn processes."
fi
