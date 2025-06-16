"""
Unified UI module for the Agent System.

This module provides shared components and logic for both terminal
and web interfaces.
"""

from src.ui.shared.formatters import CodeFormatter, DiffFormatter
from src.ui.shared.state import UIState

__all__ = ['CodeFormatter', 'DiffFormatter', 'UIState']