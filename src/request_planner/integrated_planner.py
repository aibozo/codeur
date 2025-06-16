"""
Integrated Request Planner with Task Graph and RAG support.

This module shows how to integrate the Request Planner agent with
the task graph and RAG systems using the standard interfaces.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from src.core.agent_integration_interfaces import (
    IntegratedAgent, AgentContext, AgentCapability,
    TaskGraphIntegration, RAGIntegration, EventIntegration,
    AgentEventType
)
from src.architect.models import TaskStatus, TaskPriority, TaskNode
from src.request_planner.planner import RequestPlanner
from src.request_planner.models import ChangeRequest, Plan

logger = logging.getLogger(__name__)


class TaskGraphAdapter(TaskGraphIntegration):
    """Adapter for task graph integration."""
    
    def __init__(self, task_graph_manager):
        self.manager = task_graph_manager
    
    async def get_task_context(self, task_id: str) -> Dict[str, Any]:
        """Retrieve full context for a specific task."""
        return self.manager.expand_task_context(task_id)
    
    async def update_task_status(
        self, 
        task_id: str, 
        status: TaskStatus,
        message: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update the status of a task."""
        return await self.manager.update_task_status(
            task_id, status, message=message, metrics=metrics
        )
    
    async def create_subtask(
        self,
        parent_task_id: str,
        title: str,
        description: str,
        agent_type: str,
        priority: TaskPriority = TaskPriority.MEDIUM
    ) -> str:
        """Create a subtask under a parent task."""
        task = TaskNode(
            title=title,
            description=description,
            agent_type=agent_type,
            priority=priority,
            dependencies={parent_task_id}
        )
        self.manager.graph.add_task(task)
        return task.id
    
    async def get_task_dependencies(self, task_id: str) -> List[str]:
        """Get all dependencies for a task."""
        task = self.manager.graph.tasks.get(task_id)
        return list(task.dependencies) if task else []
    
    async def get_dependent_tasks(self, task_id: str) -> List[str]:
        """Get all tasks that depend on this task."""
        task = self.manager.graph.tasks.get(task_id)
        return list(task.dependents) if task else []


