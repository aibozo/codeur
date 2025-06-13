#!/bin/bash
# Start the Agent System UI

echo "🚀 Starting Agent System UI..."

# Kill any existing processes on port 8000
if lsof -i :8000 > /dev/null 2>&1; then
    echo "⚠️  Port 8000 is in use. Killing existing process..."
    lsof -ti :8000 | xargs kill -9 2>/dev/null
    sleep 1
fi

# Check if Docker is running for Qdrant
if ! docker ps | grep -q qdrant; then
    echo "⚠️  Qdrant not running. Starting Qdrant..."
    docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
    sleep 5
fi

# Start the backend API
echo "🔧 Starting FastAPI backend..."
cd src/web_api
uvicorn app:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start the frontend
echo "🎨 Starting React frontend..."
cd ../../frontend
npm install
npm start &
FRONTEND_PID=$!

echo "✅ Agent System UI started!"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:3001"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for interrupt
trap "echo '🛑 Stopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait