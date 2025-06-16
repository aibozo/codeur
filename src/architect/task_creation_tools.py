"""
LLM-friendly tools for task graph creation.

This module provides simple interfaces that allow the Architect to create
complex task structures using natural formats like markdown or simple YAML.
"""

import re
import yaml
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from .enhanced_task_graph import TaskPriority, TaskGranularity
from .task_graph_manager import TaskGraphManager

logger = logging.getLogger(__name__)


@dataclass
class ParsedTask:
    """Simple representation of a parsed task."""
    title: str
    description: str = ""
    priority: str = "medium"
    agent: str = "coding_agent"
    depends_on: List[str] = field(default_factory=list)
    subtasks: List['ParsedTask'] = field(default_factory=list)
    estimated_hours: float = 0.0
    

class TaskCreationTools:
    """
    Simple tools for LLMs to create task graphs without complex JSON.
    """
    
    def __init__(self, task_manager: TaskGraphManager):
        self.task_manager = task_manager
        self.created_tasks = {}  # title -> task_id mapping for dependencies
        
    async def create_tasks_from_markdown(self, markdown_text: str) -> Dict[str, Any]:
        """
        Create tasks from a markdown-style list.
        
        Format:
        ```
        # Epic: Build Authentication System
        
        ## Setup Database [high] (2h)
        Create user tables and schema
        
        ## Implement JWT [high] @auth_expert (4h) 
        - Create token generation
        - Add validation middleware
        - Setup refresh tokens
        
        ## Build Login API [medium] (3h) [depends: Setup Database, Implement JWT]
        Create /login and /logout endpoints
        
        ### Write Tests (1h)
        Unit tests for all auth functions
        ```
        
        Returns:
            Summary of created tasks
        """
        lines = markdown_text.strip().split('\n')
        root_tasks = []
        current_stack = []  # Stack of (level, task) tuples
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
                
            # Check heading level
            heading_match = re.match(r'^(#{1,4})\s+(.+)$', line)
            if heading_match:
                level = len(heading_match.group(1))
                title_part = heading_match.group(2)
                
                # Parse task from heading
                task = self._parse_task_heading(title_part)
                
                # Get description from next lines
                i += 1
                description_lines = []
                while i < len(lines) and not lines[i].strip().startswith('#'):
                    if lines[i].strip():
                        description_lines.append(lines[i].strip())
                    i += 1
                i -= 1  # Back up one
                
                task.description = ' '.join(description_lines)
                
                # Handle hierarchy
                while current_stack and current_stack[-1][0] >= level:
                    current_stack.pop()
                    
                if current_stack:
                    parent_task = current_stack[-1][1]
                    parent_task.subtasks.append(task)
                else:
                    root_tasks.append(task)
                    
                current_stack.append((level, task))
            
            i += 1
            
        # Create all tasks
        created_count = 0
        for root_task in root_tasks:
            count = await self._create_task_hierarchy(root_task)
            created_count += count
            
        return {
            "status": "success",
            "created_tasks": created_count,
            "root_tasks": len(root_tasks),
            "task_mapping": dict(self.created_tasks)
        }
        
    async def create_tasks_from_simple_list(self, task_list: str) -> Dict[str, Any]:
        """
        Create tasks from a simple indented list.
        
        Format:
        ```
        Build Authentication:
          - Setup user model (high, 2h)
          - Create JWT utilities:
            - Token generation (1h)
            - Token validation (1h)
          - Build API endpoints (medium, 3h, needs: Setup user model)
          - Write tests (low, 2h, needs: Build API endpoints)
        ```
        
        Returns:
            Summary of created tasks
        """
        lines = task_list.strip().split('\n')
        root_task = None
        current_stack = []  # Stack of (indent_level, task) tuples
        
        for line in lines:
            if not line.strip():
                continue
                
            # Calculate indent level
            indent = len(line) - len(line.lstrip())
            line = line.strip()
            
            # Parse task
            if line.startswith('- '):
                task = self._parse_simple_task(line[2:])
                
                # Find parent based on indent
                while current_stack and current_stack[-1][0] >= indent:
                    current_stack.pop()
                    
                if current_stack:
                    parent = current_stack[-1][1]
                    parent.subtasks.append(task)
                    
                current_stack.append((indent, task))
            else:
                # Root task (no dash)
                if ':' in line:
                    title = line.rstrip(':')
                    root_task = ParsedTask(title=title)
                    current_stack = [(indent, root_task)]
                    
        # Create tasks
        if root_task:
            created_count = await self._create_task_hierarchy(root_task)
            return {
                "status": "success",
                "created_tasks": created_count,
                "task_mapping": dict(self.created_tasks)
            }
        else:
            return {
                "status": "error",
                "message": "No root task found"
            }
            
    async def create_tasks_from_yaml_simple(self, yaml_text: str) -> Dict[str, Any]:
        """
        Create tasks from simplified YAML format.
        
        Format:
        ```yaml
        epic: Build User System
        tasks:
          - Setup Database:
              priority: high
              hours: 2
              tasks:
                - Create user table
                - Add indexes
          - Build API:
              needs: [Setup Database]
              hours: 4
              tasks:
                - User CRUD endpoints: 
                    priority: high
                - Authentication endpoints
          - Testing:
              needs: [Build API]
              agent: test_agent
        ```
        """
        try:
            data = yaml.safe_load(yaml_text)
        except yaml.YAMLError as e:
            return {
                "status": "error", 
                "message": f"Invalid YAML: {e}"
            }
            
        # Create epic if specified
        epic_title = data.get('epic', 'Project Tasks')
        epic_task = ParsedTask(
            title=epic_title,
            description=data.get('description', ''),
            priority=data.get('priority', 'high')
        )
        
        # Parse tasks
        if 'tasks' in data:
            for task_item in data['tasks']:
                task = self._parse_yaml_task(task_item)
                if task:
                    epic_task.subtasks.append(task)
                    
        # Create all tasks
        created_count = await self._create_task_hierarchy(epic_task)
        
        return {
            "status": "success",
            "created_tasks": created_count,
            "epic": epic_title,
            "task_mapping": dict(self.created_tasks)
        }
        
    async def add_subtasks_to_existing(self, 
                                     parent_task_title: str,
                                     subtasks_text: str) -> Dict[str, Any]:
        """
        Add subtasks to an existing task using simple format.
        
        Format:
        ```
        - Subtask 1 (high, 2h)
        - Subtask 2 (1h)
        - Subtask 3 (needs: Subtask 1)
        ```
        """
        # Find parent task
        parent_id = self.created_tasks.get(parent_task_title)
        if not parent_id:
            # Try to find in graph
            for task_id, task in self.task_manager.graph.tasks.items():
                if task.title == parent_task_title:
                    parent_id = task_id
                    break
                    
        if not parent_id:
            return {
                "status": "error",
                "message": f"Parent task '{parent_task_title}' not found"
            }
            
        # Parse subtasks
        lines = subtasks_text.strip().split('\n')
        created_count = 0
        
        for line in lines:
            line = line.strip()
            if line.startswith('- '):
                task = self._parse_simple_task(line[2:])
                
                # Create the subtask
                node = await self.task_manager.create_task_from_description(
                    title=task.title,
                    description=task.description,
                    priority=self._get_priority_enum(task.priority),
                    parent_id=parent_id,
                    agent_type=task.agent
                )
                
                self.created_tasks[task.title] = node.id
                created_count += 1
                
        return {
            "status": "success",
            "parent_task": parent_task_title,
            "subtasks_added": created_count
        }
        
    def _parse_task_heading(self, heading: str) -> ParsedTask:
        """Parse a markdown heading into a task."""
        # Extract parts using regex
        # Format: Title [priority] @agent (hours) [depends: task1, task2]
        
        title = heading
        priority = "medium"
        agent = "coding_agent"
        hours = 0.0
        depends = []
        
        # Extract priority
        priority_match = re.search(r'\[(\w+)\]', heading)
        if priority_match:
            priority = priority_match.group(1).lower()
            title = heading.replace(priority_match.group(0), '').strip()
            
        # Extract agent
        agent_match = re.search(r'@(\w+)', heading)
        if agent_match:
            agent = agent_match.group(1)
            title = title.replace(agent_match.group(0), '').strip()
            
        # Extract hours
        hours_match = re.search(r'\((\d+(?:\.\d+)?)h?\)', heading)
        if hours_match:
            hours = float(hours_match.group(1))
            title = title.replace(hours_match.group(0), '').strip()
            
        # Extract dependencies
        deps_match = re.search(r'\[depends:\s*([^\]]+)\]', heading)
        if deps_match:
            depends = [d.strip() for d in deps_match.group(1).split(',')]
            title = title.replace(deps_match.group(0), '').strip()
            
        return ParsedTask(
            title=title.strip(),
            priority=priority,
            agent=agent,
            estimated_hours=hours,
            depends_on=depends
        )
        
    def _parse_simple_task(self, task_line: str) -> ParsedTask:
        """Parse a simple task line."""
        # Format: Task title (priority, hours, needs: dep1, dep2)
        
        title = task_line
        priority = "medium"
        hours = 0.0
        depends = []
        
        # Extract parenthetical info
        paren_match = re.search(r'\(([^)]+)\)', task_line)
        if paren_match:
            title = task_line[:paren_match.start()].strip()
            info = paren_match.group(1)
            
            # Parse info parts
            parts = [p.strip() for p in info.split(',')]
            for part in parts:
                if part in ['low', 'medium', 'high', 'critical']:
                    priority = part
                elif part.endswith('h'):
                    try:
                        hours = float(part[:-1])
                    except ValueError:
                        pass
                elif ':' in part and part.startswith('needs'):
                    deps_part = part.split(':', 1)[1]
                    depends = [d.strip() for d in deps_part.split(',')]
                elif part.replace('.', '').isdigit():
                    hours = float(part)
                    
        return ParsedTask(
            title=title,
            priority=priority,
            estimated_hours=hours,
            depends_on=depends
        )
        
    def _parse_yaml_task(self, task_data: Any) -> Optional[ParsedTask]:
        """Parse a YAML task definition."""
        if isinstance(task_data, str):
            return ParsedTask(title=task_data)
            
        elif isinstance(task_data, dict):
            # Get the task title (first key)
            title = list(task_data.keys())[0]
            props = task_data[title]
            
            if isinstance(props, dict):
                task = ParsedTask(
                    title=title,
                    priority=props.get('priority', 'medium'),
                    agent=props.get('agent', 'coding_agent'),
                    estimated_hours=props.get('hours', 0.0),
                    depends_on=props.get('needs', [])
                )
                
                # Parse subtasks
                if 'tasks' in props:
                    for subtask_item in props['tasks']:
                        subtask = self._parse_yaml_task(subtask_item)
                        if subtask:
                            task.subtasks.append(subtask)
                            
                return task
            else:
                return ParsedTask(title=title)
                
        return None
        
    async def _create_task_hierarchy(self, 
                                   parsed_task: ParsedTask, 
                                   parent_id: Optional[str] = None) -> int:
        """Recursively create task hierarchy."""
        # Resolve dependencies
        dependencies = set()
        for dep_title in parsed_task.depends_on:
            if dep_title in self.created_tasks:
                dependencies.add(self.created_tasks[dep_title])
                
        # Create the task
        node = await self.task_manager.create_task_from_description(
            title=parsed_task.title,
            description=parsed_task.description,
            priority=self._get_priority_enum(parsed_task.priority),
            parent_id=parent_id,
            agent_type=parsed_task.agent,
            dependencies=dependencies
        )
        
        # Store mapping
        self.created_tasks[parsed_task.title] = node.id
        
        # Set estimated hours
        if parsed_task.estimated_hours > 0:
            node.estimated_hours = parsed_task.estimated_hours
            
        # Create subtasks
        created_count = 1
        for subtask in parsed_task.subtasks:
            count = await self._create_task_hierarchy(subtask, node.id)
            created_count += count
            
        return created_count
        
    def _get_priority_enum(self, priority_str: str) -> TaskPriority:
        """Convert string priority to enum."""
        mapping = {
            'low': TaskPriority.LOW,
            'medium': TaskPriority.MEDIUM,
            'high': TaskPriority.HIGH,
            'critical': TaskPriority.CRITICAL
        }
        return mapping.get(priority_str.lower(), TaskPriority.MEDIUM)