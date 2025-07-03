#!/usr/bin/env bash
# view_logs.sh - View server logs in real-time

LATEST_LOG=$(ls -t logs/rowcast_*.log 2>/dev/null | head -1)

if [ -n "$LATEST_LOG" ]; then
    echo "📝 Viewing logs from: $LATEST_LOG"
    echo "Press Ctrl+C to exit"
    echo "----------------------------------------"
    tail -f "$LATEST_LOG"
else
    echo "❌ No log files found in logs/ directory"
    echo "Make sure the server is running with ./start_server.sh"
fi
