#!/bin/bash

# Setup virtual environment for Codeur Agent System

set -e  # Exit on error

echo "🚀 Setting up Codeur Agent System virtual environment..."
echo "=================================================="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Found Python: $PYTHON_VERSION"

# Check if venv exists
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Remove it? (y/n)"
    read -r response
    if [ "$response" = "y" ]; then
        echo "Removing existing venv..."
        rm -rf venv
    else
        echo "Keeping existing venv. Exiting."
        exit 0
    fi
fi

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "✓ Virtual environment created"
source venv/bin/activate

# Upgrade pip
echo ""
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install package in development mode
echo ""
echo "📦 Installing agent-system in development mode..."
pip install -e .

# Check Node.js
echo ""
echo "🔍 Checking Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "✓ Found Node.js: $NODE_VERSION"
    
    # Install frontend dependencies
    echo ""
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
    echo "✓ Frontend dependencies installed"
else
    echo "⚠️  Node.js not found. Frontend will not work without it."
    echo "   Install from: https://nodejs.org/"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
# Codeur Agent System Configuration

# Enable webhook server
AGENT_WEBHOOK_ENABLED=true
AGENT_WEBHOOK_PORT=8080

# LLM API Keys (add your keys here)
# AGENT_LLM_OPENAI_API_KEY=your-openai-key
# AGENT_LLM_ANTHROPIC_API_KEY=your-anthropic-key

# Redis (optional - for session persistence)
# AGENT_CACHE_REDIS_URL=redis://localhost:6379

# Logging
AGENT_LOG_LEVEL=INFO

# Security
AGENT_SECURITY_SANDBOX_GIT_OPERATIONS=true
EOF
    echo "✓ Created .env file (add your API keys)"
fi

# Create activation script
echo ""
echo "📝 Creating activation helper..."
cat > activate.sh << 'EOF'
#!/bin/bash
# Quick activation script for Codeur

source venv/bin/activate
echo "✓ Codeur environment activated"
echo ""
echo "Available commands:"
echo "  agent status          - Check system status"
echo "  agent web start       - Start web dashboard"
echo "  agent monitor --dashboard - Terminal dashboard"
echo "  agent webhook start   - Start backend only"
echo ""
echo "Quick start: agent web start"
EOF
chmod +x activate.sh

# Final summary
echo ""
echo "=================================================="
echo "✅ Setup Complete!"
echo "=================================================="
echo ""
echo "To activate the environment:"
echo "  source venv/bin/activate"
echo "  # or"
echo "  source activate.sh"
echo ""
echo "To start the web dashboard:"
echo "  agent web start"
echo ""
echo "To deactivate:"
echo "  deactivate"
echo ""

# Show environment info
echo "Environment Info:"
echo "  Python: $(python --version)"
echo "  Pip:    $(pip --version)"
echo "  Venv:   $(pwd)/venv"

# Test imports
echo ""
echo "🧪 Testing imports..."
python -c "
try:
    import click
    import fastapi
    import pydantic_settings
    from src.cli import main
    print('✓ All critical imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

echo ""
echo "🎉 Ready to use! Run 'source venv/bin/activate' to get started."