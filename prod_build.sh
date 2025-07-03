#!/usr/bin/env bash
# prod_build.sh - Build and deploy for production

echo "🏗️  Building RowCast for Production"
echo "=================================="

# Build frontend assets
echo "📦 Building frontend assets..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Frontend build failed!"
    exit 1
fi

echo "✅ Frontend build successful!"

# Check if dist directory was created
if [ ! -d "dist" ]; then
    echo "❌ dist directory not found!"
    exit 1
fi

echo "📁 Built files:"
ls -la dist/

# Set production environment
export FLASK_ENV=production

echo ""
echo "🚀 Starting production server..."
echo "Production server will serve both frontend and API from port 8000"
echo ""

# Start production server
./start_server.sh
