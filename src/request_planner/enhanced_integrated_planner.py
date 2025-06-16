"""
Enhanced Request Planner with deep task graph integration.

This integrates the RequestPlanner with the task graph system to:
- Convert plans into hierarchical task graphs
- Assign tasks to appropriate agents
- Track execution progress
- Update task status based on agent feedback
"""

import logging
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import uuid

from ..core.integrated_agent_base import (
    IntegratedAgentBase, AgentContext, IntegrationLevel, AgentCapability
)
from ..architect.enhanced_task_graph import TaskPriority, TaskStatus
from .planner import RequestPlanner
from .models import ChangeRequest, Plan, Task, TaskStatus as PlannerTaskStatus
from ..core.logging import get_logger

logger = get_logger(__name__)


class EnhancedIntegratedRequestPlanner(IntegratedAgentBase, RequestPlanner):
    """
    Request Planner with deep task graph integration.
    
    This is the main orchestrator that:
    - Converts user requests into task graphs
    - Assigns tasks to agents sequentially
    - Monitors execution progress
    - Updates both internal and graph task status
    """
    
    def __init__(self, context: AgentContext):
        """Initialize enhanced request planner."""
        # Initialize base classes
        IntegratedAgentBase.__init__(self, context)
        RequestPlanner.__init__(
            self,
            repo_path=str(context.project_path),
            use_llm=context.rag_client is not None
        )
        
        # Track mappings between planner tasks and graph tasks
        self.task_mappings: Dict[str, str] = {}  # planner_task_id -> graph_task_id
        self.plan_mappings: Dict[str, str] = {}  # plan_id -> root_task_id
        
        # Track execution state
        self.executing_plans: Set[str] = set()
        
    def get_integration_level(self) -> IntegrationLevel:
        """Request planner needs full integration."""
        return IntegrationLevel.FULL
        
    def get_capabilities(self) -> Set[AgentCapability]:
        """Request planner capabilities."""
        return {
            AgentCapability.PLANNING,
            AgentCapability.TASK_DECOMPOSITION,
            AgentCapability.COORDINATION,
            AgentCapability.TASK_SCHEDULING
        }
        
    def create_plan(self, request: ChangeRequest) -> Plan:
        """
        Create a plan with task graph integration.
        
        This extends the base create_plan to also create
        a corresponding task graph.
        """
        # Create base plan
        plan = super().create_plan(request)
        
        # Create task graph asynchronously
        # (We'll handle this in execute_plan since create_plan is sync)
        
        return plan
        
    async def execute_plan_with_graph(self, plan: Plan) -> Dict[str, Any]:
        """
        Execute a plan using the task graph system.
        
        This is the main integration point that:
        1. Converts the plan to a task graph
        2. Assigns tasks to agents
        3. Monitors execution
        """
        logger.info(f"Executing plan {plan.id} with task graph integration")
        
        # Mark plan as executing
        self.executing_plans.add(plan.id)
        
        # Create task graph from plan
        root_task_id = await self._create_task_graph_from_plan(plan)
        self.plan_mappings[plan.id] = root_task_id
        
        # Start execution by getting ready tasks
        await self._start_task_execution(plan.id)
        
        # Return execution info
        return {
            "plan_id": plan.id,
            "root_task_id": root_task_id,
            "status": "executing",
            "total_steps": len(plan.steps)
        }
        
    async def _create_task_graph_from_plan(self, plan: Plan) -> str:
        """Convert a plan into a hierarchical task graph."""
        if not self._task_integration:
            logger.warning("No task integration available")
            return ""
            
        # Create root task for the plan
        # Get description from first step or rationale
        plan_description = plan.rationale[0] if plan.rationale else f"Execute {len(plan.steps)} steps"
        
        root_task_id = await self._task_integration.create_subtask(
            parent_task_id=None,
            title=f"Plan: {plan_description[:50]}...",
            description=plan_description,
            agent_type="request_planner",
            priority=self._get_plan_priority(plan)
        )
        
        # Create tasks for each step
        prev_task_id = None
        for step in plan.steps:
            # Create main task for step
            step_task_id = await self._task_integration.create_subtask(
                parent_task_id=root_task_id,
                title=step.goal,
                description=f"Step {step.order}: {step.goal}",
                agent_type="request_planner",
                priority=self._get_step_priority(step)
            )
            
            # Add dependency on previous step if exists
            if prev_task_id:
                await self._task_integration.add_task_dependency(
                    step_task_id, 
                    prev_task_id
                )
                
            prev_task_id = step_task_id
            
            # Create subtasks based on step kind
            await self._create_step_subtasks(step, step_task_id)
            
            # Map planner task to graph task
            # (We'll create planner tasks when we execute)
            
        return root_task_id
        
    async def _create_step_subtasks(self, step, parent_task_id: str):
        """Create subtasks for a step based on its kind."""
        subtasks = []
        
        if step.kind.value == "add":
            subtasks = [
                ("Implement core functionality", "coding_agent", TaskPriority.HIGH),
                ("Write unit tests", "coding_agent", TaskPriority.MEDIUM),
                ("Update documentation", "coding_agent", TaskPriority.LOW)
            ]
        elif step.kind.value == "edit":
            subtasks = [
                ("Analyze existing code", "code_planner", TaskPriority.HIGH),
                ("Make modifications", "coding_agent", TaskPriority.HIGH),
                ("Verify changes", "analyzer", TaskPriority.MEDIUM)
            ]
        elif step.kind.value == "test":
            subtasks = [
                ("Write test cases", "coding_agent", TaskPriority.HIGH),
                ("Run tests", "test_agent", TaskPriority.HIGH),
                ("Analyze coverage", "analyzer", TaskPriority.LOW)
            ]
        elif step.kind.value == "refactor":
            subtasks = [
                ("Analyze code structure", "analyzer", TaskPriority.HIGH),
                ("Plan refactoring", "code_planner", TaskPriority.HIGH),
                ("Implement refactoring", "coding_agent", TaskPriority.HIGH),
                ("Verify functionality", "test_agent", TaskPriority.HIGH)
            ]
        else:
            # Default subtask
            subtasks = [
                (f"Execute: {step.goal}", "coding_agent", TaskPriority.MEDIUM)
            ]
            
        # Create subtasks
        for title, agent, priority in subtasks:
            subtask_id = await self._task_integration.create_subtask(
                parent_task_id=parent_task_id,
                title=title,
                description=f"{title} for: {step.goal}",
                agent_type=agent,
                priority=priority
            )
            
            # Pre-assign to agent
            await self._assign_task_to_agent(subtask_id, agent)
            
    async def _start_task_execution(self, plan_id: str):
        """Start executing tasks for a plan."""
        root_task_id = self.plan_mappings.get(plan_id)
        if not root_task_id:
            return
            
        # Get ready tasks
        ready_tasks = self.context.task_manager.graph.get_ready_tasks()
        
        # Assign ready tasks to agents
        for task in ready_tasks:
            # Skip if already assigned
            if task.assigned_agent:
                continue
                
            # Determine best agent for task
            agent_type = task.agent_type or self._determine_agent_for_task(task)
            
            # Assign task
            await self._assign_task_to_agent(task.id, agent_type)
            
            # Create corresponding planner task
            planner_task = Task(
                id=str(uuid.uuid4()),
                description=task.title,
                status=PlannerTaskStatus.PENDING,
                plan_id=plan_id
            )
            self.active_tasks.append(planner_task)
            self.task_mappings[planner_task.id] = task.id
            
            logger.info(f"Assigned task {task.title} to {agent_type}")
            
    def _determine_agent_for_task(self, task) -> str:
        """Determine the best agent for a task based on its content."""
        title_lower = task.title.lower()
        desc_lower = task.description.lower()
        
        if any(word in title_lower or word in desc_lower 
               for word in ["test", "verify", "check"]):
            return "test_agent"
        elif any(word in title_lower or word in desc_lower 
                 for word in ["analyze", "review", "structure"]):
            return "analyzer"
        elif any(word in title_lower or word in desc_lower 
                 for word in ["plan", "design", "architecture"]):
            return "code_planner"
        else:
            return "coding_agent"
            
    async def _assign_task_to_agent(self, task_id: str, agent_type: str):
        """Assign a task to an agent and emit event."""
        # Update task with assigned agent
        task = self.context.task_manager.graph.tasks.get(task_id)
        if task:
            task.assigned_agent = agent_type
            
        # Emit assignment event
        if self._event_integration:
            await self._event_integration.publish_event("task.assigned", {
                "task_id": task_id,
                "agent_id": agent_type,
                "assigned_by": self.context.agent_id
            })
            
    async def on_task_assigned(self, task_id: str):
        """Handle tasks assigned to the request planner."""
        # Request planner monitors but doesn't execute tasks
        logger.info(f"Request planner monitoring task: {task_id}")
        
    async def handle_task_completed(self, task_id: str):
        """Handle task completion and trigger next tasks."""
        logger.info(f"Task {task_id} completed")
        
        # Update planner task status if mapped
        for planner_id, graph_id in self.task_mappings.items():
            if graph_id == task_id:
                for task in self.active_tasks:
                    if task.id == planner_id:
                        task.status = PlannerTaskStatus.COMPLETED
                        break
                        
        # Get next ready tasks
        ready_tasks = self.context.task_manager.graph.get_ready_tasks()
        
        # Assign new ready tasks
        for task in ready_tasks:
            if not task.assigned_agent:
                agent_type = task.agent_type or self._determine_agent_for_task(task)
                await self._assign_task_to_agent(task.id, agent_type)
                
        # Check if plan is complete
        await self._check_plan_completion()
        
    async def _check_plan_completion(self):
        """Check if any executing plans are complete."""
        for plan_id in list(self.executing_plans):
            root_task_id = self.plan_mappings.get(plan_id)
            if not root_task_id:
                continue
                
            # Check if root task is complete
            root_task = self.context.task_manager.graph.tasks.get(root_task_id)
            if root_task and root_task.status == TaskStatus.COMPLETED:
                logger.info(f"Plan {plan_id} completed!")
                self.executing_plans.remove(plan_id)
                
                # Emit completion event
                if self._event_integration:
                    await self._event_integration.publish_event("plan.completed", {
                        "plan_id": plan_id,
                        "root_task_id": root_task_id
                    })
                    
    def _get_plan_priority(self, plan: Plan) -> TaskPriority:
        """Get priority for a plan."""
        if plan.complexity_label == "high":
            return TaskPriority.CRITICAL
        elif plan.complexity_label == "medium":
            return TaskPriority.HIGH
        else:
            return TaskPriority.MEDIUM
            
    def _get_step_priority(self, step) -> TaskPriority:
        """Get priority for a step."""
        if step.kind.value in ["fix", "critical"]:
            return TaskPriority.CRITICAL
        elif step.kind.value in ["add", "edit"]:
            return TaskPriority.HIGH
        else:
            return TaskPriority.MEDIUM
            
    async def get_execution_status(self, plan_id: str) -> Dict[str, Any]:
        """Get detailed execution status for a plan."""
        root_task_id = self.plan_mappings.get(plan_id)
        if not root_task_id:
            return {"status": "not_found"}
            
        # Gather all tasks in plan
        all_tasks = []
        to_check = [root_task_id]
        
        while to_check:
            task_id = to_check.pop()
            task = self.context.task_manager.graph.tasks.get(task_id)
            if task:
                all_tasks.append(task)
                to_check.extend(task.subtask_ids)
                
        # Calculate statistics
        total = len(all_tasks)
        by_status = {
            "completed": sum(1 for t in all_tasks if t.status == TaskStatus.COMPLETED),
            "in_progress": sum(1 for t in all_tasks if t.status == TaskStatus.IN_PROGRESS),
            "failed": sum(1 for t in all_tasks if t.status == TaskStatus.FAILED),
            "ready": sum(1 for t in all_tasks if t.status == TaskStatus.READY),
            "blocked": sum(1 for t in all_tasks if t.status == TaskStatus.BLOCKED),
            "pending": sum(1 for t in all_tasks if t.status == TaskStatus.PENDING)
        }
        
        # Get current active tasks
        active_tasks = [
            {
                "id": t.id,
                "title": t.title,
                "agent": t.assigned_agent,
                "status": t.status.value
            }
            for t in all_tasks 
            if t.status == TaskStatus.IN_PROGRESS
        ]
        
        return {
            "plan_id": plan_id,
            "root_task_id": root_task_id,
            "total_tasks": total,
            "status_breakdown": by_status,
            "completion_percentage": (by_status["completed"] / total * 100) if total > 0 else 0,
            "active_tasks": active_tasks,
            "is_executing": plan_id in self.executing_plans
        }