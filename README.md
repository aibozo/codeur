# Agent System - AI-Powered Code Generation CLI

A sophisticated multi-agent system for automated code generation, designed as a secure command-line tool that operates on your current project directory.

## Features

### Core System
- **Multi-Agent Architecture**: Specialized agents for request planning, code planning, and code generation
- **RAG (Retrieval-Augmented Generation)**: Advanced code search with hybrid dense/sparse retrieval using Qdrant
- **Secure by Design**: Restricts all operations to the current project directory
- **Tree-sitter Integration**: Intelligent code parsing and chunking for better context understanding
- **Message Queue Support**: Optional Kafka and AMQP integration for distributed processing

### Security Features
- **Directory Isolation**: Prevents access to parent directories and system files
- **Safe Path Validation**: All file operations are validated against security policies
- **Sensitive File Protection**: Automatically blocks access to credentials, keys, and secrets
- **Project Root Enforcement**: All commands operate from your current directory as the project root

## Prerequisites

- Python 3.8+
- Docker (optional, for Qdrant vector database)
- Git

## Installation

### System-wide Installation

```bash
# Install from PyPI (when published)
pip install agent-system

# Or install from source
git clone https://github.com/your-username/agent-system.git
cd agent-system
pip install -e .
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/your-username/agent-system.git
cd agent-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

## Configuration

### Environment Variables

Create a `.env` file in your project root:

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

## Usage

The agent system operates on your current directory as the project root. All commands are restricted to this directory and its subdirectories for security.

### Initialize a Project

```bash
# Navigate to your project directory
cd /path/to/your/project

# Initialize agent system
agent-system init
```

This creates a `.agent-config.yml` file with project-specific settings.

### Basic Commands

```bash
# Check system status
agent-system status

# Run a natural language request
agent-system run "Add error handling to all API endpoints"

# Create a plan without executing
agent-system run "Refactor the authentication module" --plan-only

# Analyze code structure
agent-system analyze src/

# Search codebase using RAG
agent-system search -q "error handling" -l 10

# Clean up cache and temporary files
agent-system clean
```

### Command Reference

#### `agent-system init`
Initialize the current directory for use with the agent system. Creates configuration files and sets up the project structure.

#### `agent-system status`
Display the current project status, available agents, and configuration.

#### `agent-system run <request> [options]`
Process a natural language request using the multi-agent system.

Options:
- `--plan-only`: Create a plan without executing it
- `--no-rag`: Disable RAG for this request

#### `agent-system analyze <path> [options]`
Analyze code structure and complexity for the specified path.

Options:
- `-o, --output <file>`: Save analysis results to a file

#### `agent-system search [options]`
Search the codebase using RAG technology.

Options:
- `-q, --query <text>`: Search query (required)
- `-l, --limit <number>`: Maximum number of results (default: 10)

#### `agent-system clean`
Remove cache files, logs, and temporary data.

### Examples

```bash
# Add a new feature
agent-system run "Add user authentication with JWT tokens"

# Refactor existing code
agent-system run "Refactor the database module to use async/await"

# Fix bugs
agent-system run "Fix the memory leak in the image processing module"

# Analyze a specific module
agent-system analyze src/auth/ -o auth_analysis.txt

# Search for specific patterns
agent-system search -q "TODO" -l 20
```

## Security Considerations

The agent system implements several security measures:

1. **Directory Restriction**: All file operations are restricted to the current directory and its subdirectories
2. **Forbidden Patterns**: Automatically blocks access to sensitive files like `.env`, `*.key`, `*.pem`, etc.
3. **Excluded Directories**: Skips directories like `.git`, `node_modules`, `__pycache__`
4. **Path Validation**: All paths are validated and resolved before any operation

## Architecture

```
agent-system/
├── src/
│   ├── cli.py              # Main CLI interface
│   ├── core/
│   │   ├── security.py     # Security manager
│   │   ├── logging.py      # Logging configuration
│   │   └── path_utils.py   # Path utilities
│   ├── code_planner/       # Code planning agent
│   ├── coding_agent/       # Code generation agent
│   ├── request_planner/    # Request planning agent
│   ├── rag_service/        # RAG implementation
│   └── messaging/          # Message queue support
└── tests/                  # Test suite
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   - Ensure you have write permissions in the project directory
   - Check that Docker is running if using Qdrant

2. **API Key Errors**
   - Verify your `.env` file contains valid API keys
   - Ensure the `.env` file is in your project root

3. **Path Security Errors**
   - The system prevents access outside the project root
   - Ensure all paths are relative to or within the project directory

### Debug Mode

Enable detailed logging:
```bash
agent-system --debug run "your request"
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with Anthropic's Claude API
- Vector search powered by Qdrant
- Code parsing by tree-sitter