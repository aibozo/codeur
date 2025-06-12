# Codeur - Multi-Agent Code Generation System

A sophisticated multi-agent system for automated code generation, featuring request planning, code planning, implementation, and testing phases orchestrated through a message queue architecture.

## Overview

This project implements a multi-agent architecture where specialized agents collaborate to understand requests, plan implementations, write code, and verify correctness. The Request Planner serves as the primary interface, functioning as a Claude Code/Codex style coding agent.

## Architecture

The system consists of several specialized agents:

- **Request Planner**: Main interface that understands user requests and orchestrates the system
- **Code Planner**: Breaks down high-level plans into concrete coding tasks
- **Coding Agent**: Generates and applies code changes
- **Build/CI Runner**: Executes builds and tests
- **Test Planner**: Designs test specifications
- **Test Builder**: Implements test code
- **Verifier**: Monitors results and triggers corrections
- **RAG Service**: Provides code search and context retrieval

## Getting Started

### Prerequisites

- Python 3.11+
- Poetry for dependency management
- Git

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd agent

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Basic Usage

```bash
# Request a code change
agent request "Add retry logic to the fetch_data function"

# Check status
agent status

# Plan an implementation
agent plan "Refactor the authentication module"

# Search the codebase
agent search "How does the caching system work?"
```

## Development

### Project Structure

```
agent/
├── docs/               # Architecture and design documents
├── src/
│   ├── request_planner/   # Main agent interface
│   ├── core/             # Shared functionality
│   └── proto/            # Protocol definitions
├── tests/              # Test suites
├── config/             # Configuration files
└── pyproject.toml      # Project configuration
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_request_planner.py
```

### Code Quality

```bash
# Format code
black src tests

# Lint code
ruff src tests

# Type check
mypy src
```

## Documentation

- [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md)
- [Request Planner Design](docs/REQUEST_PLANNER_DESIGN.md)

## Contributing

1. Create a feature branch
2. Make changes with tests
3. Ensure code quality checks pass
4. Submit a pull request

## License

[License details to be added]