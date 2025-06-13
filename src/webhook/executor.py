"""
Task executor for webhook-triggered agent commands.

This module handles the execution of agent tasks in response to
webhook events, with proper isolation and result tracking.
"""

import asyncio
import subprocess
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import json

from src.core.logging import get_logger, set_request_id, set_correlation_id
from src.core.settings import get_settings
from src.core.security import SecurityManager
from src.webhook.handlers import Task

logger = get_logger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskResult:
    """Result of task execution."""
    
    def __init__(self, task_id: str, task: Task):
        self.task_id = task_id
        self.task = task
        self.status = TaskStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.output = ""
        self.error = ""
        self.exit_code = None
        self.artifacts = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": (
                (self.end_time - self.start_time).total_seconds()
                if self.start_time and self.end_time else None
            ),
            "task": {
                "project": self.task.project_path,
                "command": self.task.command,
                "args": self.task.args,
                "source": self.task.source,
                "description": self.task.description
            },
            "output": self.output[-5000:] if self.output else "",  # Last 5000 chars
            "error": self.error,
            "exit_code": self.exit_code,
            "artifacts": self.artifacts
        }


class TaskExecutor:
    """Executes agent tasks from webhooks."""
    
    def __init__(self):
        """Initialize task executor."""
        self.settings = get_settings()
        self.tasks: Dict[str, TaskResult] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.workers = []
        self.running = False
        
        # Task limits
        self.max_concurrent_tasks = 5
        self.max_task_history = 1000
    
    async def start(self):
        """Start task executor workers."""
        self.running = True
        
        # Start worker tasks
        for i in range(self.max_concurrent_tasks):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
        
        logger.info(f"Started {len(self.workers)} task executor workers")
    
    async def stop(self):
        """Stop task executor."""
        self.running = False
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        logger.info("Stopped task executor")
    
    async def submit_task(self, task: Task) -> str:
        """
        Submit a task for execution.
        
        Args:
            task: Task to execute
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        result = TaskResult(task_id, task)
        
        # Store task
        self.tasks[task_id] = result
        
        # Clean old tasks if needed
        if len(self.tasks) > self.max_task_history:
            self._cleanup_old_tasks()
        
        # Queue for execution
        await self.queue.put((task_id, task))
        
        logger.info(f"Submitted task {task_id}: {task.command} for {task.project_path}")
        
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task."""
        result = self.tasks.get(task_id)
        if result:
            return result.to_dict()
        return None
    
    def active_task_count(self) -> int:
        """Get count of active tasks."""
        return sum(
            1 for r in self.tasks.values()
            if r.status in [TaskStatus.PENDING, TaskStatus.RUNNING]
        )
    
    def completed_task_count(self) -> int:
        """Get count of completed tasks."""
        return sum(
            1 for r in self.tasks.values()
            if r.status == TaskStatus.COMPLETED
        )
    
    async def _worker(self, worker_name: str):
        """Worker to process tasks from queue."""
        logger.info(f"Starting worker: {worker_name}")
        
        while self.running:
            try:
                # Get task from queue
                task_id, task = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )
                
                # Set context for logging
                set_request_id(task_id)
                set_correlation_id(task.source_id)
                
                # Execute task
                await self._execute_task(task_id, task)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}", exc_info=True)
    
    async def _execute_task(self, task_id: str, task: Task):
        """Execute a single task."""
        result = self.tasks[task_id]
        
        try:
            # Update status
            result.status = TaskStatus.RUNNING
            result.start_time = datetime.utcnow()
            
            logger.info(f"Executing task {task_id}: {task.command}")
            
            # Validate project path
            security = SecurityManager(Path(task.project_path))
            if not security.is_valid_project_root():
                raise ValueError(f"Invalid project path: {task.project_path}")
            
            # Build command
            cmd = self._build_command(task)
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=task.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**task.environment}
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=300  # 5 minute timeout
                )
                
                result.output = stdout.decode('utf-8', errors='replace')
                result.error = stderr.decode('utf-8', errors='replace')
                result.exit_code = process.returncode
                
                if process.returncode == 0:
                    result.status = TaskStatus.COMPLETED
                    logger.info(f"Task {task_id} completed successfully")
                else:
                    result.status = TaskStatus.FAILED
                    logger.warning(f"Task {task_id} failed with exit code {process.returncode}")
                
            except asyncio.TimeoutError:
                process.kill()
                result.status = TaskStatus.FAILED
                result.error = "Task execution timeout (5 minutes)"
                logger.error(f"Task {task_id} timed out")
            
        except Exception as e:
            result.status = TaskStatus.FAILED
            result.error = str(e)
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        
        finally:
            result.end_time = datetime.utcnow()
            
            # Save results if configured
            await self._save_results(task_id, result)
            
            # Notify webhook source if configured
            await self._notify_completion(task_id, result)
    
    def _build_command(self, task: Task) -> List[str]:
        """Build command to execute."""
        # Base command
        cmd = ["python", "-m", "src.cli", task.command]
        
        # Add project path
        cmd.extend(["--project-root", task.project_path])
        
        # Add task-specific args
        cmd.extend(task.args)
        
        return cmd
    
    async def _save_results(self, task_id: str, result: TaskResult):
        """Save task results to file."""
        # Create results directory
        results_dir = Path("webhook_results")
        results_dir.mkdir(exist_ok=True)
        
        # Save result
        result_file = results_dir / f"{task_id}.json"
        with open(result_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        
        logger.info(f"Saved results to {result_file}")
    
    async def _notify_completion(self, task_id: str, result: TaskResult):
        """Notify webhook source of task completion."""
        # This would integrate with notification services
        # For now, just log
        logger.info(
            f"Task {task_id} completed with status {result.status.value} "
            f"for {result.task.source}:{result.task.source_id}"
        )
    
    def _cleanup_old_tasks(self):
        """Remove old completed tasks."""
        # Sort by end time
        completed = [
            (tid, r) for tid, r in self.tasks.items()
            if r.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
            and r.end_time is not None
        ]
        completed.sort(key=lambda x: x[1].end_time)
        
        # Remove oldest
        to_remove = len(self.tasks) - self.max_task_history + 100  # Keep buffer
        for tid, _ in completed[:to_remove]:
            del self.tasks[tid]