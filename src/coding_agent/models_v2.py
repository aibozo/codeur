"""
Improved models with better context handling.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


@dataclass
class CodeContext:
    """
    Context for code generation - improved version.
    
    Key improvements:
    1. No truncation of content
    2. Better organization of chunks
    3. Metadata about line numbers preserved
    """
    task_goal: str = ""
    file_paths: List[str] = field(default_factory=list)
    file_snippets: Dict[str, str] = field(default_factory=dict)  # File skeletons
    blob_contents: Dict[str, str] = field(default_factory=dict)  # RAG chunks with line numbers
    related_functions: List[Dict[str, Any]] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    error_patterns: List[str] = field(default_factory=list)
    skeleton_patches: List[str] = field(default_factory=list)
    token_count: int = 0
    
    def add_snippet(self, file_path: str, content: str):
        """Add a file skeleton/snippet."""
        self.file_snippets[file_path] = content
    
    def add_blob(self, blob_id: str, content: str):
        """Add a RAG chunk with line numbers."""
        self.blob_contents[blob_id] = content
    
    def to_prompt_context(self, max_tokens: Optional[int] = None) -> str:
        """
        Convert to prompt-friendly context string.
        
        NO TRUNCATION - o3 needs complete context!
        """
        sections = []
        
        # Add goal
        sections.append(f"Task Goal: {self.task_goal}")
        
        # Add skeleton patches if available
        if self.skeleton_patches:
            sections.append("\nSkeleton Patches (hints):")
            for patch in self.skeleton_patches:
                sections.append(patch)
        
        # Add RAG chunks first (most relevant)
        if self.blob_contents:
            sections.append("\nRelevant Code Chunks (with line numbers):")
            for blob_id, content in self.blob_contents.items():
                sections.append(f"\n--- Chunk: {blob_id} ---")
                sections.append(content)
                sections.append("--- End Chunk ---")
        
        # Add file skeletons for structure
        if self.file_snippets:
            sections.append("\nFile Structure:")
            for file_path, content in self.file_snippets.items():
                sections.append(f"\n--- {file_path} ---")
                sections.append(content)
                sections.append("--- End File ---")
        
        # Add related functions metadata
        if self.related_functions:
            sections.append("\nRelated Functions:")
            for func in self.related_functions:
                sections.append(f"- {func['file']}:{func['line']} - {func['symbol']} ({func['type']})")
        
        full_context = "\n".join(sections)
        
        # Only truncate if explicitly requested and necessary
        if max_tokens and self.token_count > max_tokens:
            # Warn that truncation is happening
            logger.warning(f"Context truncation requested: {self.token_count} > {max_tokens} tokens")
            # Still return full context - let the model handle it
            
        return full_context
    
    def request_additional_context(self, file_path: str, start_line: int, end_line: int) -> str:
        """
        Allow agent to request specific additional context.
        
        This could be implemented as a tool for the agent.
        """
        # This would fetch the specific lines from the file
        # For now, just a placeholder
        return f"[Additional context would be fetched for {file_path}:{start_line}-{end_line}]"


# Keep other models the same
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


class CommitStatus(Enum):
    """Status of a commit attempt."""
    SUCCESS = "success"
    SOFT_FAIL = "soft_fail"  # Can retry
    HARD_FAIL = "hard_fail"  # Cannot retry
    

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


# Add logger
import logging
logger = logging.getLogger(__name__)