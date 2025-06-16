# Installation Guide

## Prerequisites

- Python 3.8+
- Node.js 16+ (for web interface)
- pip
- Git

## Quick Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd agent
   ```

2. **Install Python dependencies**:
   ```bash
   # Install pydantic-settings first if needed
   pip install pydantic-settings
   
   # Install in development mode
   pip install -e .
   
   # Or install with all dependencies
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Install frontend dependencies** (for web interface):
   ```bash
   cd frontend
   npm install
   cd ..
   ```

## Common Issues

### Pydantic Import Error

If you see:
```
PydanticImportError: `BaseSettings` has been moved to the `pydantic-settings` package
```

Solution:
```bash
pip install --upgrade pydantic-settings
```

### Node/npm Not Found

The web interface requires Node.js. Install from:
- https://nodejs.org/ (recommended)
- Or via package manager:
  ```bash
  # Ubuntu/Debian
  sudo apt install nodejs npm
  
  # macOS with Homebrew
  brew install node
  ```

## Available Commands

After installation, these commands are available:

### Terminal Interface
```bash
# Status check
agent status

# Terminal dashboard
agent monitor --dashboard
```

### Web Interface
```bash
# Start full web dashboard (frontend + backend)
agent web start

# Start on custom ports
agent web start --backend-port 9000 --port 3000

# Build frontend for production
agent web build

# Development mode (frontend only)
agent web dev
```

### Backend Server Only
```bash
# Start webhook server
agent webhook start

# Generate webhook config
agent webhook init
```

## Environment Configuration

Create a `.env` file in the project root:

```env
# Enable webhook server
AGENT_WEBHOOK_ENABLED=true

# LLM API Keys
AGENT_LLM_OPENAI_API_KEY=your-key-here
AGENT_LLM_ANTHROPIC_API_KEY=your-key-here

# Redis (optional)
AGENT_CACHE_REDIS_URL=redis://localhost:6379
```

## Verify Installation

```bash
# Check CLI is working
agent --version

# Run status check
agent status

# Test web interface
agent web start
```

Then open http://localhost:5173 in your browser.