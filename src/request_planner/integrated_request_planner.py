"""
Request Planner agent integrated with task graph and RAG systems.

This shows how to extend the IntegratedAgentBase to create a fully
integrated agent that can:
- Create and manage tasks in the task graph
- Search RAG for similar past implementations
- Coordinate with other agents via events
"""

import logging
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

from ..core.integrated_agent_base import (
    IntegratedAgentBase, AgentContext, IntegrationLevel, AgentCapability
)
from ..architect.enhanced_task_graph import TaskPriority, TaskStatus
from .planner import RequestPlanner
from .models import StepKind
from ..core.logging import get_logger

logger = get_logger(__name__)


class IntegratedRequestPlanner(IntegratedAgentBase, RequestPlanner):
    """
    Request Planner with full task graph and RAG integration.
    
    This agent:
    - Breaks down user requests into executable tasks
    - Creates task hierarchies in the task graph
    - Searches RAG for similar past implementations
    - Coordinates task execution with other agents
    """
    
    def __init__(self, context: AgentContext):
        """Initialize integrated request planner."""
        # Initialize base classes
        IntegratedAgentBase.__init__(self, context)
        RequestPlanner.__init__(
            self,
            repo_path=str(context.project_path),
            use_llm=context.rag_client is not None
        )
        
        # Track active plans
        self.active_plans: Dict[str, str] = {}  # plan_id -> root_task_id
        
        # Configuration for parallel execution
        self.parallel_coding_tasks = False  # Default to serial for safety
        
    def get_integration_level(self) -> IntegrationLevel:
        """Request planner needs full integration."""
        return IntegrationLevel.FULL
        
    def get_capabilities(self) -> Set[AgentCapability]:
        """Request planner capabilities."""
        return {
            AgentCapability.PLANNING,
            AgentCapability.TASK_DECOMPOSITION,
            AgentCapability.COORDINATION
        }
        
    def set_parallel_coding_mode(self, enabled: bool = False):
        """
        Enable or disable parallel coding tasks.
        
        Args:
            enabled: If True, coding tasks can run in parallel.
                    If False (default), coding tasks run serially to avoid merge conflicts.
        
        Note: Test tasks are always serial and dependent on their related coding tasks.
        """
        self.parallel_coding_tasks = enabled
        logger.info(f"Parallel coding tasks mode set to: {enabled}")
        
    async def plan_request(self, request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Plan a user request with full integration.
        
        This overrides the base plan_request to add:
        - Task graph creation
        - RAG context retrieval
        - Agent coordination
        """
        logger.info(f"Planning request with integration: {request[:100]}...")
        
        # Search RAG for similar past requests
        similar_plans = await self._find_similar_plans(request)
        
        # Create a ChangeRequest object for the parent planner
        from .models import ChangeRequest
        import uuid
        
        change_request = ChangeRequest(
            id=str(uuid.uuid4()),
            description=request,
            repo=self.repo_path,
            branch="main",
            requester="integrated_planner"
        )
        
        # Create base plan using parent class
        base_plan_obj = self.create_plan(change_request)
        
        # Convert Plan object to dict format
        base_plan = {
            "id": base_plan_obj.id,
            "tasks": [
                {
                    "id": f"task_{i}",
                    "title": step.goal,
                    "description": " ".join(step.hints) if step.hints else step.goal,
                    "type": self._get_task_type_from_step_kind(step.kind),
                    "priority": "medium",
                    "dependencies": []
                }
                for i, step in enumerate(base_plan_obj.steps)
            ],
            "rationale": base_plan_obj.rationale,
            "affected_paths": base_plan_obj.affected_paths
        }
        
        # Enhance plan with RAG insights
        if similar_plans:
            base_plan = self._enhance_plan_with_history(base_plan, similar_plans)
            
        # Create task graph from plan
        root_task_id = await self._create_task_graph_from_plan(base_plan, request)
        
        # Store plan mapping
        plan_id = base_plan.get("id", "default")
        self.active_plans[plan_id] = root_task_id
        
        # Emit planning complete event
        if self._event_integration:
            await self._event_integration.publish_event("planning.complete", {
                "request": request,
                "plan_id": plan_id,
                "root_task_id": root_task_id,
                "task_count": len(base_plan.get("tasks", []))
            })
            
        return {
            **base_plan,
            "root_task_id": root_task_id,
            "similar_plans": len(similar_plans)
        }
        
    async def _find_similar_plans(self, request: str) -> List[Dict[str, Any]]:
        """Find similar past plans in RAG."""
        if not self._rag_integration:
            return []
            
        # Search for similar requests
        results = await self._rag_integration.search_knowledge(
            f"request plan: {request}",
            filter_type="plan",
            limit=3
        )
        
        return results
        
    def _enhance_plan_with_history(self, 
                                 plan: Dict[str, Any], 
                                 similar_plans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhance plan based on similar past plans."""
        # Extract useful patterns from past plans
        common_steps = []
        common_issues = []
        
        for similar in similar_plans:
            metadata = similar.get("metadata", {})
            if "successful_steps" in metadata:
                common_steps.extend(metadata["successful_steps"])
            if "issues_encountered" in metadata:
                common_issues.extend(metadata["issues_encountered"])
                
        # Add insights to plan
        if common_steps:
            plan["historical_insights"] = {
                "recommended_steps": list(set(common_steps)),
                "potential_issues": list(set(common_issues))
            }
            
        return plan
        
    async def _create_task_graph_from_plan(self, 
                                         plan: Dict[str, Any], 
                                         request: str) -> str:
        """Create task graph from plan with smart dependencies."""
        if not self._task_integration:
            return ""
            
        # Create root task
        root_task_id = await self._task_integration.create_subtask(
            parent_task_id=None,  # Root task has no parent
            title=f"Execute: {request[:50]}...",
            description=request,
            agent_type="request_planner",
            priority=TaskPriority.HIGH
        )
        
        # All tasks in this plan will share the same group ID
        group_id = root_task_id
        
        # Group tasks by type and track relationships
        coding_tasks = []  # (task_dict, task_id)
        test_tasks = []    # (task_dict, task_id, related_coding_task)
        other_tasks = []   # (task_dict, task_id)
        
        # First pass: categorize tasks
        tasks = plan.get("tasks", [])
        for i, task in enumerate(tasks):
            task_type = task.get("type", "coding_agent")
            
            if task_type == "coding_agent":
                coding_tasks.append((task, None))
            elif task_type == "test_agent":
                # Find related coding task (usually the previous coding task)
                related_coding_idx = None
                # Look for coding task with similar title/description
                task_title_lower = task["title"].lower()
                for j, (coding_task, _) in enumerate(coding_tasks):
                    coding_title_lower = coding_task["title"].lower()
                    # Check if they mention the same method/function
                    if any(word in task_title_lower and word in coding_title_lower 
                           for word in ["power", "square", "sqrt", "divide", "multiply"]):
                        related_coding_idx = j
                        break
                test_tasks.append((task, None, related_coding_idx))
            else:
                other_tasks.append((task, None))
        
        # Second pass: create coding tasks
        last_coding_task_id = None
        for i, (task, _) in enumerate(coding_tasks):
            # Enhance task with file context
            enhanced_task = dict(task)
            if "affected_paths" in plan and plan["affected_paths"]:
                enhanced_task["context"] = {
                    "target_files": plan["affected_paths"]
                }
            
            task_id = await self._task_integration.create_subtask(
                parent_task_id=root_task_id,
                title=enhanced_task["title"],
                description=enhanced_task.get("description", ""),
                agent_type="coding_agent",
                priority=TaskPriority.HIGH,
                metadata=enhanced_task.get("context", {})
            )
            
            coding_tasks[i] = (task, task_id)
            
            # Add dependency on previous coding task if serial mode
            if not self.parallel_coding_tasks and last_coding_task_id:
                await self._task_integration.add_task_dependency(
                    task_id,
                    last_coding_task_id
                )
            
            last_coding_task_id = task_id
            
            # Assign to agent with group ID
            await self._assign_task_to_agent(task_id, "coding_agent", group_id)
        
        # Third pass: create test tasks with dependencies on their coding tasks
        last_test_task_id = None
        for task, _, related_coding_idx in test_tasks:
            # Enhance test task with context from related coding task
            enhanced_task = dict(task)
            
            # Add file paths to test task description if we have them
            if related_coding_idx is not None and related_coding_idx < len(coding_tasks):
                related_coding_task, related_coding_id = coding_tasks[related_coding_idx]
                
                # Include file paths in the test task
                if "affected_paths" in plan and plan["affected_paths"]:
                    file_path = plan["affected_paths"][0] if plan["affected_paths"] else "calculator/calculator.py"
                    enhanced_task["description"] = f"{task.get('description', '')} in {file_path}"
                    enhanced_task["context"] = {
                        "target_files": plan["affected_paths"],
                        "related_coding_task_id": related_coding_id
                    }
                
            task_id = await self._task_integration.create_subtask(
                parent_task_id=root_task_id,
                title=enhanced_task["title"],
                description=enhanced_task.get("description", ""),
                agent_type="test_agent",
                priority=TaskPriority.MEDIUM,
                metadata=enhanced_task.get("context", {})
            )
            
            # Test tasks always depend on their related coding task
            if related_coding_idx is not None and related_coding_idx < len(coding_tasks):
                _, related_coding_id = coding_tasks[related_coding_idx]
                await self._task_integration.add_task_dependency(
                    task_id,
                    related_coding_id
                )
            elif last_coding_task_id:
                # Fallback: depend on the last coding task
                await self._task_integration.add_task_dependency(
                    task_id,
                    last_coding_task_id
                )
            
            # Test tasks are always serial with each other
            if last_test_task_id:
                await self._task_integration.add_task_dependency(
                    task_id,
                    last_test_task_id
                )
            
            last_test_task_id = task_id
            
            # Assign to agent with group ID
            await self._assign_task_to_agent(task_id, "test_agent", group_id)
        
        # Fourth pass: create other tasks (review, etc.) - they depend on all previous tasks
        last_task_id = last_test_task_id or last_coding_task_id
        for task, _ in other_tasks:
            task_id = await self._task_integration.create_subtask(
                parent_task_id=root_task_id,
                title=task["title"],
                description=task.get("description", ""),
                agent_type=task.get("type", "reviewer"),
                priority=TaskPriority.LOW
            )
            
            # Depend on the last task
            if last_task_id:
                await self._task_integration.add_task_dependency(
                    task_id,
                    last_task_id
                )
            
            last_task_id = task_id
            
            # Assign to agent with group ID
            await self._assign_task_to_agent(task_id, task.get("type", "reviewer"), group_id)
                
        return root_task_id
        
    def _get_task_type_from_step_kind(self, step_kind: StepKind) -> str:
        """Map StepKind to appropriate agent type."""
        mapping = {
            StepKind.TEST: "test_agent",
            StepKind.EDIT: "coding_agent",
            StepKind.ADD: "coding_agent",
            StepKind.REFACTOR: "coding_agent",
            StepKind.REVIEW: "reviewer",
            StepKind.REMOVE: "coding_agent"
        }
        return mapping.get(step_kind, "coding_agent")
        
    def _get_priority_from_phase(self, phase: Dict[str, Any]) -> TaskPriority:
        """Get task priority from phase info."""
        if "critical" in phase.get("name", "").lower():
            return TaskPriority.CRITICAL
        elif "setup" in phase.get("name", "").lower():
            return TaskPriority.HIGH
        else:
            return TaskPriority.MEDIUM
            
    async def _assign_task_to_agent(self, task_id: str, agent_type: str, group_id: Optional[str] = None):
        """Assign task to appropriate agent."""
        # Emit task assignment event
        if self._event_integration:
            await self._event_integration.publish_event("task.assigned", {
                "task_id": task_id,
                "agent_id": agent_type,
                "assigned_by": self.context.agent_id,
                "group_id": group_id  # Include group ID for branch management
            })
            
    async def on_task_assigned(self, task_id: str):
        """Handle task assignment to request planner."""
        # Request planner typically doesn't execute tasks directly
        # but monitors overall progress
        task = await self._task_integration.get_task(task_id)
        if task:
            logger.info(f"Monitoring task: {task['title']}")
            
    async def monitor_plan_execution(self, plan_id: str) -> Dict[str, Any]:
        """Monitor execution of a plan."""
        root_task_id = self.active_plans.get(plan_id)
        if not root_task_id or not self._task_integration:
            return {"status": "not_found"}
            
        # Get all tasks in plan
        all_tasks = []
        to_check = [root_task_id]
        
        while to_check:
            task_id = to_check.pop()
            task = await self._task_integration.get_task(task_id)
            if task:
                all_tasks.append(task)
                # Add subtasks
                to_check.extend(task.get("subtask_ids", []))
                
        # Calculate progress
        total = len(all_tasks)
        completed = sum(1 for t in all_tasks if t["status"] == TaskStatus.COMPLETED.value)
        failed = sum(1 for t in all_tasks if t["status"] == TaskStatus.FAILED.value)
        in_progress = sum(1 for t in all_tasks if t["status"] == TaskStatus.IN_PROGRESS.value)
        
        return {
            "plan_id": plan_id,
            "status": "active",
            "progress": {
                "total_tasks": total,
                "completed": completed,
                "failed": failed,
                "in_progress": in_progress,
                "percentage": (completed / total * 100) if total > 0 else 0
            },
            "root_task_id": root_task_id
        }
        
    async def complete_plan(self, plan_id: str, results: Dict[str, Any]):
        """Mark a plan as complete and store insights."""
        # Get plan execution data
        execution_data = await self.monitor_plan_execution(plan_id)
        
        # Store successful plan in RAG for future reference
        if self._rag_integration and execution_data["progress"]["failed"] == 0:
            await self._rag_integration.store_pattern(
                pattern=f"plan_{plan_id}",
                description=f"Successful execution plan with {execution_data['progress']['total_tasks']} tasks",
                example=str(results),
                tags=["successful_plan", "request_planner"]
            )
            
        # Remove from active plans
        self.active_plans.pop(plan_id, None)
        
        # Emit plan completion event
        if self._event_integration:
            await self._event_integration.publish_event("plan.completed", {
                "plan_id": plan_id,
                "execution_data": execution_data,
                "results": results
            })