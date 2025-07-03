#!/usr/bin/env bash
# status_server.sh - check the status of the RowCast API server

PID_FILE="logs/rowcast.pid"

echo "=== RowCast API Server Status ==="

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ Server is RUNNING (PID: $PID)"
        echo "📊 Memory usage: $(ps -p "$PID" -o rss= | awk '{print $1/1024 " MB"}')"
        echo "⏱️  Running since: $(ps -p "$PID" -o lstart= | awk '{print $2, $3, $4}')"
        echo "🌐 API URL: http://localhost:5000"
        echo "📖 Documentation: http://localhost:5000/docs"
        
        # Show latest log entries
        LATEST_LOG=$(ls -t logs/rowcast_*.log 2>/dev/null | head -1)
        if [ -n "$LATEST_LOG" ]; then
            echo ""
            echo "📝 Latest log entries from $LATEST_LOG:"
            echo "----------------------------------------"
            tail -10 "$LATEST_LOG"
        fi
    else
        echo "❌ Server is NOT RUNNING (stale PID file)"
        rm -f "$PID_FILE"
    fi
else
    echo "❌ Server is NOT RUNNING (no PID file)"
fi

echo ""
echo "Available commands:"
echo "  ./start_server.sh  - Start the server"
echo "  ./stop_server.sh   - Stop the server"
echo "  ./status_server.sh - Check server status"
echo "  tail -f logs/rowcast_*.log - View live logs"