class RAGAdapter(RAGIntegration):
    """Adapter for RAG integration."""
    
    def __init__(self, rag_client):
        self.client = rag_client
    
    async def search_knowledge(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search the knowledge base."""
        return self.client.search(query, k=limit, filters=filters)
    
    async def store_knowledge(
        self,
        doc_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store new knowledge in the system."""
        doc_id = f"{doc_type}_{hash(content)}"
        # In real implementation, would use proper RAG storage
        logger.info(f"Storing {doc_type} knowledge: {doc_id}")
        return doc_id
    
    async def find_similar_implementations(
        self,
        description: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar past implementations."""
        # Search for similar plans and implementations
        results = await self.search_knowledge(
            description,
            filters={"doc_type": {"$in": ["plan", "implementation"]}},
            limit=limit
        )
        return results
    
    async def get_component_context(
        self,
        component_name: str
    ) -> Dict[str, Any]:
        """Get full context for a code component."""
        results = self.client.find_symbol(component_name)
        if results:
            return results[0]
        return {}


class EventAdapter(EventIntegration):
    """Adapter for event integration."""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.subscriptions = {}
    
    async def publish_event(
        self,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Publish an event to the system."""
        if self.event_bus:
            await self.event_bus.publish(event_type, data)
    
    async def subscribe_to_events(
        self,
        event_types: List[str],
        callback: Any
    ) -> str:
        """Subscribe to specific event types."""
        subscription_id = f"sub_{len(self.subscriptions)}"
        # In real implementation, would set up actual subscriptions
        self.subscriptions[subscription_id] = (event_types, callback)
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from events."""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]


class IntegratedRequestPlanner(IntegratedAgent):
    """Request Planner with full integration support."""
    
    def __init__(self, context: AgentContext, repo_path: str = "."):
        super().__init__(context)
        self.base_planner = RequestPlanner(repo_path, use_llm=True)
        self.active_plans = {}
        self.repo_path = Path(repo_path)
        
        # Subscribe to relevant events if available
        if self.events:
            self._setup_event_subscriptions()
    
    def _create_task_integration(self) -> TaskGraphIntegration:
        """Create task graph integration instance."""
        return TaskGraphAdapter(self.context.task_graph_manager)
    
    def _create_rag_integration(self) -> RAGIntegration:
        """Create RAG integration instance."""
        return RAGAdapter(self.context.rag_client)
    
    def _create_event_integration(self) -> EventIntegration:
        """Create event integration instance."""
        return EventAdapter(self.context.event_bus)
    
    async def _setup_event_subscriptions(self):
        """Subscribe to relevant events."""
        await self.events.subscribe_to_events(
            [AgentEventType.TASK_COMPLETED, AgentEventType.TASK_FAILED],
            self._handle_task_event
        )
    
    async def _handle_task_event(self, event_type: str, data: Dict[str, Any]):
        """Handle task-related events."""
        task_id = data.get("task_id")
        if task_id and task_id in self.active_plans:
            plan_id = self.active_plans[task_id]
            
            if event_type == AgentEventType.TASK_COMPLETED:
                logger.info(f"Task {task_id} completed for plan {plan_id}")
                await self._check_plan_completion(plan_id)
            elif event_type == AgentEventType.TASK_FAILED:
                logger.error(f"Task {task_id} failed for plan {plan_id}")
                await self._handle_task_failure(task_id, plan_id)
    
    async def create_plan_with_tasks(self, request: ChangeRequest) -> Plan:
        """
        Create a plan and corresponding tasks in the task graph.
        
        This is the main integration point that:
        1. Uses RAG to find similar past implementations
        2. Creates a plan using the base planner
        3. Creates tasks in the task graph
        4. Publishes events about the new plan
        """
        # Search for similar implementations
        similar_impls = []
        if self.rag:
            similar_impls = await self.rag.find_similar_implementations(
                request.description, limit=3
            )
            logger.info(f"Found {len(similar_impls)} similar implementations")
        
        # Create base plan (enhanced with similar implementations context)
        plan = self.base_planner.create_plan(request)
        
        # Create top-level task for the plan
        if self.task_graph:
            plan_task_id = await self._create_plan_task(plan, request)
            
            # Create subtasks for each step
            step_task_ids = []
            for step in plan.steps:
                task_id = await self.task_graph.create_subtask(
                    parent_task_id=plan_task_id,
                    title=step.goal,
                    description=f"Step {step.order}: {step.goal}",
                    agent_type=self._determine_agent_for_step(step),
                    priority=self._determine_priority(plan.complexity_label)
                )
                step_task_ids.append(task_id)
                self.active_plans[task_id] = plan.id
            
            # Store plan context in task
            await self._store_plan_context(plan_task_id, plan, step_task_ids)
        
        # Store successful plan in RAG for future reference
        if self.rag:
            await self.rag.store_knowledge(
                doc_type="plan",
                content=self._serialize_plan(plan),
                metadata={
                    "request_type": request.request_type,
                    "complexity": plan.complexity_label,
                    "success": True  # Will update based on execution
                }
            )
        
        # Publish plan created event
        if self.events:
            await self.events.publish_event(
                AgentEventType.PLAN_CREATED,
                {
                    "plan_id": plan.id,
                    "request_id": request.id,
                    "steps": len(plan.steps),
                    "complexity": plan.complexity_label
                }
            )
        
        return plan
    
    async def _create_plan_task(self, plan: Plan, request: ChangeRequest) -> str:
        """Create the top-level task for a plan."""
        task = TaskNode(
            title=f"Plan: {request.description[:50]}...",
            description=f"Implementation plan for: {request.description}",
            agent_type="request_planner",
            priority=TaskPriority.HIGH,
            context={
                "plan_id": plan.id,
                "request_id": request.id,
                "rationale": plan.rationale
            }
        )
        # In real implementation, would add to task graph properly
        return task.id
    
    def _determine_agent_for_step(self, step) -> str:
        """Determine which agent should handle a step."""
        # Simple heuristic - in real implementation would be more sophisticated
        if "test" in step.goal.lower():
            return "code_tester"
        elif "implement" in step.goal.lower() or "fix" in step.goal.lower():
            return "coding_agent"
        elif "analyze" in step.goal.lower():
            return "analyzer"
        elif "design" in step.goal.lower() or "plan" in step.goal.lower():
            return "code_planner"
        else:
            return "coding_agent"  # Default
    
    def _determine_priority(self, complexity_label: str) -> TaskPriority:
        """Determine task priority based on complexity."""
        if complexity_label == "COMPLEX":
            return TaskPriority.CRITICAL
        elif complexity_label == "MODERATE":
            return TaskPriority.HIGH
        else:
            return TaskPriority.MEDIUM
    
    async def _store_plan_context(
        self, 
        task_id: str, 
        plan: Plan, 
        step_task_ids: List[str]
    ):
        """Store plan context in the task for other agents."""
        # In real implementation, would update task context
        logger.info(f"Storing context for plan task {task_id}")
    
    def _serialize_plan(self, plan: Plan) -> str:
        """Serialize plan for storage."""
        return f"Plan {plan.id}:\n" + \
               f"Steps: {len(plan.steps)}\n" + \
               f"Complexity: {plan.complexity_label}\n" + \
               f"Rationale: {'; '.join(plan.rationale)}"
    
    async def _check_plan_completion(self, plan_id: str):
        """Check if all tasks for a plan are complete."""
        # In real implementation, would check task graph
        logger.info(f"Checking completion status for plan {plan_id}")
    
    async def _handle_task_failure(self, task_id: str, plan_id: str):
        """Handle a failed task in a plan."""
        # In real implementation, might create alternative tasks
        logger.error(f"Handling failure of task {task_id} in plan {plan_id}")