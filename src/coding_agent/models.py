"""
Data models for the Coding Agent.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class CommitStatus(Enum):
    """Status of a commit operation."""
    SUCCESS = "SUCCESS"
    SOFT_FAIL = "SOFT_FAIL"  # Retryable failure
    HARD_FAIL = "HARD_FAIL"  # Non-retryable failure


@dataclass
class CodeContext:
    """
    Context gathered for code generation.
    
    Contains all the relevant code snippets, imports, and
    documentation needed to generate a patch.
    """
    task_goal: str
    file_snippets: Dict[str, str] = field(default_factory=dict)
    blob_contents: Dict[str, str] = field(default_factory=dict)
    imports: List[str] = field(default_factory=list)
    related_functions: List[Dict[str, Any]] = field(default_factory=list)
    error_patterns: List[str] = field(default_factory=list)
    skeleton_patches: List[str] = field(default_factory=list)
    token_count: int = 0
    
    def add_snippet(self, file_path: str, content: str):
        """Add a code snippet."""
        self.file_snippets[file_path] = content
    
    def add_blob(self, blob_id: str, content: str):
        """Add blob content."""
        self.blob_contents[blob_id] = content
    
    def to_prompt_context(self) -> str:
        """
        Convert to a prompt-friendly context string.
        
        Returns:
            Formatted context string
        """
        sections = []
        
        # Add goal
        sections.append(f"Task Goal: {self.task_goal}")
        
        # Add skeleton patches if available
        if self.skeleton_patches:
            sections.append("\nSkeleton Patches (hints):")
            for patch in self.skeleton_patches[:2]:  # Limit to 2
                sections.append(patch)
        
        # Add relevant functions
        if self.related_functions:
            sections.append("\nRelated Functions:")
            for func in self.related_functions[:3]:  # Limit to 3
                sections.append(f"- {func['file']}:{func['line']} - {func['symbol']}")
        
        # Add file snippets (NO TRUNCATION - models need full context)
        if self.file_snippets:
            sections.append("\nRelevant Code:")
            for file_path, content in list(self.file_snippets.items())[:3]:
                sections.append(f"\n--- {file_path} ---")
                sections.append(content)  # Full content, no truncation
        
        # Add blob contents
        if self.blob_contents:
            sections.append("\nPrefetched Context:")
            for blob_id, content in list(self.blob_contents.items())[:2]:
                sections.append(f"\n--- Blob: {blob_id} ---")
                sections.append(content[:300])
        
        return "\n".join(sections)


@dataclass
class PatchResult:
    """Result of patch generation."""
    success: bool
    patch_content: Optional[str] = None
    error_message: Optional[str] = None
    files_modified: List[str] = field(default_factory=list)
    tokens_used: int = 0
    
    @property
    def is_valid_patch(self) -> bool:
        """Check if we have a valid patch."""
        return self.success and self.patch_content is not None


@dataclass
class ValidationResult:
    """Result of patch validation."""
    syntax_valid: bool = True
    lint_passed: bool = True
    tests_passed: bool = True
    type_check_passed: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    test_output: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return (self.syntax_valid and 
                self.lint_passed and 
                self.tests_passed)
    
    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
        
    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)


@dataclass
class CommitResult:
    """Result of a coding task."""
    task_id: str
    status: CommitStatus
    commit_sha: Optional[str] = None
    branch_name: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    retries: int = 0
    llm_tokens_used: float = 0.0
    
    def add_note(self, note: str):
        """Add a diagnostic note."""
        self.notes.append(note)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "commit_sha": self.commit_sha,
            "branch_name": self.branch_name,
            "notes": self.notes,
            "retries": self.retries,
            "llm_tokens_used": self.llm_tokens_used
        }