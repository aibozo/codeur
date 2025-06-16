"""
Intelligent Task Scheduler for the enhanced task graph system.

This module handles task assignment, prioritization, and execution scheduling
based on agent capabilities, task dependencies, and resource availability.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import heapq

from src.architect.enhanced_task_graph import (
    EnhancedTaskNode, EnhancedTaskGraph, TaskStatus, 
    TaskPriority, TaskGranularity, TaskCommunity
)
from src.core.agent_registry import AgentRegistry, AgentState, AgentStatus

logger = logging.getLogger(__name__)


@dataclass
class TaskAssignment:
    """Represents a task assignment to an agent."""
    task_id: str
    agent_type: str
    agent_id: Optional[str] = None
    assigned_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    

@dataclass
class SchedulerMetrics:
    """Metrics for scheduler performance."""
    tasks_scheduled: int = 0
    tasks_completed: int = 0
    average_wait_time: float = 0.0
    average_execution_time: float = 0.0
    agent_utilization: Dict[str, float] = field(default_factory=dict)
    

class TaskScheduler:
    """
    Intelligent scheduler for task execution.
    
    Features:
    - Priority-based scheduling with dependency resolution
    - Agent capability matching
    - Load balancing across agents
    - Community-aware batch scheduling
    - Resource optimization
    """
    
    def __init__(self, 
                 agent_registry: AgentRegistry,
                 max_concurrent_tasks: int = 10,
                 scheduling_interval: float = 5.0):
        """
        Initialize the task scheduler.
        
        Args:
            agent_registry: Registry of available agents
            max_concurrent_tasks: Maximum tasks to run concurrently
            scheduling_interval: How often to run scheduling (seconds)
        """
        self.agent_registry = agent_registry
        self.max_concurrent_tasks = max_concurrent_tasks
        self.scheduling_interval = scheduling_interval
        
        # Task tracking
        self.active_assignments: Dict[str, TaskAssignment] = {}
        self.task_queue: List[Tuple[float, str, EnhancedTaskNode]] = []  # Priority queue
        self.agent_queues: Dict[str, List[str]] = defaultdict(list)  # Per-agent queues
        
        # Metrics
        self.metrics = SchedulerMetrics()
        
        # Scheduling state
        self._running = False
        self._scheduler_task = None
        
    async def start(self):
        """Start the scheduler."""
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduling_loop())
        logger.info("Task scheduler started")
        
    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Task scheduler stopped")
        
    async def schedule_graph(self, graph: EnhancedTaskGraph):
        """
        Schedule all ready tasks from a task graph.
        
        Args:
            graph: The task graph to schedule from
        """
        ready_tasks = graph.get_ready_tasks()
        
        for task in ready_tasks:
            if isinstance(task, EnhancedTaskNode):
                await self.schedule_task(task, graph)
            
    async def schedule_task(self, task: EnhancedTaskNode, graph: Optional[EnhancedTaskGraph] = None):
        """
        Schedule a single task for execution.
        
        Args:
            task: The task to schedule
            graph: Optional graph for context
        """
        # Skip if already scheduled or running
        if task.id in self.active_assignments:
            return
            
        # Calculate priority score
        priority_score = self._calculate_priority(task, graph)
        
        # Add to priority queue
        heapq.heappush(self.task_queue, (-priority_score, task.id, task))
        
        logger.info(f"Scheduled task {task.id}: {task.title} (priority: {priority_score:.2f})")
        
    def _calculate_priority(self, task: EnhancedTaskNode, graph: Optional[EnhancedTaskGraph] = None) -> float:
        """
        Calculate priority score for a task.
        
        Considers:
        - Base priority level
        - Critical path membership
        - Community urgency
        - Subtask count (prefer tasks with more subtasks)
        - Age of task
        """
        score = 0.0
        
        # Base priority
        priority_weights = {
            TaskPriority.CRITICAL: 100.0,
            TaskPriority.HIGH: 50.0,
            TaskPriority.MEDIUM: 20.0,
            TaskPriority.LOW: 10.0
        }
        score += priority_weights.get(task.priority, 10.0)
        
        # Critical path bonus
        if graph and task.id in graph.get_critical_path():
            score += 30.0
            
        # Subtask bonus (prefer tasks that unlock more work)
        score += len(task.subtask_ids) * 5.0
        
        # Age bonus (older tasks get slight priority)
        age_hours = (datetime.utcnow() - task.created_at).total_seconds() / 3600
        score += min(age_hours * 0.5, 10.0)  # Cap at 10 points
        
        # Community bonus (tasks in active communities)
        if graph and task.community_id:
            community = graph.communities.get(task.community_id)
            if community:
                # Bonus based on community completion percentage
                comm_tasks = graph.get_community_tasks(task.community_id)
                if comm_tasks:
                    completion_rate = len([t for t in comm_tasks if t.status == TaskStatus.COMPLETED]) / len(comm_tasks)
                    # Higher bonus for communities that are almost complete
                    if completion_rate > 0.7:
                        score += 20.0
                        
        return score
        
    async def _scheduling_loop(self):
        """Main scheduling loop."""
        while self._running:
            try:
                await self._schedule_batch()
                await asyncio.sleep(self.scheduling_interval)
            except Exception as e:
                logger.error(f"Scheduling error: {e}")
                
    async def _schedule_batch(self):
        """Schedule a batch of tasks to agents."""
        # Get available agents
        agents = await self.agent_registry.get_all_agents()
        available_agents = [
            agent for agent in agents 
            if agent.status in [AgentStatus.IDLE, AgentStatus.ACTIVE]
        ]
        
        if not available_agents or not self.task_queue:
            return
            
        # Count active tasks per agent type
        agent_load = defaultdict(int)
        for assignment in self.active_assignments.values():
            agent_load[assignment.agent_type] += 1
            
        # Schedule tasks
        scheduled_count = 0
        max_batch = min(len(self.task_queue), self.max_concurrent_tasks - len(self.active_assignments))
        
        while self.task_queue and scheduled_count < max_batch:
            # Get highest priority task
            _, task_id, task = heapq.heappop(self.task_queue)
            
            # Find suitable agent
            agent = self._find_best_agent(task, available_agents, agent_load)
            if not agent:
                # No suitable agent, requeue
                heapq.heappush(self.task_queue, (self._calculate_priority(task, None), task_id, task))
                break
                
            # Create assignment
            assignment = TaskAssignment(
                task_id=task.id,
                agent_type=agent.agent_type,
                agent_id=agent.agent_type  # Using type as ID for now
            )
            
            self.active_assignments[task.id] = assignment
            agent_load[agent.agent_type] += 1
            scheduled_count += 1
            
            # Notify about assignment
            await self._execute_task(task, agent)
            
        if scheduled_count > 0:
            logger.info(f"Scheduled {scheduled_count} tasks in batch")
            
    def _find_best_agent(self, 
                        task: EnhancedTaskNode, 
                        agents: List[AgentState],
                        agent_load: Dict[str, int]) -> Optional[AgentState]:
        """
        Find the best agent for a task.
        
        Considers:
        - Agent type matching
        - Current agent load
        - Agent capabilities
        """
        # Filter agents by type
        suitable_agents = [
            agent for agent in agents 
            if agent.agent_type == task.agent_type or task.agent_type in agent.capabilities
        ]
        
        if not suitable_agents:
            # Try to find any agent that can handle it
            suitable_agents = [
                agent for agent in agents
                if 'universal' in agent.capabilities or not task.agent_type
            ]
            
        if not suitable_agents:
            return None
            
        # Sort by load (ascending)
        suitable_agents.sort(key=lambda a: agent_load.get(a.agent_type, 0))
        
        return suitable_agents[0]
        
    async def _execute_task(self, task: EnhancedTaskNode, agent: AgentState):
        """
        Execute a task on an agent.
        
        This is where we would actually send the task to the agent.
        For now, it's a placeholder that simulates execution.
        """
        logger.info(f"Executing task {task.id} on agent {agent.agent_type}")
        
        # Update task status
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.utcnow()
        
        # Update agent status
        await self.agent_registry.update_agent_status(
            agent.agent_type,
            AgentStatus.ACTIVE,
            current_task=task.title
        )
        
        # TODO: Actually send task to agent via message queue
        # For now, simulate with a delay
        asyncio.create_task(self._simulate_task_execution(task, agent))
        
    async def _simulate_task_execution(self, task: EnhancedTaskNode, agent: AgentState):
        """Simulate task execution for testing."""
        # Simulate execution time based on estimated hours
        execution_time = min(task.estimated_hours * 10, 60)  # 10s per hour, max 60s
        await asyncio.sleep(execution_time)
        
        # Mark as completed
        await self.complete_task(task.id, success=True)
        
    async def complete_task(self, task_id: str, success: bool = True, error_message: Optional[str] = None):
        """
        Mark a task as completed.
        
        Args:
            task_id: The task ID
            success: Whether the task succeeded
            error_message: Error message if failed
        """
        if task_id not in self.active_assignments:
            logger.warning(f"Attempted to complete unassigned task: {task_id}")
            return
            
        assignment = self.active_assignments[task_id]
        
        # Update metrics
        self.metrics.tasks_completed += 1
        if assignment.started_at:
            execution_time = (datetime.utcnow() - assignment.started_at).total_seconds()
            # Update rolling average
            self.metrics.average_execution_time = (
                (self.metrics.average_execution_time * (self.metrics.tasks_completed - 1) + execution_time) /
                self.metrics.tasks_completed
            )
            
        # Remove from active assignments
        del self.active_assignments[task_id]
        
        # Update agent status
        await self.agent_registry.update_agent_status(
            assignment.agent_type,
            AgentStatus.IDLE
        )
        
        logger.info(f"Task {task_id} completed (success: {success})")
        
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status and metrics."""
        return {
            'running': self._running,
            'active_tasks': len(self.active_assignments),
            'queued_tasks': len(self.task_queue),
            'metrics': {
                'tasks_scheduled': self.metrics.tasks_scheduled,
                'tasks_completed': self.metrics.tasks_completed,
                'average_wait_time': self.metrics.average_wait_time,
                'average_execution_time': self.metrics.average_execution_time,
            },
            'active_assignments': [
                {
                    'task_id': assignment.task_id,
                    'agent': assignment.agent_type,
                    'assigned_at': assignment.assigned_at.isoformat(),
                    'duration': (datetime.utcnow() - assignment.assigned_at).total_seconds()
                }
                for assignment in self.active_assignments.values()
            ]
        }
        
    async def optimize_schedule(self, graph: EnhancedTaskGraph):
        """
        Optimize task scheduling based on graph analysis.
        
        Features:
        - Batch similar tasks (same community)
        - Prioritize critical path
        - Balance agent loads
        """
        # Group tasks by community
        community_tasks = defaultdict(list)
        for task in graph.get_ready_tasks():
            if isinstance(task, EnhancedTaskNode) and task.community_id:
                community_tasks[task.community_id].append(task)
                
        # Schedule community batches
        for community_id, tasks in community_tasks.items():
            # Sort by priority within community
            tasks.sort(key=lambda t: self._calculate_priority(t, graph), reverse=True)
            
            # Schedule the batch
            for task in tasks:
                await self.schedule_task(task, graph)
                
        # Schedule remaining tasks
        for task in graph.get_ready_tasks():
            if isinstance(task, EnhancedTaskNode) and not task.community_id:
                await self.schedule_task(task, graph)