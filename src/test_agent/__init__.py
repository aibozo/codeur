"""
Test Agent for intelligent test generation and execution.

This agent specializes in:
- Generating comprehensive tests with minimal mocks
- Running tests and analyzing failures
- Adapting tests based on execution results
- Reporting test outcomes to other agents
"""

from .test_agent import TestAgent
from .integrated_test_agent import IntegratedTestAgent

__all__ = ['TestAgent', 'IntegratedTestAgent']