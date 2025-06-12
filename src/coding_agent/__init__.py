"""
Coding Agent - Converts CodingTasks into Git commits.

The Coding Agent is responsible for:
- Receiving CodingTasks from the Code Planner
- Gathering relevant context using RAG
- Generating code patches with LLM
- Validating the changes
- Creating Git commits
"""

from .agent import CodingAgent
from .models import CommitStatus, CommitResult, CodeContext, PatchResult, ValidationResult
from .context_gatherer import ContextGatherer
from .context_gatherer_v2 import SmartContextGatherer
from .patch_generator import PatchGenerator
from .validator import PatchValidator
from .git_operations import GitOperations

__all__ = [
    "CodingAgent",
    "CommitStatus",
    "CommitResult",
    "CodeContext",
    "PatchResult",
    "ValidationResult",
    "ContextGatherer",
    "SmartContextGatherer",
    "PatchGenerator",
    "PatchValidator",
    "GitOperations"
]