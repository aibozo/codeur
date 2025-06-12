"""
Git integration utilities for the agent system.
"""

import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


class GitAdapter:
    """Adapter for Git operations."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        
    def get_current_commit(self) -> str:
        """Get the current commit SHA."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            # Not a git repo or no commits
            return "no-commit"
    
    def get_current_branch(self) -> str:
        """Get the current branch name."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "main"
    
    def get_modified_files(self) -> List[str]:
        """Get list of modified files."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            files = result.stdout.strip().split('\n')
            return [f for f in files if f]
        except subprocess.CalledProcessError:
            return []
    
    def get_file_content(self, file_path: str, commit: Optional[str] = None) -> Optional[str]:
        """Get file content at specific commit."""
        try:
            cmd = ["git", "show"]
            if commit:
                cmd.append(f"{commit}:{file_path}")
            else:
                cmd.append(f"HEAD:{file_path}")
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return None
    
    def apply_patch(self, patch: str) -> Tuple[bool, str]:
        """Apply a patch to the repository."""
        try:
            result = subprocess.run(
                ["git", "apply", "--check"],
                cwd=self.repo_path,
                input=patch,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return False, f"Patch validation failed: {result.stderr}"
            
            # Apply the patch
            result = subprocess.run(
                ["git", "apply"],
                cwd=self.repo_path,
                input=patch,
                capture_output=True,
                text=True,
                check=True
            )
            
            return True, "Patch applied successfully"
            
        except subprocess.CalledProcessError as e:
            return False, f"Failed to apply patch: {e.stderr}"
    
    def commit(self, message: str, author: Optional[str] = None) -> Tuple[bool, str]:
        """Create a commit with the given message."""
        try:
            # Stage all changes
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_path,
                check=True
            )
            
            # Commit
            cmd = ["git", "commit", "-m", message]
            if author:
                cmd.extend(["--author", author])
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get the commit SHA
            sha_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            return True, sha_result.stdout.strip()
            
        except subprocess.CalledProcessError as e:
            return False, f"Failed to commit: {e.stderr}"