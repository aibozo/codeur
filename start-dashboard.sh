#!/bin/bash
# Start all dashboard components with a single command

echo "🚀 Starting Codeur Dashboard..."
echo "================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to cleanup on exit
cleanup() {
    echo -e "\n${BLUE}Shutting down services...${NC}"
    # Kill all child processes
    pkill -P $$
    exit 0
}

trap cleanup INT TERM

# Check if we're in the project root
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

# Check Python virtual environment
if [ ! -d "venv" ]; then
    echo -e "${BLUE}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Install Python dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    pip install -e . >/dev/null 2>&1
    pip install networkx psutil GPUtil redis >/dev/null 2>&1
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${BLUE}Installing frontend dependencies...${NC}"
    cd frontend
    npm install
    cd ..
fi

# Start backend server
echo -e "${GREEN}✓ Starting backend server on port 8088...${NC}"
python minimal_webhook_server.py &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 2

# Start frontend
echo -e "${GREEN}✓ Starting frontend on port 5173...${NC}"
cd frontend
npm run dev -- --host &
FRONTEND_PID=$!
cd ..

echo -e "\n${GREEN}✅ Dashboard is ready!${NC}"
echo "================================"
echo -e "Frontend: ${BLUE}http://localhost:5173${NC}"
echo -e "Backend API: ${BLUE}http://localhost:8088${NC}"
echo -e "API Docs: ${BLUE}http://localhost:8088/docs${NC}"
echo -e "\nPress ${RED}Ctrl+C${NC} to stop all services"

# Wait for any process to exit
wait