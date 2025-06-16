"""
Queue metrics tracking for job processing statistics.

This module tracks job queue statistics including wait times,
processing times, and throughput metrics.
"""

from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
import asyncio
from dataclasses import dataclass, field
from enum import Enum

from src.core.logging import get_logger

logger = get_logger(__name__)


class JobStatus(Enum):
    """Job processing status."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobInfo:
    """Information about a job in the queue."""
    job_id: str
    job_type: str
    enqueued_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: JobStatus = JobStatus.QUEUED
    agent_type: Optional[str] = None
    error_message: Optional[str] = None
    
    @property
    def wait_time(self) -> Optional[float]:
        """Time spent waiting in queue (seconds)."""
        if self.started_at:
            return (self.started_at - self.enqueued_at).total_seconds()
        return None
    
    @property
    def processing_time(self) -> Optional[float]:
        """Time spent processing (seconds)."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def total_time(self) -> Optional[float]:
        """Total time from enqueue to completion (seconds)."""
        if self.completed_at:
            return (self.completed_at - self.enqueued_at).total_seconds()
        return None


class QueueMetrics:
    """Tracks job queue statistics and broadcasts metrics."""
    
    def __init__(self, realtime_service, history_size: int = 1000):
        """
        Initialize queue metrics tracker.
        
        Args:
            realtime_service: Service for WebSocket broadcasting
            history_size: Number of completed jobs to keep in history
        """
        self.realtime_service = realtime_service
        self.job_history = deque(maxlen=history_size)
        self.active_jobs: Dict[str, JobInfo] = {}
        self._lock = asyncio.Lock()
        self._metrics_task = None
        self._running = False
        
    async def start(self):
        """Start periodic metrics broadcasting."""
        if self._running:
            return
            
        self._running = True
        self._metrics_task = asyncio.create_task(self._broadcast_loop())
        logger.info("Started queue metrics tracking")
        
    async def stop(self):
        """Stop metrics broadcasting."""
        self._running = False
        if self._metrics_task:
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped queue metrics tracking")
        
    async def job_enqueued(self, job_id: str, job_type: str) -> None:
        """
        Track when a job is added to queue.
        
        Args:
            job_id: Unique job identifier
            job_type: Type of job (e.g., 'code_generation', 'refactoring')
        """
        async with self._lock:
            self.active_jobs[job_id] = JobInfo(
                job_id=job_id,
                job_type=job_type
            )
        
        logger.debug(f"Job {job_id} enqueued (type: {job_type})")
        await self._broadcast_metrics()
    
    async def job_started(self, job_id: str, agent_type: str) -> None:
        """
        Track when a job starts processing.
        
        Args:
            job_id: Job identifier
            agent_type: Type of agent processing the job
        """
        async with self._lock:
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                job.started_at = datetime.utcnow()
                job.status = JobStatus.PROCESSING
                job.agent_type = agent_type
            else:
                logger.warning(f"Job {job_id} started but not found in active jobs")
                
        logger.debug(f"Job {job_id} started by {agent_type}")
        await self._broadcast_metrics()
    
    async def job_completed(self, job_id: str, success: bool = True, error_message: Optional[str] = None) -> None:
        """
        Track job completion.
        
        Args:
            job_id: Job identifier
            success: Whether job completed successfully
            error_message: Error message if job failed
        """
        async with self._lock:
            if job_id in self.active_jobs:
                job = self.active_jobs.pop(job_id)
                job.completed_at = datetime.utcnow()
                job.status = JobStatus.COMPLETED if success else JobStatus.FAILED
                job.error_message = error_message
                self.job_history.append(job)
                
                logger.info(f"Job {job_id} completed - Success: {success}, "
                          f"Wait: {job.wait_time:.1f}s, "
                          f"Process: {job.processing_time:.1f}s")
            else:
                logger.warning(f"Job {job_id} completed but not found in active jobs")
                
        await self._broadcast_metrics()
    
    async def job_cancelled(self, job_id: str) -> None:
        """Track job cancellation."""
        async with self._lock:
            if job_id in self.active_jobs:
                job = self.active_jobs.pop(job_id)
                job.completed_at = datetime.utcnow()
                job.status = JobStatus.CANCELLED
                self.job_history.append(job)
                
        logger.debug(f"Job {job_id} cancelled")
        await self._broadcast_metrics()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Calculate current queue metrics."""
        metrics = {
            'queue_length': 0,
            'processing': 0,
            'completed_last_hour': 0,
            'failed_last_hour': 0,
            'avg_wait_time': 0,
            'avg_processing_time': 0,
            'throughput_per_minute': 0,
            'success_rate': 0,
            'by_type': {},
            'by_agent': {}
        }
        
        # Count active jobs
        for job in self.active_jobs.values():
            if job.status == JobStatus.QUEUED:
                metrics['queue_length'] += 1
            elif job.status == JobStatus.PROCESSING:
                metrics['processing'] += 1
        
        # Analyze completed jobs
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        minute_ago = now - timedelta(minutes=1)
        
        recent_jobs = [job for job in self.job_history if job.completed_at and job.completed_at > hour_ago]
        
        if recent_jobs:
            # Count completed and failed
            completed = [j for j in recent_jobs if j.status == JobStatus.COMPLETED]
            failed = [j for j in recent_jobs if j.status == JobStatus.FAILED]
            
            metrics['completed_last_hour'] = len(completed)
            metrics['failed_last_hour'] = len(failed)
            
            # Calculate success rate
            total = len(completed) + len(failed)
            metrics['success_rate'] = (len(completed) / total * 100) if total > 0 else 0
            
            # Calculate average times
            wait_times = [j.wait_time for j in recent_jobs if j.wait_time is not None]
            processing_times = [j.processing_time for j in recent_jobs if j.processing_time is not None]
            
            if wait_times:
                metrics['avg_wait_time'] = round(sum(wait_times) / len(wait_times), 1)
            if processing_times:
                metrics['avg_processing_time'] = round(sum(processing_times) / len(processing_times), 1)
            
            # Calculate throughput
            minute_jobs = [j for j in recent_jobs if j.completed_at > minute_ago]
            metrics['throughput_per_minute'] = len(minute_jobs)
            
            # Group by type
            type_counts = {}
            for job in recent_jobs:
                type_counts[job.job_type] = type_counts.get(job.job_type, 0) + 1
            metrics['by_type'] = type_counts
            
            # Group by agent
            agent_counts = {}
            for job in recent_jobs:
                if job.agent_type:
                    agent_counts[job.agent_type] = agent_counts.get(job.agent_type, 0) + 1
            metrics['by_agent'] = agent_counts
        
        return metrics
    
    async def _broadcast_metrics(self) -> None:
        """Calculate and broadcast queue metrics."""
        try:
            metrics = self.get_metrics()
            
            await self.realtime_service.broadcast({
                'type': 'queue_metrics',
                'timestamp': datetime.utcnow().isoformat(),
                'data': metrics
            }, topic='metrics')
        except Exception as e:
            logger.error(f"Error broadcasting queue metrics: {e}")
    
    async def _broadcast_loop(self) -> None:
        """Periodically broadcast metrics."""
        while self._running:
            try:
                await asyncio.sleep(10)  # Broadcast every 10 seconds
                await self._broadcast_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics broadcast loop: {e}")
    
    def get_job_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent job history.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job information dictionaries
        """
        jobs = list(self.job_history)[-limit:]
        return [
            {
                'job_id': job.job_id,
                'job_type': job.job_type,
                'status': job.status.value,
                'agent_type': job.agent_type,
                'enqueued_at': job.enqueued_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'wait_time': job.wait_time,
                'processing_time': job.processing_time,
                'total_time': job.total_time,
                'error_message': job.error_message
            }
            for job in reversed(jobs)
        ]