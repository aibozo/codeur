# Makefile for Codeur Agent System

.PHONY: help setup venv install install-dev clean test lint format run-web run-backend run-terminal build-frontend

# Default target
help:
	@echo "Codeur Agent System - Available Commands:"
	@echo "========================================="
	@echo "  make setup        - Complete setup (venv + dependencies)"
	@echo "  make venv         - Create virtual environment"
	@echo "  make install      - Install dependencies"
	@echo "  make install-dev  - Install with dev dependencies"
	@echo "  make clean        - Clean up generated files"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make run-web      - Start web dashboard"
	@echo "  make run-backend  - Start backend only"
	@echo "  make run-terminal - Start terminal dashboard"
	@echo "  make build-frontend - Build frontend for production"

# Setup everything
setup: venv install
	@echo "✅ Setup complete! Run 'source venv/bin/activate' to activate"

# Create virtual environment
venv:
	@echo "Creating virtual environment..."
	@python3 -m venv venv
	@echo "✓ Virtual environment created"

# Install dependencies
install:
	@echo "Installing dependencies..."
	@. venv/bin/activate && pip install --upgrade pip
	@. venv/bin/activate && pip install -r requirements.txt
	@. venv/bin/activate && pip install -e .
	@if [ -d "frontend" ]; then \
		echo "Installing frontend dependencies..."; \
		cd frontend && npm install; \
	fi
	@echo "✓ Dependencies installed"

# Install with dev dependencies
install-dev:
	@echo "Installing dependencies with dev tools..."
	@. venv/bin/activate && pip install --upgrade pip
	@. venv/bin/activate && pip install -r requirements-dev.txt
	@. venv/bin/activate && pip install -e .
	@if [ -d "frontend" ]; then \
		echo "Installing frontend dependencies..."; \
		cd frontend && npm install; \
	fi
	@echo "✓ All dependencies installed"

# Clean up
clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@if [ -d "frontend/dist" ]; then rm -rf frontend/dist; fi
	@if [ -d "frontend/node_modules" ]; then rm -rf frontend/node_modules; fi
	@echo "✓ Cleaned"

# Run tests
test:
	@echo "Running tests..."
	@. venv/bin/activate && pytest tests/

# Run linters
lint:
	@echo "Running linters..."
	@. venv/bin/activate && ruff check src/
	@. venv/bin/activate && mypy src/

# Format code
format:
	@echo "Formatting code..."
	@. venv/bin/activate && black src/ tests/
	@. venv/bin/activate && isort src/ tests/

# Run web dashboard
run-web:
	@echo "Starting web dashboard..."
	@. venv/bin/activate && agent web start

# Run backend only
run-backend:
	@echo "Starting backend server..."
	@. venv/bin/activate && AGENT_WEBHOOK_ENABLED=true agent webhook start

# Run terminal dashboard
run-terminal:
	@echo "Starting terminal dashboard..."
	@. venv/bin/activate && agent monitor --dashboard

# Build frontend for production
build-frontend:
	@echo "Building frontend..."
	@cd frontend && npm run build
	@echo "✓ Frontend built in frontend/dist/"

# Development shortcuts
dev: install-dev
	@echo "Development environment ready!"

# Quick start
start: setup run-web