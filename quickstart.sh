#!/bin/bash
# Quick start script for Agent System

set -e

echo "🚀 Agent System Quick Start"
echo "=========================="
echo ""

# Check Python version
echo "📌 Checking Python version..."
python_version=$(python3 --version 2>&1)
if [[ $? -ne 0 ]]; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi
echo "✅ $python_version"

# Check Node.js version
echo "📌 Checking Node.js version..."
node_version=$(node --version 2>&1)
if [[ $? -ne 0 ]]; then
    echo "❌ Node.js is not installed. Please install Node.js 16 or higher."
    exit 1
fi
echo "✅ Node.js $node_version"

# Check Docker
echo "📌 Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker is not installed. Qdrant vector database requires Docker."
    echo "   You can install Docker from: https://docs.docker.com/get-docker/"
    read -p "Continue without Docker? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Docker is installed"
fi

# Create virtual environment
echo ""
echo "📦 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -e .
echo "✅ Python dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Creating .env file..."
    cat > .env << EOL
# API Keys
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key  # Optional

# Model Configuration
ANTHROPIC_MODEL=claude-3-opus-20240229

# System Configuration
LOG_LEVEL=INFO
RAG_COLLECTION_NAME=code_chunks
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Message Queue (optional)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
AMQP_URL=amqp://guest:guest@localhost:5672/
EOL
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API keys before running the system!"
else
    echo "✅ .env file already exists"
fi

# Install frontend dependencies
if [ -d "frontend" ]; then
    echo ""
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
    echo "✅ Frontend dependencies installed"
fi

# Make start script executable
chmod +x start_ui.sh

echo ""
echo "✨ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Start Docker (if not running)"
echo "3. Run ./start_ui.sh to start the system"
echo ""
echo "For more information, see README.md"