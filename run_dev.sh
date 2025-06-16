#!/bin/bash

# Run development servers

echo "Starting Codeur Development Environment..."
echo "========================================="

# Function to kill processes on exit
cleanup() {
    echo -e "\n\nShutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}

trap cleanup EXIT INT TERM

# Start backend server
echo "Starting backend server on port 8080..."
cd "$(dirname "$0")"
python -m src.webhook.server &
BACKEND_PID=$!

# Give backend time to start
sleep 2

# Start frontend dev server
echo "Starting frontend dev server on port 5173..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo -e "\n========================================="
echo "Servers are running:"
echo "  Backend:  http://localhost:8080"
echo "  Frontend: http://localhost:5173"
echo "  WebSocket: ws://localhost:8080/ws"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "========================================="

# Wait for processes
wait