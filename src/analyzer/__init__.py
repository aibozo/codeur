"""
Analyzer Agent package.

The Analyzer agent is responsible for automatic architecture analysis,
documentation generation, and keeping architectural understanding up-to-date.
"""

from .analyzer import Analyzer
from .models import (
    ArchitectureGraph,
    ComponentNode,
    DependencyEdge,
    AnalysisReport,
    ChangeThreshold
)

__all__ = [
    'Analyzer',
    'ArchitectureGraph',
    'ComponentNode',
    'DependencyEdge',
    'AnalysisReport',
    'ChangeThreshold'
]