#!/bin/bash
# Quick start script for Agent System CLI

set -e

echo "🚀 Agent System CLI Quick Start"
echo "==============================="
echo ""

# Check Python version
echo "📌 Checking Python version..."
python_version=$(python3 --version 2>&1)
if [[ $? -ne 0 ]]; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi
echo "✅ $python_version"

# Check Docker (optional)
echo "📌 Checking Docker (optional for Qdrant)..."
if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker is not installed. Qdrant vector database requires Docker."
    echo "   The system can work without it but RAG features will be limited."
    echo "   Install Docker from: https://docs.docker.com/get-docker/"
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
echo "📦 Installing Agent System..."
pip install -e .
echo "✅ Agent System installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Creating .env file template..."
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
    echo "⚠️  IMPORTANT: Edit .env and add your API keys before using the system!"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "✨ Installation complete!"
echo ""
echo "The 'agent-system' command is now available in your virtual environment."
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Activate the virtual environment: source venv/bin/activate"
echo "3. Navigate to your project: cd /path/to/your/project"
echo "4. Initialize the project: agent-system init"
echo "5. Run commands: agent-system run 'your request'"
echo ""
echo "For more information, see README.md"