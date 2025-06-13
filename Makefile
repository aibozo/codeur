# Makefile for Agent System

.PHONY: help
help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: requirements
requirements:  ## Compile requirements.txt from requirements.in
	pip-compile requirements.in -o requirements.txt --resolver=backtracking

.PHONY: dev-requirements
dev-requirements: requirements  ## Compile dev-requirements.txt from dev-requirements.in
	pip-compile dev-requirements.in -o dev-requirements.txt --resolver=backtracking

.PHONY: upgrade-requirements
upgrade-requirements:  ## Upgrade all dependencies in requirements.txt
	pip-compile --upgrade requirements.in -o requirements.txt --resolver=backtracking

.PHONY: upgrade-dev-requirements
upgrade-dev-requirements: upgrade-requirements  ## Upgrade all dev dependencies
	pip-compile --upgrade dev-requirements.in -o dev-requirements.txt --resolver=backtracking

.PHONY: sync
sync:  ## Sync installed packages with requirements.txt
	pip-sync requirements.txt

.PHONY: sync-dev
sync-dev:  ## Sync installed packages with dev-requirements.txt
	pip-sync dev-requirements.txt

.PHONY: install
install: requirements sync  ## Install production dependencies

.PHONY: install-dev
install-dev: dev-requirements sync-dev  ## Install all dependencies including dev

.PHONY: test
test:  ## Run tests
	pytest tests/

.PHONY: test-coverage
test-coverage:  ## Run tests with coverage
	pytest tests/ --cov=src --cov-report=html --cov-report=term

.PHONY: lint
lint:  ## Run linters
	ruff check src/
	mypy src/

.PHONY: format
format:  ## Format code with black
	black src/

.PHONY: clean
clean:  ## Clean up cache and temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf dist
	rm -rf *.egg-info