#!/bin/bash

# Quickstart script for Codeur - Multi-Agent Code Generation System
# This script sets up the environment and starts the web UI

set -e  # Exit on error

echo "======================================"
echo "Codeur - Multi-Agent Code Generation System"
echo "Quickstart Installation Script"
echo "======================================"
echo

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python $required_version or higher is required. Found: Python $python_version"
    exit 1
fi
echo "✓ Python $python_version found"

# Check Node.js
echo "Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed. Please install Node.js 16+ from https://nodejs.org/"
    exit 1
fi
node_version=$(node --version | grep -oE '[0-9]+' | head -1)
echo "✓ Node.js v$(node --version) found"

# Create virtual environment
echo
echo "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -e .
echo "✓ Python dependencies installed"

# Install frontend dependencies
echo
echo "Installing frontend dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
else
    echo "✓ Frontend dependencies already installed"
fi
cd ..

# Check for .env file
echo
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOL
# OpenAI API key for LLM integration
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Anthropic API key if using Claude
# ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Message queue configuration
MESSAGE_QUEUE_TYPE=memory
EOL
    echo "✓ Created .env file"
    echo
    echo "⚠️  IMPORTANT: Please edit .env and add your OpenAI API key"
    echo "   You can get an API key from: https://platform.openai.com/api-keys"
    echo
    read -p "Press Enter when you've added your API key to .env..."
fi

# Make start script executable
chmod +x start_ui.sh

echo
echo "======================================"
echo "✅ Installation Complete!"
echo "======================================"
echo
echo "To start the system, run:"
echo "  ./start_ui.sh"
echo
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  python -m src.web_api.app &"
echo "  cd frontend && npm start"
echo
echo "The web UI will be available at:"
echo "  http://localhost:3000"
echo
echo "For more information, see README.md"