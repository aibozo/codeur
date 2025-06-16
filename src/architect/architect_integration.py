"""
Integration of LLM tools with the Architect agent.

This module shows how to integrate the simplified task creation tools
with the existing Architect agent for use with OpenAI function calling.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .architect import Architect
from .task_graph_manager import TaskGraphManager, TaskGraphContext
from .llm_tools import ArchitectTools

logger = logging.getLogger(__name__)


class EnhancedArchitect(Architect):
    """
    Enhanced Architect with integrated task graph management and LLM tools.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize task graph manager
        context = TaskGraphContext(
            project_id=f"project_{self.project_path.name}",
            project_path=self.project_path,
            rag_client=self.rag_client
        )
        self.task_manager = TaskGraphManager(context)
        self.tools = ArchitectTools(self.task_manager)
        
    def get_system_prompt(self) -> str:
        """Get enhanced system prompt that includes task management guidance."""
        base_prompt = """You are an expert software architect. You help users plan and design software projects by creating detailed task structures.

When creating tasks, use the simple list format unless specifically asked for another format. Here's how:

For a simple task list:
```
Main Task:
  - Subtask 1 (priority, hours)
  - Subtask 2:
    - Sub-subtask 1
    - Sub-subtask 2
  - Subtask 3 (needs: Subtask 1)
```

Guidelines:
- Use clear, action-oriented task titles
- Add priority (low/medium/high/critical) and time estimates in parentheses
- Use "needs: Task1, Task2" to specify dependencies
- Nest subtasks with indentation
- Group related tasks together (they'll be auto-organized into communities)

You can also:
- Get task status with get_task_status()
- Add subtasks to existing tasks with add_subtasks()
- Update priorities with update_task_priority()
"""
        return base_prompt
        
    def get_available_functions(self) -> List[Dict[str, Any]]:
        """Get function definitions for OpenAI function calling."""
        return self.tools.get_tool_definitions()
        
    async def handle_function_call(self, 
                                 function_name: str,
                                 arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle function calls from the LLM.
        
        Args:
            function_name: Name of the function to call
            arguments: Arguments for the function
            
        Returns:
            Result of the function call
        """
        if function_name == "create_tasks":
            return await self.tools.create_tasks(**arguments)
        elif function_name == "add_subtasks":
            return await self.tools.add_subtasks(**arguments)
        elif function_name == "get_task_status":
            return await self.tools.get_task_status(**arguments)
        elif function_name == "update_task_priority":
            return await self.tools.update_task_priority(**arguments)
        else:
            return {
                "status": "error",
                "message": f"Unknown function: {function_name}"
            }
            
    async def process_request(self, user_message: str) -> str:
        """
        Process a user request with integrated task management.
        
        This is a simplified example of how the Architect would process requests.
        In practice, this would integrate with your LLM client.
        """
        # This is where you'd integrate with OpenAI or other LLM
        # For now, we'll just show the structure
        
        if not self.llm_client:
            return "No LLM client configured. Please set OPENAI_API_KEY."
            
        try:
            # Add task context to the conversation
            task_context = self.task_manager.get_abstracted_state()
            
            # Prepare messages
            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": user_message}
            ]
            
            # Add context if tasks exist
            if task_context['total_tasks'] > 0:
                context_msg = f"\nCurrent project status:\n"
                context_msg += f"- Total tasks: {task_context['total_tasks']}\n"
                context_msg += f"- Completed: {task_context['completed_tasks']}\n"
                context_msg += f"- Communities: {len(task_context['communities'])}\n"
                
                messages.append({
                    "role": "system", 
                    "content": f"Project context: {context_msg}"
                })
                
            # Call LLM with function definitions
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                functions=self.get_available_functions(),
                function_call="auto",
                temperature=0.7
            )
            
            # Handle response
            message = response.choices[0].message
            
            # Check if function was called
            if message.function_call:
                function_name = message.function_call.name
                arguments = json.loads(message.function_call.arguments)
                
                # Execute function
                result = await self.handle_function_call(function_name, arguments)
                
                # Add function result to conversation
                messages.append(message)
                messages.append({
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps(result)
                })
                
                # Get final response
                final_response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7
                )
                
                return final_response.choices[0].message.content
            else:
                return message.content
                
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return f"I encountered an error: {str(e)}"
            
    def get_current_task_graph(self) -> Dict[str, Any]:
        """Get the current task graph for visualization."""
        return {
            "tasks": {
                tid: task.to_dict() 
                for tid, task in self.task_manager.graph.tasks.items()
            },
            "communities": {
                cid: {
                    "id": comm.id,
                    "name": comm.name,
                    "theme": comm.theme,
                    "color": comm.color,
                    "task_ids": list(comm.task_ids)
                }
                for cid, comm in self.task_manager.graph.communities.items()
            },
            "display_mode": self.task_manager.graph.display_mode.value,
            "stats": self.task_manager.get_abstracted_state()
        }


# Example prompt templates the Architect might use internally
TASK_CREATION_EXAMPLES = {
    "web_app": """Build Web Application:
  - Setup project structure (high, 2h)
  - Database design (critical, 4h)
  - Backend API:
    - User management (high, 6h, needs: Database design)
    - Authentication (critical, 4h, needs: User management)
    - Core features (high, 8h, needs: Authentication)
  - Frontend:
    - UI components (medium, 6h)
    - Pages (medium, 8h, needs: UI components)
    - API integration (high, 4h, needs: Backend API, Pages)
  - Testing (medium, 6h, needs: Backend API, Frontend)
  - Deployment (high, 4h, needs: Testing)""",
    
    "microservice": """Microservice Architecture:
  - Service design (critical, 4h)
  - API Gateway (high, 6h)
  - Services:
    - User service (high, 8h, needs: Service design)
    - Auth service (critical, 6h, needs: User service, API Gateway)
    - Payment service (high, 8h, needs: Auth service)
    - Notification service (medium, 6h)
  - Message queue (high, 4h, needs: Service design)
  - Service discovery (medium, 4h, needs: Services)
  - Monitoring (medium, 6h, needs: Services)""",
    
    "mobile_app": """Mobile Application:
  - App architecture (high, 4h)
  - UI/UX design (high, 8h)
  - Core features:
    - User registration (high, 4h, needs: App architecture)
    - Main screens (high, 12h, needs: UI/UX design)
    - Data sync (medium, 6h, needs: Main screens)
  - Backend API (high, 8h)
  - Push notifications (medium, 4h, needs: Backend API)
  - Testing:
    - Unit tests (medium, 4h)
    - UI tests (medium, 4h)
  - App store setup (low, 4h, needs: Testing)"""
}