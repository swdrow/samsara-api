#!/usr/bin/env bash
# dev_start.sh - Start development environment with both frontend and backend

echo "🚀 Starting RowCast Development Environment"
echo "=========================================="

# Function to cleanup on exit
cleanup() {
    echo "🛑 Shutting down development servers..."
    pkill -f "vite"
    pkill -f "gunicorn"
    exit 0
}

# Trap ctrl+c and cleanup
trap cleanup SIGINT SIGTERM

# Check if both servers should start
if [ "$1" = "--frontend-only" ]; then
    echo "📱 Starting frontend dev server only..."
    npm run dev
elif [ "$1" = "--backend-only" ]; then
    echo "🔧 Starting backend API server only..."
    npm run api
else
    echo "🔥 Starting both frontend and backend servers..."
    echo ""
    echo "Frontend will be available at: http://localhost:3000"
    echo "Backend API will be available at: http://localhost:8000"
    echo ""
    echo "Press Ctrl+C to stop both servers"
    echo ""
    
    # Start both servers
    npm run dev:full
fi
