"""
Git operations wrapper for Coding Agent.

Provides a clean interface for git operations needed by the agent.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List
import tempfile
import os

try:
    import git
    GIT_PYTHON_AVAILABLE = True
except ImportError:
    git = None
    GIT_PYTHON_AVAILABLE = False

logger = logging.getLogger(__name__)


class GitOperations:
    """
    Wrapper for git operations.
    
    Provides methods for applying patches, creating commits,
    and managing branches.
    """
    
    def __init__(self, repo_path: str):
        """
        Initialize git operations.
        
        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = Path(repo_path)
        
        # Verify it's a git repository
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"{repo_path} is not a git repository")
        
        # Initialize GitPython repo if available
        self.repo = None
        if GIT_PYTHON_AVAILABLE:
            try:
                self.repo = git.Repo(str(self.repo_path))
            except Exception as e:
                logger.warning(f"Failed to initialize GitPython repo: {e}")
                self.repo = None
    
    def get_current_branch(self) -> str:
        """Get the current branch name."""
        result = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        return result.stdout.strip()
    
    def get_current_commit(self) -> str:
        """Get the current commit SHA."""
        result = self._run_git(["rev-parse", "HEAD"])
        return result.stdout.strip()
    
    def create_branch(self, branch_name: str, base_commit: Optional[str] = None) -> bool:
        """
        Create a new branch.
        
        Args:
            branch_name: Name of the new branch
            base_commit: Base commit SHA (uses current if None)
            
        Returns:
            True if successful
        """
        try:
            if base_commit:
                self._run_git(["checkout", "-b", branch_name, base_commit])
            else:
                self._run_git(["checkout", "-b", branch_name])
            
            logger.info(f"Created branch: {branch_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create branch {branch_name}: {e}")
            return False
    
    def checkout_branch(self, branch_name: str) -> bool:
        """
        Checkout an existing branch.
        
        Args:
            branch_name: Name of the branch
            
        Returns:
            True if successful
        """
        try:
            self._run_git(["checkout", branch_name])
            logger.info(f"Checked out branch: {branch_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to checkout branch {branch_name}: {e}")
            return False
    
    def apply_patch(self, patch_content: str) -> Tuple[bool, str]:
        """
        Apply a patch to the repository.
        
        Args:
            patch_content: The patch content in unified diff format
            
        Returns:
            Tuple of (success, error_message)
        """
        # Write patch to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
            f.write(patch_content)
            patch_file = f.name
        
        try:
            # Apply the patch
            result = self._run_git(["apply", "--3way", patch_file])
            
            logger.info("Patch applied successfully")
            return True, ""
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            logger.error(f"Failed to apply patch: {error_msg}")
            
            # Try to get more details
            try:
                check_result = self._run_git(["apply", "--check", patch_file], check=False)
                if check_result.returncode != 0:
                    error_msg += f"\nPatch check output: {check_result.stderr}"
            except:
                pass
            
            return False, error_msg
            
        finally:
            # Clean up temp file
            try:
                os.unlink(patch_file)
            except:
                pass
    
    def stage_changes(self, paths: Optional[List[str]] = None) -> bool:
        """
        Stage changes for commit.
        
        Args:
            paths: Specific paths to stage (all if None)
            
        Returns:
            True if successful
        """
        try:
            if paths:
                self._run_git(["add"] + paths)
            else:
                self._run_git(["add", "-A"])
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stage changes: {e}")
            return False
    
    def commit(self, message: str, author: Optional[str] = None) -> Optional[str]:
        """
        Create a commit.
        
        Args:
            message: Commit message
            author: Author in "Name <email>" format
            
        Returns:
            Commit SHA if successful, None otherwise
        """
        try:
            cmd = ["commit", "-m", message]
            
            if author:
                cmd.extend(["--author", author])
            
            self._run_git(cmd)
            
            # Get the commit SHA
            commit_sha = self.get_current_commit()
            logger.info(f"Created commit: {commit_sha}")
            
            return commit_sha
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create commit: {e}")
            return None
    
    def commit_changes(self, message: str, author: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Create a commit (wrapper for commit method).
        
        Args:
            message: Commit message
            author: Author in "Name <email>" format
            
        Returns:
            Tuple of (success, commit_sha)
        """
        commit_sha = self.commit(message, author)
        return (commit_sha is not None, commit_sha)
    
    def push_branch(self, branch_name: Optional[str] = None, force: bool = False) -> bool:
        """
        Push branch to remote.
        
        Args:
            branch_name: Branch to push (current if None)
            force: Force push
            
        Returns:
            True if successful
        """
        try:
            cmd = ["push", "origin"]
            
            if branch_name:
                cmd.append(branch_name)
            else:
                cmd.append("HEAD")
            
            if force:
                cmd.append("--force")
            
            self._run_git(cmd)
            logger.info(f"Pushed branch: {branch_name or 'current'}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to push branch: {e}")
            return False
    
    def get_diff(self, staged: bool = True) -> str:
        """
        Get the current diff.
        
        Args:
            staged: Get staged diff (vs unstaged)
            
        Returns:
            Diff output
        """
        try:
            cmd = ["diff"]
            if staged:
                cmd.append("--cached")
            
            result = self._run_git(cmd)
            return result.stdout
            
        except subprocess.CalledProcessError:
            return ""
    
    def reset_changes(self, hard: bool = False):
        """
        Reset changes in the working directory.
        
        Args:
            hard: Do a hard reset (loses all changes)
        """
        try:
            if hard:
                self._run_git(["reset", "--hard", "HEAD"])
            else:
                self._run_git(["reset", "HEAD"])
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to reset changes: {e}")
    
    def merge_branch(self, branch_name: str, no_ff: bool = True) -> Tuple[bool, str]:
        """
        Merge a branch into the current branch.
        
        Args:
            branch_name: Name of the branch to merge
            no_ff: Use --no-ff to create a merge commit even for fast-forward
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if branch exists
            branches_result = self._run_git(["branch", "-a"])
            if branch_name not in branches_result.stdout:
                return False, f"Branch {branch_name} does not exist"
            
            # Perform merge
            merge_args = ["merge", branch_name]
            if no_ff:
                merge_args.append("--no-ff")
            merge_args.extend(["-m", f"Merge branch '{branch_name}'"])
            
            result = self._run_git(merge_args)
            
            # Check for conflicts
            status_result = self._run_git(["status", "--porcelain"])
            if status_result.stdout.strip():
                # There are conflicts
                return False, "Merge conflicts detected"
            
            logger.info(f"Successfully merged branch: {branch_name}")
            return True, f"Merged {branch_name} successfully"
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to merge branch {branch_name}: {e.stderr}")
            return False, f"Merge failed: {e.stderr}"
    
    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        result = self._run_git(["status", "--porcelain"])
        return bool(result.stdout.strip())
    
    def get_current_commit_hash(self) -> str:
        """Get the current commit hash."""
        result = self._run_git(["rev-parse", "HEAD"])
        return result.stdout.strip()
    
    def delete_branch(self, branch_name: str, force: bool = False) -> bool:
        """
        Delete a branch.
        
        Args:
            branch_name: Name of the branch to delete
            force: Force delete even if not merged
            
        Returns:
            True if successful
        """
        try:
            cmd = ["branch", "-d" if not force else "-D", branch_name]
            self._run_git(cmd)
            logger.info(f"Deleted branch: {branch_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to delete branch {branch_name}: {e}")
            return False
    
    def find_commits_by_pattern(self, pattern: str, max_count: int = 10) -> List[str]:
        """
        Find commits with messages matching a pattern.
        
        Args:
            pattern: Regex pattern to search for
            max_count: Maximum number of commits to return
            
        Returns:
            List of commit hashes
        """
        try:
            result = self._run_git([
                "log", 
                f"--grep={pattern}", 
                "--format=%H",
                f"-{max_count}"
            ])
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        except subprocess.CalledProcessError:
            return []
    
    def stage_all_changes(self) -> bool:
        """Stage all changes for commit."""
        try:
            self._run_git(["add", "-A"])
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stage changes: {e}")
            return False
    
    def _run_git(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """
        Run a git command.
        
        Args:
            args: Git command arguments
            check: Check return code
            
        Returns:
            Completed process result
        """
        cmd = ["git"] + args
        
        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=check
        )
        
        return result