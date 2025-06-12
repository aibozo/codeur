"""
Git adapter for repository operations.

This module provides Git functionality for the Request Planner,
including repository cloning, branch management, and diff analysis.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

try:
    import git
    from git import Repo, GitCommandError
    HAS_GITPYTHON = True
except ImportError:
    HAS_GITPYTHON = False
    Repo = None
    GitCommandError = Exception

logger = logging.getLogger(__name__)


class GitAdapter:
    """
    Adapter for Git operations.
    
    Provides repository management, file operations, and diff analysis.
    """
    
    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialize the Git adapter.
        
        Args:
            repo_path: Path to existing repository (optional)
        """
        if not HAS_GITPYTHON:
            logger.warning("GitPython not installed. Git operations will be limited.")
        
        self.repo_path = repo_path
        self.repo = None
        
        if repo_path and repo_path.exists():
            self._load_repo(repo_path)
    
    def _load_repo(self, path: Path) -> bool:
        """Load an existing repository."""
        if not HAS_GITPYTHON:
            return False
            
        try:
            self.repo = Repo(path)
            self.repo_path = path
            logger.info(f"Loaded repository at {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load repository: {e}")
            return False
    
    def clone_repository(
        self, 
        url: str, 
        branch: str = "main",
        target_dir: Optional[Path] = None
    ) -> Tuple[bool, Optional[Path]]:
        """
        Clone a repository.
        
        Args:
            url: Repository URL
            branch: Branch to checkout
            target_dir: Target directory (temp if None)
            
        Returns:
            Tuple of (success, repo_path)
        """
        if not HAS_GITPYTHON:
            logger.error("GitPython not installed. Cannot clone repository.")
            return False, None
        
        try:
            # Create target directory
            if target_dir is None:
                target_dir = Path(tempfile.mkdtemp(prefix="agent_repo_"))
            
            # Clone repository
            logger.info(f"Cloning {url} to {target_dir}")
            self.repo = Repo.clone_from(url, target_dir, branch=branch)
            self.repo_path = target_dir
            
            logger.info(f"Successfully cloned repository to {target_dir}")
            return True, target_dir
            
        except GitCommandError as e:
            logger.error(f"Git command failed: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            return False, None
    
    def get_current_branch(self) -> Optional[str]:
        """Get the current branch name."""
        if not self.repo:
            return None
        
        try:
            return self.repo.active_branch.name
        except Exception:
            return None
    
    def checkout_branch(self, branch: str) -> bool:
        """
        Checkout a branch.
        
        Args:
            branch: Branch name
            
        Returns:
            Success status
        """
        if not self.repo:
            logger.error("No repository loaded")
            return False
        
        try:
            self.repo.git.checkout(branch)
            logger.info(f"Checked out branch: {branch}")
            return True
        except Exception as e:
            logger.error(f"Failed to checkout branch {branch}: {e}")
            return False
    
    def get_file_content(self, file_path: str, ref: str = "HEAD") -> Optional[str]:
        """
        Get file content at a specific ref.
        
        Args:
            file_path: Path to file relative to repo root
            ref: Git reference (commit, branch, tag)
            
        Returns:
            File content or None
        """
        if not self.repo:
            # Fallback to direct file reading
            if self.repo_path:
                full_path = self.repo_path / file_path
                if full_path.exists():
                    try:
                        return full_path.read_text(encoding='utf-8')
                    except Exception:
                        pass
            return None
        
        try:
            # Get content from Git
            blob = self.repo.oid(f"{ref}:{file_path}")
            return blob.data_stream.read().decode('utf-8')
        except Exception:
            # Fallback to direct reading for working tree
            if ref == "HEAD":
                full_path = self.repo_path / file_path
                if full_path.exists():
                    try:
                        return full_path.read_text(encoding='utf-8')
                    except Exception:
                        pass
            return None
    
    def get_changed_files(self, base_ref: str = "HEAD~1", target_ref: str = "HEAD") -> List[str]:
        """
        Get list of changed files between two refs.
        
        Args:
            base_ref: Base reference
            target_ref: Target reference
            
        Returns:
            List of changed file paths
        """
        if not self.repo:
            return []
        
        try:
            # Get diff between refs
            diff = self.repo.git.diff(base_ref, target_ref, name_only=True)
            if diff:
                return diff.strip().split('\n')
            return []
        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            return []
    
    def get_file_diff(
        self, 
        file_path: str, 
        base_ref: str = "HEAD~1", 
        target_ref: str = "HEAD"
    ) -> Optional[str]:
        """
        Get diff for a specific file.
        
        Args:
            file_path: Path to file
            base_ref: Base reference
            target_ref: Target reference
            
        Returns:
            Diff content or None
        """
        if not self.repo:
            return None
        
        try:
            diff = self.repo.git.diff(base_ref, target_ref, file_path)
            return diff
        except Exception as e:
            logger.error(f"Failed to get diff for {file_path}: {e}")
            return None
    
    def list_files(self, pattern: Optional[str] = None) -> List[str]:
        """
        List files in the repository.
        
        Args:
            pattern: Optional glob pattern
            
        Returns:
            List of file paths
        """
        if not self.repo_path:
            return []
        
        files = []
        
        # If we have a Git repo, use git ls-files
        if self.repo and HAS_GITPYTHON:
            try:
                if pattern:
                    output = self.repo.git.ls_files(pattern)
                else:
                    output = self.repo.git.ls_files()
                
                if output:
                    files = output.strip().split('\n')
                return files
            except Exception:
                # Fall through to filesystem scan
                pass
        
        # Fallback to filesystem scan
        if pattern:
            files = [str(p.relative_to(self.repo_path)) 
                    for p in self.repo_path.rglob(pattern)]
        else:
            files = [str(p.relative_to(self.repo_path)) 
                    for p in self.repo_path.rglob("*") if p.is_file()]
        
        # Filter out .git directory
        files = [f for f in files if not f.startswith('.git/')]
        return files
    
    def get_repo_info(self) -> Dict[str, Any]:
        """Get repository information."""
        info = {
            "path": str(self.repo_path) if self.repo_path else None,
            "is_git_repo": self.repo is not None,
            "current_branch": None,
            "remote_url": None,
            "last_commit": None
        }
        
        if self.repo:
            try:
                info["current_branch"] = self.repo.active_branch.name
            except Exception:
                pass
            
            try:
                if self.repo.remotes:
                    info["remote_url"] = self.repo.remotes.origin.url
            except Exception:
                pass
            
            try:
                last_commit = self.repo.head.commit
                info["last_commit"] = {
                    "hash": last_commit.hexsha[:8],
                    "message": last_commit.message.strip(),
                    "author": str(last_commit.author),
                    "date": last_commit.committed_datetime.isoformat()
                }
            except Exception:
                pass
        
        return info
    
    def create_branch(self, branch_name: str, base_ref: str = "HEAD") -> bool:
        """
        Create a new branch.
        
        Args:
            branch_name: Name for the new branch
            base_ref: Base reference for the branch
            
        Returns:
            Success status
        """
        if not self.repo:
            logger.error("No repository loaded")
            return False
        
        try:
            # Create new branch
            new_branch = self.repo.create_head(branch_name, base_ref)
            
            # Checkout the new branch
            new_branch.checkout()
            
            logger.info(f"Created and checked out branch: {branch_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create branch {branch_name}: {e}")
            return False
    
    def stage_file(self, file_path: str) -> bool:
        """
        Stage a file for commit.
        
        Args:
            file_path: Path to file
            
        Returns:
            Success status
        """
        if not self.repo:
            return False
        
        try:
            self.repo.index.add([file_path])
            logger.info(f"Staged file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to stage file {file_path}: {e}")
            return False
    
    def commit_changes(self, message: str) -> Optional[str]:
        """
        Commit staged changes.
        
        Args:
            message: Commit message
            
        Returns:
            Commit hash or None
        """
        if not self.repo:
            return None
        
        try:
            commit = self.repo.index.commit(message)
            logger.info(f"Created commit: {commit.hexsha[:8]}")
            return commit.hexsha
        except Exception as e:
            logger.error(f"Failed to commit changes: {e}")
            return None
    
    def cleanup(self):
        """Clean up temporary repository."""
        if self.repo_path and str(self.repo_path).startswith(tempfile.gettempdir()):
            try:
                shutil.rmtree(self.repo_path)
                logger.info(f"Cleaned up temporary repository: {self.repo_path}")
            except Exception as e:
                logger.error(f"Failed to cleanup repository: {e}")