"""
Branch Manager for handling git branch operations after task completion.

This module monitors task completion events and handles merging feature branches
back to the main branch when coding and test tasks complete successfully.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Set, Tuple
from pathlib import Path

from ..coding_agent.git_operations import GitOperations
from ..core.event_bridge import EventBridge
from .git_workflow import GitWorkflow, MergeStrategy
from .logging import get_logger

logger = get_logger(__name__)


class BranchManager:
    """
    Manages git branches for the multi-agent system.
    
    Monitors task completion and handles branch merging when appropriate.
    """
    
    def __init__(
        self,
        project_path: Path,
        event_bridge: EventBridge,
        target_branch: str = "main",
        gitless_mode: bool = False,
        simple_event_bridge = None,
        git_workflow: Optional[GitWorkflow] = None
    ):
        """
        Initialize the branch manager.
        
        Args:
            project_path: Path to the project repository
            event_bridge: Event bridge for monitoring task events
            target_branch: Target branch for merging (default: "main")
            gitless_mode: If True, skip all git operations
            git_workflow: Optional git workflow system for enhanced operations
        """
        self.project_path = project_path
        self.event_bridge = event_bridge
        self.target_branch = target_branch
        self.gitless_mode = gitless_mode
        self.simple_event_bridge = simple_event_bridge
        self.git_workflow = git_workflow
        
        if not gitless_mode:
            self.git_ops = GitOperations(str(project_path))
        else:
            self.git_ops = None
            
        # Track task groups and their branches
        self.task_groups: Dict[str, Dict[str, Any]] = {}
        
        # Subscribe to relevant events
        self._subscribe_to_events()
        
    def _subscribe_to_events(self):
        """Subscribe to task and code events."""
        # For now, we'll use the message bus directly if available
        if hasattr(self.event_bridge, 'message_bus'):
            # Subscribe to wildcard events and filter
            self.event_bridge.message_bus.subscribe("*", self._handle_event)
        else:
            logger.warning("EventBridge doesn't have message_bus, branch tracking may be limited")
            
    def _handle_event(self, event_type: str, data: Dict[str, Any]):
        """Handle all events and filter for ones we care about."""
        if event_type == "task.completed":
            asyncio.create_task(self._on_task_completed({"data": data}))
        elif event_type == "task.failed":
            asyncio.create_task(self._on_task_failed({"data": data}))
        elif event_type == "code.branch.created":
            asyncio.create_task(self._on_branch_created({"data": data}))
        
    def set_target_branch(self, branch_name: str):
        """
        Set the target branch for merging.
        
        Args:
            branch_name: Name of the target branch
        """
        self.target_branch = branch_name
        logger.info(f"Target branch set to: {branch_name}")
        
    def set_gitless_mode(self, enabled: bool):
        """
        Enable or disable gitless mode.
        
        Args:
            enabled: If True, skip all git operations
        """
        self.gitless_mode = enabled
        if enabled:
            self.git_ops = None
            logger.info("Gitless mode enabled - skipping all git operations")
        else:
            self.git_ops = GitOperations(str(self.project_path))
            logger.info("Gitless mode disabled - git operations enabled")
            
    async def _on_branch_created(self, event: Dict[str, Any]):
        """Handle branch creation events."""
        data = event.get("data", {})
        branch_name = data.get("branch_name")
        task_id = data.get("task_id")
        group_id = data.get("group_id") or task_id
        
        if branch_name and task_id:
            # Track this branch for the task group
            if group_id not in self.task_groups:
                self.task_groups[group_id] = {
                    "branches": set(),
                    "completed_tasks": set(),
                    "failed_tasks": set(),
                    "all_tasks": set()
                }
                
            self.task_groups[group_id]["branches"].add(branch_name)
            self.task_groups[group_id]["all_tasks"].add(task_id)
            
            logger.info(f"Tracking branch {branch_name} for task group {group_id}")
            
    async def _on_task_completed(self, event: Dict[str, Any]):
        """Handle task completion events."""
        data = event.get("data", {})
        task_id = data.get("task_id")
        task_type = data.get("agent_id", "").replace("_agent", "")
        group_id = data.get("group_id") or task_id
        
        if not task_id:
            return
            
        # Find the group this task belongs to
        for gid, group in self.task_groups.items():
            if task_id in group["all_tasks"]:
                group_id = gid
                break
                
        if group_id not in self.task_groups:
            return
            
        group = self.task_groups[group_id]
        group["completed_tasks"].add(task_id)
        
        # Check if all tasks in the group are completed
        if self._is_group_ready_for_merge(group_id):
            await self._merge_group_branches(group_id)
            
    async def _on_task_failed(self, event: Dict[str, Any]):
        """Handle task failure events."""
        data = event.get("data", {})
        task_id = data.get("task_id")
        
        if not task_id:
            return
            
        # Find the group this task belongs to
        for group_id, group in self.task_groups.items():
            if task_id in group["all_tasks"]:
                group["failed_tasks"].add(task_id)
                logger.warning(f"Task {task_id} failed in group {group_id}")
                break
                
    def _is_group_ready_for_merge(self, group_id: str) -> bool:
        """
        Check if a task group is ready for merging.
        
        A group is ready when:
        - All tasks are completed (no pending tasks)
        - No tasks have failed
        - There is at least one branch to merge
        """
        group = self.task_groups.get(group_id, {})
        
        if not group.get("branches"):
            return False
            
        # Check if all tasks are done (completed or failed)
        all_done = len(group["completed_tasks"]) + len(group["failed_tasks"]) == len(group["all_tasks"])
        
        # Check if any tasks failed
        has_failures = len(group["failed_tasks"]) > 0
        
        return all_done and not has_failures
        
    async def _merge_group_branches(self, group_id: str):
        """
        Merge all branches for a completed task group.
        
        Args:
            group_id: ID of the task group
        """
        if self.gitless_mode:
            logger.info(f"Gitless mode - skipping merge for group {group_id}")
            return
            
        group = self.task_groups[group_id]
        branches = group.get("branches", set())
        
        if not branches:
            return
            
        logger.info(f"Merging {len(branches)} branches for group {group_id}")
        
        merged_branches = []
        failed_branches = []
        
        # Use git workflow for enhanced merging if available
        if self.git_workflow:
            try:
                for branch in branches:
                    # Extract task_id from branch name for workflow merge
                    task_id = self._extract_task_id_from_branch(branch)
                    if task_id:
                        success, message = await self.git_workflow.merge_task_to_working(
                            task_id=task_id,
                            agent_id="branch_manager",
                            strategy=MergeStrategy.SQUASH
                        )
                        
                        if success:
                            merged_branches.append(branch)
                            logger.info(f"Successfully merged task branch {branch}")
                        else:
                            failed_branches.append((branch, message))
                            logger.error(f"Failed to merge task branch {branch}: {message}")
                    else:
                        # Fallback to basic merge for non-task branches
                        await self._fallback_merge_branch(branch, merged_branches, failed_branches)
                        
            except Exception as e:
                logger.error(f"Git workflow merge failed: {e}")
                # Fallback to basic git operations
                await self._fallback_merge_all(branches, merged_branches, failed_branches)
        else:
            # Use basic git operations
            await self._fallback_merge_all(branches, merged_branches, failed_branches)
            
        # Emit merge completion event
        if self.simple_event_bridge:
            await self.simple_event_bridge.emit({
                "type": "branch.merge.completed",
                "group_id": group_id,
                "target_branch": self.target_branch,
                "merged_branches": merged_branches,
                "failed_branches": failed_branches
            })
        
        # Clean up tracking
        del self.task_groups[group_id]
        
    def _extract_task_id_from_branch(self, branch_name: str) -> Optional[str]:
        """Extract task ID from branch name if it follows task branch naming convention."""
        # Handle task/* branches
        if branch_name.startswith("task/"):
            parts = branch_name.split("/")
            if len(parts) >= 2:
                return parts[1]
        # Handle feature/* branches (legacy)
        elif branch_name.startswith("feature/"):
            parts = branch_name.split("/")
            if len(parts) >= 2:
                return parts[1]
        return None
        
    async def _fallback_merge_branch(self, branch: str, merged_branches: list, failed_branches: list):
        """Fallback merge for a single branch using basic git operations."""
        success, message = self.git_ops.merge_branch(branch)
        
        if success:
            merged_branches.append(branch)
            logger.info(f"Successfully merged branch {branch}")
        else:
            failed_branches.append((branch, message))
            logger.error(f"Failed to merge branch {branch}: {message}")
            
    async def _fallback_merge_all(self, branches: set, merged_branches: list, failed_branches: list):
        """Fallback merge for all branches using basic git operations."""
        # Save current branch
        original_branch = self.git_ops.get_current_branch()
        
        try:
            # Checkout target branch
            if not self.git_ops.checkout_branch(self.target_branch):
                logger.error(f"Failed to checkout target branch {self.target_branch}")
                return
                
            # Merge each feature branch
            for branch in branches:
                await self._fallback_merge_branch(branch, merged_branches, failed_branches)
                    
        finally:
            # Return to original branch
            if original_branch != self.target_branch:
                self.git_ops.checkout_branch(original_branch)
                
    async def create_feature_branch(self, task_id: str, branch_prefix: str = "feature") -> Optional[str]:
        """
        Create a feature branch for a task.
        
        Args:
            task_id: ID of the task
            branch_prefix: Prefix for the branch name
            
        Returns:
            Branch name if created, None otherwise
        """
        if self.gitless_mode:
            return None
            
        # Generate branch name
        branch_name = f"{branch_prefix}/{task_id}"
        
        # Create branch
        if self.git_ops.create_branch(branch_name):
            # Emit branch created event
            if self.simple_event_bridge:
                await self.simple_event_bridge.emit({
                    "type": "code.branch.created",
                    "task_id": task_id,
                    "branch_name": branch_name
                })
            
            return branch_name
            
        return None
        
    def get_task_group_status(self, group_id: str) -> Dict[str, Any]:
        """
        Get the status of a task group.
        
        Args:
            group_id: ID of the task group
            
        Returns:
            Status information
        """
        group = self.task_groups.get(group_id, {})
        
        return {
            "exists": bool(group),
            "branches": list(group.get("branches", [])),
            "total_tasks": len(group.get("all_tasks", [])),
            "completed_tasks": len(group.get("completed_tasks", [])),
            "failed_tasks": len(group.get("failed_tasks", [])),
            "ready_for_merge": self._is_group_ready_for_merge(group_id)
        }