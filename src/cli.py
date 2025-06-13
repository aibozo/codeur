"""Main CLI interface for the Agent System.

This provides the unified command-line interface for all agent operations.
This file now acts as a simple entry point that delegates to the refactored CLI module.
"""

from src.cli import main

if __name__ == "__main__":
    main()