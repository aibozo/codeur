# Agent System - AI-Powered Code Generation Framework

A sophisticated multi-agent system for automated code generation, featuring a beautiful web UI for real-time monitoring and interaction.

## 🚀 Features

### Core System
- **Multi-Agent Architecture**: Specialized agents for request planning, code planning, and code generation
- **RAG (Retrieval-Augmented Generation)**: Advanced code search with hybrid dense/sparse retrieval using Qdrant
- **Real-time Monitoring**: WebSocket-based live updates of system status and agent activities
- **Message Queue Integration**: Support for Kafka and AMQP for distributed processing
- **Tree-sitter Integration**: Intelligent code parsing and chunking for better context understanding

### Web UI
- **Interactive Dashboard**: Real-time visualization of system metrics, task progress, and agent performance
- **Request Planner Chat**: Natural language interface for describing coding tasks
- **System Metrics**: CPU, memory, and queue monitoring with beautiful time-series charts
- **Agent Network Visualization**: Interactive D3.js force-directed graph showing agent relationships
- **Dark Theme**: Modern, research-style UI with smooth animations and gradient accents

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- Docker (for Qdrant vector database)
- Git

## 🛠️ Installation

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-username/agent-system.git
cd agent-system

# Run the quickstart script
chmod +x quickstart.sh
./quickstart.sh
```

### Manual Installation

1. **Set up Python environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install Python dependencies**:
```bash
pip install -e .
# Or with Poetry:
poetry install
```

3. **Install frontend dependencies**:
```bash
cd frontend
npm install
cd ..
```

4. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your API keys:
# ANTHROPIC_API_KEY=your-api-key
# OPENAI_API_KEY=your-api-key (optional)
```

5. **Start Qdrant (vector database)**:
```bash
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
```

## 🚀 Usage

### Starting the Web UI

```bash
./start_ui.sh
```

This will:
- Start the FastAPI backend on http://localhost:8000
- Start the React frontend on http://localhost:3001
- Ensure Qdrant is running

### Using the System

1. **Open the Web UI**: Navigate to http://localhost:3001

2. **Dashboard View**: Monitor real-time system metrics and agent activities

3. **Request Planner Chat**: 
   - Click on "Request Planner" in the navigation
   - Describe your coding task in natural language
   - The system will break down your request and orchestrate agents to complete it

4. **System Metrics**: View detailed performance metrics and resource usage

5. **Agent Network**: Visualize how agents interact and process your requests

### CLI Usage

For direct agent interaction:

```bash
# Run the coding agent
python -m src.agents.coding_agent --request "Add error handling to the API"

# Run the request planner
python -m src.agents.request_planner --goal "Build a REST API with authentication"
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with:

```env
# API Keys
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key  # Optional

# Model Configuration
ANTHROPIC_MODEL=claude-3-opus-20240229  # or claude-3-sonnet-20240229

# System Configuration
LOG_LEVEL=INFO
RAG_COLLECTION_NAME=code_chunks
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Message Queue (optional)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
AMQP_URL=amqp://guest:guest@localhost:5672/
```

### Port Configuration

Default ports (can be changed in `start_ui.sh`):
- Backend API: 8000
- Frontend: 3001
- Qdrant: 6333

## 🐛 Troubleshooting

### Common Issues

1. **Port Conflicts**:
   - Error: "Address already in use"
   - Solution: The start script automatically kills processes on required ports
   - Alternative: Change ports in `start_ui.sh` and `frontend/package.json`

2. **Line Ending Issues (WSL/Windows)**:
   - Error: "/bin/bash^M: bad interpreter"
   - Solution: Run `sed -i 's/\r$//' start_ui.sh`

3. **ModuleNotFoundError**:
   - Error: "No module named 'src.core.message_bus'"
   - Solution: Ensure you're running from the project root and have installed with `pip install -e .`

4. **TypeScript Errors**:
   - Error: "Could not find a declaration file for module 'react-syntax-highlighter'"
   - Solution: Run `npm install --save-dev @types/react-syntax-highlighter` in the frontend directory

### Debug Mode

Enable detailed logging:
```bash
LOG_LEVEL=DEBUG ./start_ui.sh
```

## 🏗️ Architecture

```
agent-system/
├── src/
│   ├── agents/           # Agent implementations
│   ├── rag/             # RAG system with Qdrant
│   ├── tools/           # Code analysis tools
│   ├── web_api/         # FastAPI backend
│   └── core/            # Core utilities
├── frontend/            # React TypeScript UI
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── store/       # Zustand state management
│   │   └── App.tsx      # Main application
│   └── package.json
├── tests/               # Test suite
└── start_ui.sh         # Main startup script
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with Anthropic's Claude API
- UI powered by React, TypeScript, and Tailwind CSS
- Vector search by Qdrant
- Code parsing by tree-sitter