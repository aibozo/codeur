# Codeur - Multi-Agent Code Generation System

#
#This system is still in development. it should be merged with a working version soon. I had to fix some issues with patch generation and im implementing a react frontend to monitor agent health, interact with the task manager, etc. smoothing them out now. 
#

A sophisticated multi-agent system for automated code generation, featuring request planning, code planning, implementation, and testing phases orchestrated through a message queue architecture.

## Features

### Web UI Dashboard
- **Real-time System Monitoring**: View active agents, task progress, and system metrics
- **Interactive Chat Interface**: Communicate with the Request Planner agent through a modern chat UI
- **Task Visualization**: See the flow of tasks through different agents with progress tracking
- **Agent Network View**: Visualize the connections and communication between agents
- **System Metrics**: Monitor CPU usage, memory consumption, and queue lengths

### Core Agent System
- **Request Planner**: Main interface that understands user requests and orchestrates the system
- **Code Planner**: Breaks down high-level plans into concrete coding tasks
- **Coding Agent**: Generates and applies code changes
- **Build/CI Runner**: Executes builds and tests
- **Test Planner**: Designs test specifications
- **Test Builder**: Implements test code
- **Verifier**: Monitors results and triggers corrections
- **RAG Service**: Provides code search and context retrieval with Qdrant vector database

## Prerequisites

- Python 3.11 or higher
- Node.js 16+ and npm (for the web UI)
- Git
- Docker and Docker Compose (optional, for running message queues)
- Unix-like environment (Linux, macOS, or WSL on Windows)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd agent
```

### 2. Install Python Dependencies

#### Using pip (recommended for easy installation)

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows (PowerShell):
# .\venv\Scripts\Activate.ps1

# Install the package in development mode
pip install -e .

# Or install from requirements.txt
pip install -r requirements.txt
```

#### Using Poetry (alternative)

```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate the Poetry shell
poetry shell
```

### 3. Install Frontend Dependencies

```bash
# Navigate to the frontend directory
cd frontend

# Install npm dependencies
npm install

# Return to the root directory
cd ..
```

### 4. Set Up Environment Variables

Create a `.env` file in the root directory:

```bash
# OpenAI API key for LLM integration
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Anthropic API key if using Claude
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Message queue configuration
MESSAGE_QUEUE_TYPE=memory  # Options: memory, kafka, amqp
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

### 5. Install Additional Tools (Optional)

```bash
# Install development tools
pip install black ruff mypy pytest pytest-cov

# Install Docker (for running Kafka/RabbitMQ)
# Follow instructions at https://docs.docker.com/get-docker/
```

## Quick Start

### Starting the Web UI

The easiest way to start the system is using the provided startup script:

```bash
# Make the script executable (first time only)
chmod +x start_ui.sh

# Start the web UI and backend services
./start_ui.sh
```

This will:
1. Start the FastAPI backend server on http://localhost:8000
2. Start the React frontend on http://localhost:3000
3. Open your default browser to the UI

### Manual Start (Alternative)

If you prefer to start services manually:

```bash
# Terminal 1: Start the backend API
cd src/web_api
python app.py

# Terminal 2: Start the frontend
cd frontend
npm start
```

## Usage

### Web UI

1. **Dashboard**: View system status, active tasks, and metrics
2. **Chat Interface**: Type your coding requests in natural language
3. **Task Monitor**: Track the progress of your requests through the agent pipeline
4. **Agent Network**: Visualize how agents communicate and collaborate

### Command Line Interface

```bash
# Request a code change
python -m src.request_planner.cli request "Add retry logic to the fetch_data function"

# Check status
python -m src.request_planner.cli status

# Plan an implementation
python -m src.code_planner.cli plan "Refactor the authentication module"

# Search the codebase
python -m src.rag_service.cli search "How does the caching system work?"
```

### Python API

```python
from src.request_planner import RequestPlanner
from src.messaging.factory import create_message_bus

# Initialize the system
message_bus = create_message_bus("memory")
planner = RequestPlanner(message_bus=message_bus)

# Process a request
response = planner.process_request("Add logging to all API endpoints")
print(response.reasoning)
```

## Configuration

### Message Queue Options

The system supports multiple message queue backends:

1. **In-Memory (Default)**: Good for development and testing
2. **Kafka**: For production use with high throughput
3. **RabbitMQ/AMQP**: For reliable message delivery

Configure in `config/messaging.yaml` or via environment variables.

### Starting External Services

```bash
# Start Kafka (requires Docker)
docker-compose -f docker-compose-kafka.yml up -d

# Start RabbitMQ (requires Docker)
docker-compose up -d

# Start Qdrant vector database
./scripts/start_qdrant.sh
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Kill processes on port 8000 (backend)
   lsof -ti:8000 | xargs kill -9
   
   # Kill processes on port 3000 (frontend)
   lsof -ti:3000 | xargs kill -9
   ```

2. **Module Import Errors**
   ```bash
   # Ensure you're in the virtual environment
   which python  # Should show venv path
   
   # Reinstall in development mode
   pip install -e .
   ```

3. **Permission Denied on start_ui.sh**
   ```bash
   chmod +x start_ui.sh
   ```

4. **npm Command Not Found**
   - Install Node.js from https://nodejs.org/

5. **OpenAI API Key Not Set**
   - Create a `.env` file with your API key
   - Or export it: `export OPENAI_API_KEY=your_key_here`

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_request_planner.py

# Run integration tests
pytest tests/integration/
```

### Code Quality

```bash
# Format code
black src tests

# Lint code
ruff src tests

# Type checking
mypy src
```

### Project Structure

```
agent/
├── frontend/              # React web UI
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── hooks/        # React hooks
│   │   └── store/        # State management
│   └── public/           # Static assets
├── src/
│   ├── request_planner/  # Main agent interface
│   ├── code_planner/     # Code planning agent
│   ├── coding_agent/     # Code generation agent
│   ├── rag_service/      # RAG/search service
│   ├── messaging/        # Message queue implementations
│   ├── web_api/          # FastAPI backend
│   └── core/             # Shared utilities
├── tests/                # Test suites
├── config/               # Configuration files
├── docs/                 # Documentation
└── scripts/              # Utility scripts
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run code quality checks (`black`, `ruff`, `mypy`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

[License details to be added]

## Acknowledgments

- Built with FastAPI, React, and TypeScript
- Uses OpenAI GPT models for code generation
- Vector search powered by Qdrant
- Message queue options include Kafka and RabbitMQ
