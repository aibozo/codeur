"""
Simple LLM tool interfaces for the Architect agent.

This module provides the actual tool definitions that can be exposed to the LLM
through function calling or similar interfaces.
"""

import json
from typing import Dict, Any, Optional
from enum import Enum

from .task_graph_manager import TaskGraphManager
from .task_creation_tools import TaskCreationTools
from .enhanced_task_graph import TaskPriority


class TaskFormat(str, Enum):
    """Supported task creation formats."""
    MARKDOWN = "markdown"
    LIST = "list"
    YAML = "yaml"
    

class ArchitectTools:
    """
    Simple tools for the Architect LLM to use.
    
    Designed to minimize tool calls and use natural formats.
    """
    
    def __init__(self, task_manager: TaskGraphManager):
        self.task_manager = task_manager
        self.creation_tools = TaskCreationTools(task_manager)
        
    async def create_tasks(self, 
                          content: str,
                          format: str = "list",
                          title: Optional[str] = None) -> Dict[str, Any]:
        """
        Create tasks using a simple text format.
        
        This is the main tool for the Architect to create task structures.
        It supports multiple formats to allow flexibility.
        
        Args:
            content: The task description in the specified format
            format: Format type - "markdown", "list", or "yaml"
            title: Optional title for the task group (becomes epic)
            
        Returns:
            Summary of created tasks
            
        Examples:
            
        Format: "list" (simplest, recommended)
        ```
        Build User System:
          - Setup database tables (high, 2h)
          - Create user model:
            - Define fields (1h)
            - Add validation (1h)
          - Build API endpoints (medium, 3h, needs: Create user model)
          - Write tests (2h, needs: Build API endpoints)
        ```
        
        Format: "markdown" (more detailed)
        ```
        # Build Authentication
        
        ## Setup Database [high] (2h)
        Create users table with proper indexes
        
        ## Implement JWT [high] (4h)
        - Token generation
        - Validation middleware
        
        ## API Endpoints [medium] (3h) [depends: Setup Database, Implement JWT]
        Create login and logout endpoints
        ```
        
        Format: "yaml" (most structured)
        ```
        epic: Authentication System
        tasks:
          - Database Setup:
              priority: high
              hours: 2
          - JWT Implementation:
              priority: high  
              hours: 4
              tasks:
                - Token generation
                - Token validation
          - API Endpoints:
              needs: [Database Setup, JWT Implementation]
              hours: 3
        ```
        """
        try:
            # Add title to content if provided
            if title and format == "list":
                content = f"{title}:\n{content}"
            elif title and format == "yaml":
                content = f"epic: {title}\n{content}"
            elif title and format == "markdown":
                content = f"# {title}\n\n{content}"
                
            # Create tasks based on format
            if format == TaskFormat.MARKDOWN:
                result = await self.creation_tools.create_tasks_from_markdown(content)
            elif format == TaskFormat.LIST:
                result = await self.creation_tools.create_tasks_from_simple_list(content)
            elif format == TaskFormat.YAML:
                result = await self.creation_tools.create_tasks_from_yaml_simple(content)
            else:
                return {
                    "status": "error",
                    "message": f"Unknown format: {format}. Use 'list', 'markdown', or 'yaml'"
                }
                
            # Auto-detect communities if tasks were created
            if result.get("status") == "success" and result.get("created_tasks", 0) > 5:
                communities = self.task_manager.detect_and_create_communities(method="theme")
                result["communities_detected"] = len(communities)
                
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create tasks: {str(e)}"
            }
            
    async def add_subtasks(self,
                          parent_task: str,
                          subtasks: str) -> Dict[str, Any]:
        """
        Add subtasks to an existing task.
        
        Args:
            parent_task: Title of the parent task
            subtasks: List of subtasks in simple format
            
        Example:
        ```
        parent_task: "Build API endpoints"
        subtasks: |
          - Create user controller (1h)
          - Add authentication middleware (2h)
          - Setup route handlers (1h)
          - Add input validation (1h, needs: Create user controller)
        ```
        """
        try:
            result = await self.creation_tools.add_subtasks_to_existing(
                parent_task,
                subtasks
            )
            return result
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to add subtasks: {str(e)}"
            }
            
    async def get_task_status(self, 
                            detail_level: str = "summary") -> Dict[str, Any]:
        """
        Get current task graph status.
        
        Args:
            detail_level: "summary" for high-level, "detailed" for full info
            
        Returns:
            Task graph status information
        """
        try:
            if detail_level == "summary":
                # Get abstracted view
                state = self.task_manager.get_abstracted_state()
                
                # Format nicely for LLM
                return {
                    "status": "success",
                    "summary": {
                        "total_tasks": state["total_tasks"],
                        "completed_tasks": state["completed_tasks"],
                        "communities": [
                            {
                                "name": comm["name"],
                                "tasks": comm["task_count"],
                                "completed": comm["completed_count"]
                            }
                            for comm in state["communities"].values()
                        ],
                        "top_tasks": [
                            {
                                "title": task["title"],
                                "status": task["status"],
                                "subtasks": task["subtask_count"]
                            }
                            for task in state["top_level_tasks"][:5]
                        ]
                    }
                }
            else:
                # More detailed view
                graph = self.task_manager.graph
                ready_tasks = graph.get_ready_tasks()
                
                return {
                    "status": "success",
                    "detailed": {
                        "total_tasks": len(graph.tasks),
                        "by_status": {
                            "completed": len(graph.completed_tasks),
                            "ready": len(ready_tasks),
                            "blocked": len([t for t in graph.tasks.values() 
                                          if t.status.value == "blocked"]),
                            "in_progress": len([t for t in graph.tasks.values() 
                                              if t.status.value == "in_progress"])
                        },
                        "ready_tasks": [
                            {
                                "id": task.id,
                                "title": task.title,
                                "agent": task.agent_type,
                                "priority": task.priority.value
                            }
                            for task in ready_tasks[:10]
                        ],
                        "communities": len(graph.communities),
                        "display_mode": graph.display_mode.value
                    }
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get status: {str(e)}"
            }
            
    async def update_task_priority(self,
                                 task_title: str,
                                 new_priority: str) -> Dict[str, Any]:
        """
        Update the priority of a task.
        
        Args:
            task_title: Title of the task to update
            new_priority: New priority level (low, medium, high, critical)
        """
        try:
            # Find task
            task_id = None
            for tid, task in self.task_manager.graph.tasks.items():
                if task.title == task_title:
                    task_id = tid
                    break
                    
            if not task_id:
                return {
                    "status": "error",
                    "message": f"Task '{task_title}' not found"
                }
                
            # Update priority
            priority_map = {
                "low": TaskPriority.LOW,
                "medium": TaskPriority.MEDIUM,
                "high": TaskPriority.HIGH,
                "critical": TaskPriority.CRITICAL
            }
            
            new_priority_enum = priority_map.get(new_priority.lower())
            if not new_priority_enum:
                return {
                    "status": "error",
                    "message": f"Invalid priority: {new_priority}"
                }
                
            task = self.task_manager.graph.tasks[task_id]
            old_priority = task.priority.value
            task.priority = new_priority_enum
            
            return {
                "status": "success",
                "task": task_title,
                "old_priority": old_priority,
                "new_priority": new_priority
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to update priority: {str(e)}"
            }
            
    def get_tool_definitions(self) -> list:
        """
        Get OpenAI-style function definitions for these tools.
        
        Returns a list of function definitions that can be used with
        OpenAI's function calling or similar LLM APIs.
        """
        return [
            {
                "name": "create_tasks",
                "description": "Create a task structure using simple text formats",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The task structure in the specified format"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["list", "markdown", "yaml"],
                            "description": "Format of the content. 'list' is simplest and recommended",
                            "default": "list"
                        },
                        "title": {
                            "type": "string",
                            "description": "Optional title for the task group"
                        }
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "add_subtasks",
                "description": "Add subtasks to an existing task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "parent_task": {
                            "type": "string",
                            "description": "Title of the parent task"
                        },
                        "subtasks": {
                            "type": "string",
                            "description": "List of subtasks in simple format (- Task name (priority, hours))"
                        }
                    },
                    "required": ["parent_task", "subtasks"]
                }
            },
            {
                "name": "get_task_status",
                "description": "Get current status of the task graph",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "detail_level": {
                            "type": "string",
                            "enum": ["summary", "detailed"],
                            "description": "Level of detail to return",
                            "default": "summary"
                        }
                    }
                }
            },
            {
                "name": "update_task_priority",
                "description": "Update the priority of a task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_title": {
                            "type": "string",
                            "description": "Title of the task to update"
                        },
                        "new_priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                            "description": "New priority level"
                        }
                    },
                    "required": ["task_title", "new_priority"]
                }
            }
        ]