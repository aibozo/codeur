"""
Sandboxed Git operations for enhanced security.

This module provides safe git operations using temporary clones
or dulwich for pure-Python git operations.
"""

import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from contextlib import contextmanager
import uuid

from src.core.logging import get_logger
from src.core.settings import get_settings
from src.core.security import SecurityManager

logger = get_logger(__name__)


class GitSandbox:
    """Manages sandboxed git operations."""
    
    def __init__(self, repo_path: str):
        """
        Initialize git sandbox.
        
        Args:
            repo_path: Path to the actual git repository
        """
        self.repo_path = Path(repo_path).resolve()
        self.settings = get_settings()
        self.security_manager = SecurityManager(self.repo_path)
        
        # Verify it's a git repository
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"{repo_path} is not a git repository")
        
        # Setup sandbox directory
        if self.settings.security.git_sandbox_dir:
            self.sandbox_base = self.settings.security.git_sandbox_dir
        else:
            self.sandbox_base = Path(tempfile.gettempdir()) / "agent-git-sandbox"
        
        self.sandbox_base.mkdir(exist_ok=True, parents=True)
    
    @contextmanager
    def sandboxed_clone(self, branch: Optional[str] = None):
        """
        Create a temporary sandboxed clone of the repository.
        
        Args:
            branch: Specific branch to clone
            
        Yields:
            Path to the sandboxed clone
        """
        sandbox_id = str(uuid.uuid4())
        sandbox_path = self.sandbox_base / sandbox_id
        
        try:
            # Create sandbox directory
            sandbox_path.mkdir(parents=True)
            
            # Clone the repository
            clone_cmd = [
                "git", "clone",
                "--no-hardlinks",  # Ensure complete isolation
                str(self.repo_path),
                str(sandbox_path)
            ]
            
            if branch:
                clone_cmd.extend(["-b", branch])
            
            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"Created sandboxed clone at {sandbox_path}")
            
            yield sandbox_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create sandboxed clone: {e.stderr}")
            raise
        finally:
            # Clean up sandbox
            if sandbox_path.exists():
                try:
                    shutil.rmtree(sandbox_path)
                    logger.info(f"Cleaned up sandbox {sandbox_id}")
                except Exception as e:
                    logger.error(f"Failed to clean up sandbox: {e}")
    
    def apply_patch_sandboxed(self, patch_content: str) -> Tuple[bool, str, Optional[str]]:
        """
        Apply a patch in a sandboxed environment.
        
        Args:
            patch_content: The patch content in unified diff format
            
        Returns:
            Tuple of (success, message, modified_files_list)
        """
        with self.sandboxed_clone() as sandbox_path:
            sandbox_git = SandboxedGitOperations(sandbox_path)
            
            # Apply patch in sandbox
            success, error_msg = sandbox_git.apply_patch(patch_content)
            
            if not success:
                return False, error_msg, None
            
            # Get list of modified files
            modified_files = sandbox_git.get_modified_files()
            
            # If successful, apply to real repository
            if success:
                real_git = SandboxedGitOperations(self.repo_path)
                success, error_msg = real_git.apply_patch(patch_content)
                
                if success:
                    return True, "Patch applied successfully", modified_files
                else:
                    return False, f"Patch validated but failed to apply: {error_msg}", None
            
            return False, error_msg, None
    
    def validate_patch(self, patch_content: str) -> Tuple[bool, str]:
        """
        Validate a patch without applying it.
        
        Args:
            patch_content: The patch content
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        with self.sandboxed_clone() as sandbox_path:
            sandbox_git = SandboxedGitOperations(sandbox_path)
            
            # Try to apply with --check flag
            with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
                f.write(patch_content)
                patch_file = f.name
            
            try:
                result = sandbox_git._run_git(
                    ["apply", "--check", patch_file],
                    check=False
                )
                
                if result.returncode == 0:
                    return True, "Patch is valid"
                else:
                    return False, result.stderr or "Patch validation failed"
                    
            finally:
                try:
                    os.unlink(patch_file)
                except:
                    pass
    
    def get_file_content_safe(self, file_path: str, 
                             commit: Optional[str] = None) -> Optional[str]:
        """
        Safely get file content from repository.
        
        Args:
            file_path: Path to file relative to repo root
            commit: Specific commit to get file from
            
        Returns:
            File content or None if not found
        """
        # Validate path
        try:
            safe_path = self.security_manager.validate_path(
                self.repo_path / file_path
            )
            relative_path = safe_path.relative_to(self.repo_path)
        except Exception as e:
            logger.error(f"Invalid file path: {e}")
            return None
        
        # Use git show to get content without filesystem access
        cmd = ["git", "show"]
        
        if commit:
            cmd.append(f"{commit}:{relative_path}")
        else:
            cmd.append(f"HEAD:{relative_path}")
        
        try:
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


class SandboxedGitOperations:
    """
    Git operations within a sandboxed environment.
    
    This class provides the same interface as GitOperations but
    operates within a sandboxed directory.
    """
    
    def __init__(self, sandbox_path: str):
        """Initialize sandboxed git operations."""
        self.repo_path = Path(sandbox_path)
        self.settings = get_settings()
    
    def apply_patch(self, patch_content: str) -> Tuple[bool, str]:
        """Apply a patch to the repository."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
            f.write(patch_content)
            patch_file = f.name
        
        try:
            # Apply the patch
            result = self._run_git(["apply", "--3way", patch_file])
            
            logger.info("Patch applied successfully in sandbox")
            return True, ""
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            logger.error(f"Failed to apply patch in sandbox: {error_msg}")
            return False, error_msg
            
        finally:
            try:
                os.unlink(patch_file)
            except:
                pass
    
    def get_modified_files(self) -> List[str]:
        """Get list of modified files."""
        try:
            result = self._run_git(["diff", "--name-only", "HEAD"])
            files = result.stdout.strip().split('\n')
            return [f for f in files if f]
        except subprocess.CalledProcessError:
            return []
    
    def get_diff(self, staged: bool = True) -> str:
        """Get the current diff."""
        try:
            cmd = ["diff"]
            if staged:
                cmd.append("--cached")
            
            result = self._run_git(cmd)
            return result.stdout
        except subprocess.CalledProcessError:
            return ""
    
    def _run_git(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command in the sandbox."""
        cmd = ["git"] + args
        
        # Add safety options
        env = os.environ.copy()
        env['GIT_CONFIG_NOSYSTEM'] = '1'  # Ignore system config
        env['HOME'] = str(self.repo_path)  # Isolate HOME
        
        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=check,
            env=env
        )
        
        return result


def create_git_operations(repo_path: str) -> Any:
    """
    Create appropriate git operations instance based on settings.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        GitSandbox or GitOperations instance
    """
    settings = get_settings()
    
    if settings.security.sandbox_git_operations:
        logger.info("Using sandboxed git operations")
        return GitSandbox(repo_path)
    else:
        # Fall back to regular git operations
        logger.info("Using regular git operations (sandboxing disabled)")
        from src.coding_agent.git_operations import GitOperations
        return GitOperations(repo_path)