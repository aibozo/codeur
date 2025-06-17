"""
Git Workflow Management System

This module provides a comprehensive Git workflow for the multi-agent system,
including branch management, atomic commits, checkpoints, and reversion capabilities.
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from ..coding_agent.git_operations import GitOperations
from .logging import get_logger

logger = get_logger(__name__)


class BranchType(Enum):
    """Types of branches in the workflow."""
    MAIN = "main"
    WORKING = "working"
    TASK = "task"
    FIX = "fix"
    EXPERIMENT = "experiment"
    CHECKPOINT = "checkpoint"


class CommitType(Enum):
    """Types of commits."""
    FEATURE = "feature"
    FIX = "fix"
    REFACTOR = "refactor"
    TEST = "test"
    DOCS = "docs"
    CHORE = "chore"


class MergeStrategy(Enum):
    """Merge strategies for branches."""
    MERGE = "merge"
    SQUASH = "squash"
    REBASE = "rebase"


@dataclass
class BranchNamingConfig:
    """Configuration for branch naming conventions."""
    session_prefix: str = "working/session"
    task_prefix: str = "task"
    fix_prefix: str = "fix"
    experiment_prefix: str = "experiment"
    checkpoint_prefix: str = "checkpoint"
    max_description_length: int = 50
    separator: str = "-"


@dataclass
class CommitMetadata:
    """Metadata for atomic commits."""
    task_id: str
    agent_type: str
    description: str
    files_modified: List[str]
    test_status: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_commit_message(self) -> str:
        """Generate formatted commit message."""
        lines = [
            f"[TASK-{self.task_id}] {self.description}",
            "",
            f"Agent: {self.agent_type}",
            f"Task: {self.description}",
            f"Files: {', '.join(self.files_modified)}",
        ]
        
        if self.test_status:
            lines.append(f"Tests: {self.test_status}")
            
        if self.dependencies:
            lines.append(f"Dependencies: {', '.join(self.dependencies)}")
            
        return "\n".join(lines)


@dataclass
class Checkpoint:
    """Represents a save point in the workflow."""
    id: str
    branch_name: str
    description: str
    timestamp: datetime
    commit_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class GitWorkflow:
    """
    Manages Git workflow for the multi-agent system.
    
    Provides branch management, atomic commits, checkpoints,
    and reversion capabilities.
    """
    
    def __init__(self, repo_path: str, event_bridge=None, naming_config: Optional[BranchNamingConfig] = None, gitless_mode: bool = False):
        """
        Initialize Git workflow.
        
        Args:
            repo_path: Path to the project repository
            event_bridge: Event bridge for publishing git events
            naming_config: Branch naming configuration
            gitless_mode: If True, skip all Git operations
        """
        self.project_path = Path(repo_path)
        self.repo_path = repo_path  # Keep both for compatibility
        self.event_bridge = event_bridge
        self.naming_config = naming_config or BranchNamingConfig()
        self.gitless_mode = gitless_mode
        self.git_ops = GitOperations(str(repo_path)) if not gitless_mode else None
        
        # Current session info
        self.session_id = None
        self.working_branch = None
        self.active_tasks = {}  # task_id -> branch_name
        
        # Checkpoint management
        self.checkpoints = []
        
        # Configuration
        self.config = {
            "auto_checkpoint_interval": 3600,  # 1 hour
            "max_file_size": 10 * 1024 * 1024,  # 10MB
            "require_tests": True,
            "enforce_linear_history": True,
            "checkpoint_on_success": True,
        }
        
    def initialize_session(self, user_id: str = "default", session_id: Optional[str] = None) -> Optional[str]:
        """
        Initialize a new session with a working branch.
        
        Args:
            user_id: User identifier for the session
            session_id: Optional session ID (generated if not provided)
            
        Returns:
            Name of the created working branch
        """
        if self.gitless_mode:
            logger.info("Gitless mode - skipping session initialization")
            return None
            
        # Generate session ID if not provided
        if session_id:
            self.session_id = session_id
        else:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self.session_id = f"{timestamp}-{user_id}"
        
        # Create working branch name
        self.working_branch = f"working/session-{self.session_id}"
        
        # Ensure we're on main branch first
        current_branch = self.git_ops.get_current_branch()
        if current_branch != "main":
            if not self.git_ops.checkout_branch("main"):
                logger.error("Failed to checkout main branch")
                return None
                
        # Create and checkout working branch
        if not self.git_ops.create_branch(self.working_branch):
            logger.error(f"Failed to create working branch: {self.working_branch}")
            return None
            
        logger.info(f"Initialized session with working branch: {self.working_branch}")
        
        # Create initial checkpoint
        self.create_checkpoint("session-start", auto=True)
        
        return self.working_branch
        
    def create_task_branch(self, task_id: str, description: str, agent_id: str = None) -> Optional[str]:
        """
        Create a task branch for a specific task.
        
        Args:
            task_id: Unique task identifier
            description: Short description of the task
            
        Returns:
            Name of the created task branch
        """
        if self.gitless_mode:
            return None
            
        # Sanitize description for branch name
        safe_desc = re.sub(r'[^a-zA-Z0-9-]', '-', description.lower())
        safe_desc = re.sub(r'-+', '-', safe_desc).strip('-')[:50]
        
        # Create branch name
        branch_name = f"task/{task_id}/{safe_desc}"
        
        # Ensure we're on working branch
        if self.git_ops.get_current_branch() != self.working_branch:
            if not self.git_ops.checkout_branch(self.working_branch):
                logger.error(f"Failed to checkout working branch: {self.working_branch}")
                return None
                
        # Create and checkout task branch
        if not self.git_ops.create_branch(branch_name):
            logger.error(f"Failed to create task branch: {branch_name}")
            return None
            
        # Track active task
        self.active_tasks[task_id] = branch_name
        
        logger.info(f"Created task branch: {branch_name}")
        return branch_name
        
    def commit_task(self, task_id: str, metadata: CommitMetadata) -> Optional[str]:
        """
        Create an atomic commit for a task.
        
        Args:
            task_id: Task identifier
            metadata: Commit metadata
            
        Returns:
            Commit hash if successful
        """
        if self.gitless_mode:
            return None
            
        # Ensure we're on the task branch
        task_branch = self.active_tasks.get(task_id)
        if not task_branch:
            logger.error(f"No active branch for task: {task_id}")
            return None
            
        current_branch = self.git_ops.get_current_branch()
        if current_branch != task_branch:
            if not self.git_ops.checkout_branch(task_branch):
                logger.error(f"Failed to checkout task branch: {task_branch}")
                return None
                
        # Stage all changes
        self.git_ops.stage_all_changes()
        
        # Create commit
        commit_message = metadata.to_commit_message()
        success, commit_hash = self.git_ops.commit_changes(commit_message)
        
        if not success:
            logger.error(f"Failed to commit changes for task: {task_id}")
            return None
            
        logger.info(f"Created atomic commit {commit_hash} for task {task_id}")
        return commit_hash
        
    def merge_task_to_working(self, task_id: str, squash: bool = True, agent_id: str = None, strategy: MergeStrategy = None) -> Tuple[bool, str]:
        """
        Merge a task branch back to the working branch.
        
        Args:
            task_id: Task identifier
            squash: Whether to squash commits
            agent_id: Agent performing the merge (optional)
            strategy: Merge strategy to use (optional)
            
        Returns:
            Tuple of (success, message)
        """
        if self.gitless_mode:
            return True, "Gitless mode - no merge needed"
            
        # Use provided strategy or default to squash
        if strategy == MergeStrategy.SQUASH or squash:
            squash = True
        elif strategy == MergeStrategy.MERGE:
            squash = False
            
        task_branch = self.active_tasks.get(task_id)
        if not task_branch:
            msg = f"No active branch for task: {task_id}"
            logger.error(msg)
            return False, msg
            
        # Checkout working branch
        if not self.git_ops.checkout_branch(self.working_branch):
            msg = f"Failed to checkout working branch: {self.working_branch}"
            logger.error(msg)
            return False, msg
            
        # Merge task branch
        if squash:
            # Squash merge for clean history
            success = self._squash_merge(task_branch, f"[TASK-{task_id}] Merged")
        else:
            success, _ = self.git_ops.merge_branch(task_branch)
            
        if not success:
            msg = f"Failed to merge task branch: {task_branch}"
            logger.error(msg)
            return False, msg
            
        # Delete task branch
        self.git_ops.delete_branch(task_branch)
        del self.active_tasks[task_id]
        
        msg = f"Successfully merged task {task_id} to working branch"
        logger.info(msg)
        
        # Auto-checkpoint if configured
        if self.config.get("checkpoint_on_success"):
            self.create_checkpoint(f"after-task-{task_id}", auto=True)
            
        return True, msg
        
    def _squash_merge(self, branch: str, message: str) -> bool:
        """Perform a squash merge."""
        try:
            if self.git_ops.repo:
                # Use GitPython if available
                # Get the merge base
                result = self.git_ops.repo.git.merge_base("HEAD", branch)
                merge_base = result.strip()
                
                # Reset to merge base
                self.git_ops.repo.git.reset("--soft", merge_base)
                
                # Cherry-pick changes from branch
                self.git_ops.repo.git.cherry_pick("--no-commit", f"{merge_base}..{branch}")
                
                # Commit with message
                self.git_ops.repo.index.commit(message)
            else:
                # Fallback to regular merge if GitPython not available
                success, _ = self.git_ops.merge_branch(branch)
                return success
            
            return True
        except Exception as e:
            logger.error(f"Squash merge failed: {e}")
            return False
            
    def create_checkpoint(self, description: str, auto: bool = False) -> Optional[Checkpoint]:
        """
        Create a checkpoint (save point).
        
        Args:
            description: Checkpoint description
            auto: Whether this is an automatic checkpoint
            
        Returns:
            Created checkpoint object
        """
        if self.gitless_mode:
            return None
            
        # Generate checkpoint ID with microsecond precision to ensure uniqueness
        timestamp = datetime.now()
        checkpoint_id = timestamp.strftime("%Y%m%d-%H%M%S-%f")[:21]  # Include microseconds but truncate to milliseconds
        
        # Create checkpoint branch name
        safe_desc = re.sub(r'[^a-zA-Z0-9-]', '-', description.lower())[:30]
        branch_name = f"checkpoint/{checkpoint_id}-{safe_desc}"
        
        # Get current commit
        current_commit = self.git_ops.get_current_commit_hash()
        
        # Create checkpoint branch
        current_branch = self.git_ops.get_current_branch()
        if not self.git_ops.create_branch(branch_name):
            logger.error(f"Failed to create checkpoint branch: {branch_name}")
            return None
            
        # Return to original branch
        self.git_ops.checkout_branch(current_branch)
        
        # Create checkpoint object
        checkpoint = Checkpoint(
            id=checkpoint_id,
            branch_name=branch_name,
            description=description,
            timestamp=timestamp,
            commit_hash=current_commit,
            metadata={
                "auto": auto,
                "session_id": self.session_id,
                "active_tasks": list(self.active_tasks.keys())
            }
        )
        
        self.checkpoints.append(checkpoint)
        
        logger.info(f"Created checkpoint: {checkpoint_id} - {description}")
        return checkpoint
        
    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Restore project state to a checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to restore
            
        Returns:
            True if restoration successful
        """
        if self.gitless_mode:
            return True
            
        # Find checkpoint
        checkpoint = None
        for cp in self.checkpoints:
            if cp.id == checkpoint_id:
                checkpoint = cp
                break
                
        if not checkpoint:
            logger.error(f"Checkpoint not found: {checkpoint_id}")
            return False
            
        # Create restoration branch
        restore_branch = f"restore/{checkpoint_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Checkout checkpoint branch
        if not self.git_ops.checkout_branch(checkpoint.branch_name):
            logger.error(f"Failed to checkout checkpoint branch: {checkpoint.branch_name}")
            return False
            
        # Create new branch from checkpoint
        if not self.git_ops.create_branch(restore_branch):
            logger.error(f"Failed to create restoration branch: {restore_branch}")
            return False
            
        # Update working branch reference
        self.working_branch = restore_branch
        
        logger.info(f"Restored to checkpoint: {checkpoint_id}")
        return True
        
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        List all available checkpoints.
        
        Returns:
            List of checkpoint information
        """
        checkpoint_list = []
        for cp in self.checkpoints:
            checkpoint_list.append({
                "id": cp.id,
                "description": cp.description,
                "timestamp": cp.timestamp.isoformat(),
                "branch_name": cp.branch_name,
                "auto": cp.metadata.get("auto", False)
            })
        return checkpoint_list
        
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        Get a specific checkpoint by ID.
        
        Args:
            checkpoint_id: ID of the checkpoint
            
        Returns:
            Checkpoint object if found
        """
        for cp in self.checkpoints:
            if cp.id == checkpoint_id:
                return cp
        return None
        
    def revert_task(self, task_id: str, cascade: bool = True) -> bool:
        """
        Revert changes from a specific task.
        
        Args:
            task_id: Task to revert
            cascade: Whether to revert dependent tasks
            
        Returns:
            True if reversion successful
        """
        if self.gitless_mode:
            return True
            
        # Find commit for task
        commit_pattern = f"\\[TASK-{task_id}\\]"
        commits = self.git_ops.find_commits_by_pattern(commit_pattern)
        
        if not commits:
            logger.error(f"No commits found for task: {task_id}")
            return False
            
        # Get the commit to revert
        commit_to_revert = commits[0]
        
        try:
            # Create revert commit
            if self.git_ops.repo:
                self.git_ops.repo.git.revert("--no-edit", commits[0])
            else:
                # Use subprocess fallback
                import subprocess
                subprocess.run(
                    ["git", "revert", "--no-edit", commits[0]], 
                    cwd=str(self.project_path),
                    check=True
                )
            
            logger.info(f"Successfully reverted task: {task_id}")
            
            # Handle cascade reversion if needed
            if cascade:
                # Find dependent tasks by analyzing commit messages
                dependent_tasks = self._find_dependent_tasks(task_id)
                if dependent_tasks:
                    logger.info(f"Found {len(dependent_tasks)} dependent tasks to revert")
                    # Revert in reverse order
                    for dep_task_id in reversed(dependent_tasks):
                        logger.info(f"Reverting dependent task: {dep_task_id}")
                        self.revert_task(dep_task_id, cascade=False)  # Avoid infinite recursion
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to revert task {task_id}: {e}")
            return False
            
    def get_task_history(self) -> List[Dict[str, Any]]:
        """
        Get history of all tasks in current session.
        
        Returns:
            List of task history entries
        """
        if self.gitless_mode:
            return []
            
        history = []
        
        # Get commits from working branch
        try:
            if self.git_ops.repo:
                commits = list(self.git_ops.repo.iter_commits(self.working_branch))
                
                for commit in commits:
                    # Parse task info from commit message
                    match = re.search(r'\[TASK-([^\]]+)\]', commit.message)
                    if match:
                        task_id = match.group(1)
                        
                        # Extract metadata from commit message
                        lines = commit.message.split('\n')
                        agent = None
                        files = []
                        
                        for line in lines:
                            if line.startswith("Agent:"):
                                agent = line.split(":", 1)[1].strip()
                            elif line.startswith("Files:"):
                                files = [f.strip() for f in line.split(":", 1)[1].split(",")]
                                
                        history.append({
                            "task_id": task_id,
                            "commit": commit.hexsha,
                            "timestamp": commit.committed_datetime,
                            "agent": agent,
                            "files": files,
                            "message": lines[0] if lines else ""
                        })
            else:
                # Fallback to git log
                import subprocess
                result = subprocess.run(
                    ["git", "log", "--pretty=format:%H|%ai|%s", self.working_branch],
                    cwd=str(self.project_path),
                    capture_output=True,
                    text=True
                )
                
                for line in result.stdout.split('\n'):
                    if not line:
                        continue
                    parts = line.split('|', 2)
                    if len(parts) >= 3:
                        commit_hash, timestamp, message = parts
                        # Parse task info from commit message
                        match = re.search(r'\[TASK-([^\]]+)\]', message)
                        if match:
                            task_id = match.group(1)
                            history.append({
                                "task_id": task_id,
                                "commit": commit_hash,
                                "timestamp": timestamp,
                                "agent": None,  # Would need to parse from message
                                "files": [],    # Would need to parse from message
                                "message": message
                            })
                    
        except Exception as e:
            logger.error(f"Failed to get task history: {e}")
            
        return history
        
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task information including commit, files, etc.
        """
        if self.gitless_mode:
            return None
            
        # Find commit for task
        commit_pattern = f"\\[TASK-{task_id}\\]"
        commits = self.git_ops.find_commits_by_pattern(commit_pattern)
        
        if not commits:
            return None
            
        commit_hash = commits[0]
        
        try:
            # Get commit details
            import subprocess
            
            # Get commit message
            msg_result = subprocess.run(
                ["git", "show", "-s", "--format=%B", commit_hash],
                cwd=str(self.project_path),
                capture_output=True,
                text=True
            )
            
            # Get changed files
            files_result = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
                cwd=str(self.project_path),
                capture_output=True,
                text=True
            )
            
            # Parse commit message for metadata
            message_lines = msg_result.stdout.split('\n') if msg_result.returncode == 0 else []
            agent = None
            description = ""
            
            for line in message_lines:
                if line.startswith("Agent:"):
                    agent = line.split(":", 1)[1].strip()
                elif line.startswith("Task:"):
                    description = line.split(":", 1)[1].strip()
                    
            files = files_result.stdout.strip().split('\n') if files_result.returncode == 0 else []
            
            # Find dependent tasks
            dependent_tasks = self._find_dependent_tasks(task_id)
            
            return {
                "task_id": task_id,
                "commit": commit_hash,
                "agent": agent,
                "description": description,
                "files": files,
                "dependent_tasks": dependent_tasks,
                "branch": self.active_tasks.get(task_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to get task info: {e}")
            return None
        
    def cleanup_session(self) -> bool:
        """
        Clean up session branches and resources.
        
        Returns:
            True if cleanup successful
        """
        if self.gitless_mode:
            return True
            
        # Clean up any remaining task branches
        for task_id, branch in list(self.active_tasks.items()):
            try:
                self.git_ops.delete_branch(branch)
                logger.info(f"Cleaned up task branch: {branch}")
            except Exception as e:
                logger.warning(f"Failed to clean up branch {branch}: {e}")
                
        self.active_tasks.clear()
        
        # Create final checkpoint
        self.create_checkpoint("session-end", auto=True)
        
        logger.info("Session cleanup completed")
        return True
        
    def can_merge_to_main(self, agent_type: str) -> bool:
        """
        Check if an agent can merge to main branch.
        
        Args:
            agent_type: Type of agent requesting merge
            
        Returns:
            True if agent can merge to main
        """
        # Only architect can merge to main
        return agent_type == "architect"
        
    def merge_to_main(self, message: str = None) -> bool:
        """
        Merge working branch to main (requires architect approval).
        
        Args:
            message: Merge commit message
            
        Returns:
            True if merge successful
        """
        if self.gitless_mode:
            return True
            
        # Checkout main branch
        if not self.git_ops.checkout_branch("main"):
            logger.error("Failed to checkout main branch")
            return False
            
        # Merge working branch
        if not message:
            message = f"Merge session {self.session_id} to main"
            
        success, _ = self.git_ops.merge_branch(self.working_branch, message)
        
        if not success:
            logger.error("Failed to merge to main")
            return False
            
        logger.info("Successfully merged working branch to main")
        return True
        
    # Async wrapper methods for agent_factory compatibility
    async def start_session(self, session_id: str, user_id: str = "default") -> Optional[str]:
        """
        Start a new session with a working branch (async wrapper).
        
        Args:
            session_id: Session identifier
            user_id: User identifier for the session
            
        Returns:
            Name of the created working branch
        """
        return self.initialize_session(user_id, session_id)
        
    async def create_task_branch_async(self, task_id: str, description: str, agent_id: str = "system") -> Optional[str]:
        """
        Create a task branch for a specific task (async wrapper).
        
        Args:
            task_id: Unique task identifier
            description: Short description of the task
            agent_id: Agent that will work on this task
            
        Returns:
            Name of the created task branch
        """
        # Call the non-async version
        return self.create_task_branch(task_id, description)
        
    async def merge_task_to_working_async(self, task_id: str, agent_id: str = None, strategy: MergeStrategy = None) -> Tuple[bool, str]:
        """
        Merge a task branch back to the working branch (async wrapper).
        
        Args:
            task_id: Task identifier
            agent_id: Agent performing the merge
            strategy: Merge strategy to use
            
        Returns:
            Tuple of (success, message)
        """
        # Call the non-async version
        return self.merge_task_to_working(task_id, squash=(strategy == MergeStrategy.SQUASH), agent_id=agent_id, strategy=strategy)
        
    async def commit_atomic(self, task_id: str, agent_id: str, message: str, commit_type: 'CommitType' = None, metadata: Dict[str, Any] = None) -> Optional[str]:
        """
        Create an atomic commit for completed work.
        
        Args:
            task_id: Task identifier
            agent_id: Agent that did the work
            message: Commit message
            commit_type: Type of commit (feature, fix, etc.)
            metadata: Additional metadata for the commit
            
        Returns:
            Commit SHA if successful
        """
        # Create commit metadata
        commit_metadata = CommitMetadata(
            task_id=task_id,
            agent_type=agent_id,
            description=message,
            files_modified=self.git_ops.get_diff(staged=False).split('\n') if self.git_ops else []
        )
        
        return self.commit_task(task_id, commit_metadata)
        
    async def create_checkpoint_async(self, description: str) -> Optional[Checkpoint]:
        """
        Create a checkpoint (async wrapper).
        
        Args:
            description: Checkpoint description
            
        Returns:
            Created checkpoint object
        """
        # Call the non-async version
        return self.create_checkpoint(description, auto=False)
        
    def get_visual_history(self, max_commits: int = 20) -> str:
        """
        Get visual git history as text.
        
        Args:
            max_commits: Maximum number of commits to show
            
        Returns:
            Visual git history as text
        """
        if self.gitless_mode:
            return "Git operations disabled"
            
        try:
            # Use git log with graph
            import subprocess
            result = subprocess.run(
                ["git", "log", "--graph", "--oneline", "--decorate", f"-{max_commits}"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error getting git history: {result.stderr}"
                
        except Exception as e:
            logger.error(f"Failed to get visual history: {e}")
            return f"Failed to get git history: {str(e)}"
            
    def _find_dependent_tasks(self, task_id: str) -> List[str]:
        """
        Find tasks that depend on the given task.
        
        Args:
            task_id: Task to find dependencies for
            
        Returns:
            List of dependent task IDs
        """
        dependent_tasks = []
        
        # Get all commits after the task commit
        task_commit_pattern = f"\\[TASK-{task_id}\\]"
        task_commits = self.git_ops.find_commits_by_pattern(task_commit_pattern)
        
        if not task_commits:
            return dependent_tasks
            
        # Get all commits since this task
        try:
            import subprocess
            result = subprocess.run(
                ["git", "log", "--oneline", f"{task_commits[0]}..HEAD"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Parse task IDs from subsequent commits
                import re
                for line in result.stdout.split('\n'):
                    match = re.search(r'\[TASK-([^\]]+)\]', line)
                    if match:
                        dep_task_id = match.group(1)
                        if dep_task_id != task_id:
                            dependent_tasks.append(dep_task_id)
                            
        except Exception as e:
            logger.error(f"Failed to find dependent tasks: {e}")
            
        return dependent_tasks
        
    def revert_task_files(self, task_id: str, file_paths: List[str]) -> bool:
        """
        Selectively revert specific files from a task.
        
        Args:
            task_id: Task whose changes to revert
            file_paths: List of file paths to revert
            
        Returns:
            True if successful
        """
        if self.gitless_mode:
            return True
            
        # Find commit for task
        commit_pattern = f"\\[TASK-{task_id}\\]"
        commits = self.git_ops.find_commits_by_pattern(commit_pattern)
        
        if not commits:
            logger.error(f"No commits found for task: {task_id}")
            return False
            
        try:
            # Revert specific files from the commit
            import subprocess
            for file_path in file_paths:
                # Get the file content from before the commit
                result = subprocess.run(
                    ["git", "show", f"{commits[0]}~1:{file_path}"],
                    cwd=str(self.project_path),
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    # Write the old content back
                    full_path = self.project_path / file_path
                    full_path.write_text(result.stdout)
                    logger.info(f"Reverted {file_path} from task {task_id}")
                else:
                    # File didn't exist before this commit, so delete it
                    full_path = self.project_path / file_path
                    if full_path.exists():
                        full_path.unlink()
                        logger.info(f"Deleted {file_path} - was new in task {task_id}")
                    else:
                        logger.warning(f"Could not revert {file_path} - file not found")
                    
            # Stage and commit the selective reversion
            self.git_ops.stage_changes(file_paths)
            commit_msg = f"[REVERT] Selectively reverted files from task {task_id}\n\nFiles: {', '.join(file_paths)}"
            self.git_ops.commit(commit_msg)
            
            logger.info(f"Successfully reverted {len(file_paths)} files from task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to selectively revert files: {e}")
            return False