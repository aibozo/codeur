"""
Integrated Code Planner
=====================

This module provides the integrated version of the Code Planner agent
that works with the task graph and event system.
"""

from typing import Dict, Any, List, Optional
from ..core.integrated_agent_base import IntegratedAgentBase, AgentContext
from .code_planner import CodePlanner


class IntegratedCodePlanner(IntegratedAgentBase):
    """Code planner with full system integration."""
    
    def __init__(self, context: AgentContext):
        """Initialize integrated code planner."""
        super().__init__(context)
        
        # Create base code planner
        self.planner = CodePlanner(
            repo_path=str(context.project_path),
            use_rag=bool(context.rag_client)
        )
        
    def get_capabilities(self) -> List[str]:
        """Return agent capabilities."""
        return ["code_analysis", "dependency_analysis", "planning"]
        
    def get_integration_level(self) -> str:
        """Return integration level."""
        return "full"
        
    async def on_task_assigned(self, task: Dict[str, Any]) -> None:
        """Handle task assignment."""
        await self.publish_event("agent.task_assigned", {
            "agent_id": self.agent_id,
            "task_id": task["id"]
        })
        
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a code planning task."""
        await self.publish_event("task.started", {
            "task_id": task["id"],
            "agent_id": self.agent_id
        })
        
        try:
            # Extract planning request
            description = task.get("description", "")
            context = task.get("context", {})
            
            # Create planning request
            request = {
                "goal": description,
                "context_files": context.get("files", []),
                "constraints": context.get("constraints", [])
            }
            
            # Run code planner
            result = await self.planner.create_plan(request)
            
            # Convert to task result format
            task_result = {
                "status": "completed",
                "plan": result,
                "subtasks": self._convert_to_subtasks(result)
            }
            
            await self.publish_event("task.completed", {
                "task_id": task["id"],
                "agent_id": self.agent_id,
                "result": task_result
            })
            
            return task_result
            
        except Exception as e:
            error_result = {
                "status": "failed",
                "error": str(e)
            }
            
            await self.publish_event("task.failed", {
                "task_id": task["id"],
                "agent_id": self.agent_id,
                "error": str(e)
            })
            
            return error_result
            
    def _convert_to_subtasks(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert plan steps to subtasks."""
        subtasks = []
        
        for i, step in enumerate(plan.get("steps", [])):
            subtask = {
                "id": f"{plan.get('id', 'plan')}_{i}",
                "type": "coding",
                "description": step.get("description", ""),
                "dependencies": step.get("dependencies", []),
                "files": step.get("files", []),
                "priority": step.get("priority", "medium")
            }
            subtasks.append(subtask)
            
        return subtasks
        
    async def analyze_code_structure(self, files: List[str]) -> Dict[str, Any]:
        """Analyze code structure and dependencies."""
        # Delegate to base planner
        return await self.planner.analyze_dependencies(files)