#!/bin/bash

echo "🚀 Starting Deal Scout Development Environment..."

# Start Chrome with remote debugging (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📱 Starting Chrome with remote debugging..."
    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
        --remote-debugging-port=9222 \
        --user-data-dir=$HOME/.chrome-dealscout-profile \
        --disable-blink-features=AutomationControlled &
    CHROME_PID=$!
    echo "Chrome started (PID: $CHROME_PID)"
fi

# Start Docker services
echo "🐳 Starting Docker services (PostgreSQL + Redis)..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 5

# Start API server
echo "🔧 Starting FastAPI backend..."
cd apps/api
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -e .
uvicorn src.main:app --reload --port 8000 &
API_PID=$!
cd ../..
echo "API started (PID: $API_PID)"

# Start frontend (if exists)
if [ -d "apps/web" ]; then
    echo "🎨 Starting Next.js frontend..."
    cd apps/web
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        pnpm install
    fi
    pnpm dev &
    WEB_PID=$!
    cd ../..
    echo "Frontend started (PID: $WEB_PID)"
fi

echo ""
echo "✅ Deal Scout is running!"
echo ""
echo "📍 Services:"
echo "   - API:      http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Frontend: http://localhost:3000"
echo "   - Chrome:   http://localhost:9222"
echo ""
echo "🛑 To stop all services:"
echo "   docker-compose down"
echo "   kill $API_PID"
if [ ! -z "$WEB_PID" ]; then
    echo "   kill $WEB_PID"
fi
if [ ! -z "$CHROME_PID" ]; then
    echo "   kill $CHROME_PID"
fi
echo ""

# Keep script running
wait
