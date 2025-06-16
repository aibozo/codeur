"""
Metrics simulation for testing dashboard system monitoring.

This module simulates job processing and agent activity to demonstrate
the metrics collection capabilities.
"""

import asyncio
import random
from datetime import datetime
from typing import Optional

from src.core.agent_registry import AgentRegistry, AgentStatus
from src.core.queue_metrics import QueueMetrics
from src.core.flow_tracker import FlowTracker
from src.core.logging import get_logger
from src.core.log_streamer import LogContext

logger = get_logger(__name__)


class MetricsSimulator:
    """Simulates agent activity and job processing for metrics testing."""
    
    def __init__(self, registry: AgentRegistry, queue_metrics: QueueMetrics, 
                 flow_tracker: Optional[FlowTracker] = None):
        """
        Initialize simulator.
        
        Args:
            registry: Agent registry to update
            queue_metrics: Queue metrics tracker
            flow_tracker: Optional flow tracker for message flows
        """
        self.registry = registry
        self.queue_metrics = queue_metrics
        self.flow_tracker = flow_tracker
        self.running = False
        self._simulation_task = None
        
        # Agent types and their typical task durations
        self.agent_configs = {
            'request_planner': {
                'min_duration': 2,
                'max_duration': 5,
                'error_rate': 0.05,
                'task_types': ['plan_request', 'analyze_requirements', 'decompose_task']
            },
            'code_planner': {
                'min_duration': 3,
                'max_duration': 8,
                'error_rate': 0.08,
                'task_types': ['design_architecture', 'plan_implementation', 'review_approach']
            },
            'coding_agent': {
                'min_duration': 5,
                'max_duration': 15,
                'error_rate': 0.1,
                'task_types': ['implement_feature', 'fix_bug', 'refactor_code', 'write_tests']
            },
            'rag_service': {
                'min_duration': 1,
                'max_duration': 3,
                'error_rate': 0.02,
                'task_types': ['search_codebase', 'find_examples', 'retrieve_docs']
            },
            'git_operations': {
                'min_duration': 0.5,
                'max_duration': 2,
                'error_rate': 0.01,
                'task_types': ['commit_changes', 'create_branch', 'push_code']
            }
        }
        
        # Job types with their typical workflows
        self.job_workflows = {
            'feature_implementation': [
                ('request_planner', 'plan_request'),
                ('code_planner', 'design_architecture'),
                ('rag_service', 'search_codebase'),
                ('coding_agent', 'implement_feature'),
                ('git_operations', 'commit_changes')
            ],
            'bug_fix': [
                ('request_planner', 'analyze_requirements'),
                ('rag_service', 'find_examples'),
                ('coding_agent', 'fix_bug'),
                ('coding_agent', 'write_tests'),
                ('git_operations', 'commit_changes')
            ],
            'refactoring': [
                ('request_planner', 'decompose_task'),
                ('code_planner', 'review_approach'),
                ('coding_agent', 'refactor_code'),
                ('git_operations', 'commit_changes')
            ]
        }
    
    async def start(self, duration: Optional[int] = None):
        """
        Start the simulation.
        
        Args:
            duration: Run for specified seconds, or indefinitely if None
        """
        if self.running:
            logger.warning("Simulator already running")
            return
            
        self.running = True
        self._simulation_task = asyncio.create_task(self._run_simulation(duration))
        logger.info(f"Started metrics simulator (duration: {duration or 'indefinite'}s)")
    
    async def stop(self):
        """Stop the simulation."""
        self.running = False
        if self._simulation_task:
            self._simulation_task.cancel()
            try:
                await self._simulation_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped metrics simulator")
    
    async def _run_simulation(self, duration: Optional[int]):
        """Main simulation loop."""
        start_time = datetime.utcnow()
        job_counter = 0
        
        try:
            while self.running:
                # Check duration limit
                if duration and (datetime.utcnow() - start_time).total_seconds() > duration:
                    break
                
                # Start a new job workflow
                job_counter += 1
                job_type = random.choice(list(self.job_workflows.keys()))
                job_id = f"sim_job_{job_counter:04d}"
                
                # Run job workflow in background
                asyncio.create_task(self._simulate_job_workflow(job_id, job_type))
                
                # Wait before starting next job (simulate realistic arrival rate)
                await asyncio.sleep(random.uniform(3, 10))
                
        except asyncio.CancelledError:
            logger.info("Simulation cancelled")
        finally:
            self.running = False
    
    async def _simulate_job_workflow(self, job_id: str, job_type: str):
        """Simulate a complete job workflow."""
        with LogContext(job_id=job_id):
            logger.info(f"Starting job {job_id} ({job_type})")
            
            try:
                # Enqueue job
                await self.queue_metrics.job_enqueued(job_id, job_type)
                logger.debug(f"Job {job_id} enqueued")
                
                # Simulate queue wait time
                await asyncio.sleep(random.uniform(0.5, 3))
                
                # Get workflow steps
                workflow = self.job_workflows[job_type]
                
                # Execute each step
                prev_agent = None
                for agent_type, task_type in workflow:
                    # Simulate message flow from previous agent
                    if self.flow_tracker and prev_agent:
                        await self.flow_tracker.track_message(
                            from_agent=prev_agent,
                            to_agent=agent_type,
                            message_type='delegation',
                            payload_size=random.randint(100, 10000),
                            duration_ms=random.randint(10, 100)
                        )
                    
                    # Check if agent should fail
                    config = self.agent_configs[agent_type]
                    if random.random() < config['error_rate']:
                        # Simulate error
                        await self._simulate_agent_error(job_id, agent_type, task_type)
                        if self.flow_tracker and prev_agent:
                            await self.flow_tracker.track_message(
                                from_agent=agent_type,
                                to_agent=prev_agent,
                                message_type='error',
                                success=False
                            )
                        await self.queue_metrics.job_completed(
                            job_id, 
                            success=False, 
                            error_message=f"Agent {agent_type} failed during {task_type}"
                        )
                        return
                    
                    # Normal execution
                    await self._simulate_agent_task(job_id, agent_type, task_type, config)
                    prev_agent = agent_type
                
                # Job completed successfully
                await self.queue_metrics.job_completed(job_id, success=True)
                logger.debug(f"Completed job {job_id}")
                
            except Exception as e:
                logger.error(f"Error in job workflow {job_id}: {e}")
                await self.queue_metrics.job_completed(
                    job_id, 
                    success=False, 
                    error_message=str(e)
                )
    
    async def _simulate_agent_task(self, job_id: str, agent_type: str, task_type: str, config: dict):
        """Simulate an agent processing a task."""
        with LogContext(agent_type=agent_type, job_id=job_id):
            # Mark job as started by this agent
            if agent_type in ['request_planner', 'code_planner', 'coding_agent']:
                await self.queue_metrics.job_started(job_id, agent_type)
            
            logger.info(f"{agent_type} starting {task_type}")
            
            # Update agent status to active
            await self.registry.update_agent_status(
                agent_type,
                AgentStatus.ACTIVE,
                current_task=f"{task_type} for {job_id}"
            )
        
        # Simulate processing time
        duration = random.uniform(config['min_duration'], config['max_duration'])
        
        # Simulate internal queries (e.g., to RAG service)
        if self.flow_tracker and agent_type in ['code_planner', 'coding_agent']:
            # Query RAG service
            num_queries = random.randint(1, 3)
            logger.debug(f"{agent_type} querying RAG service ({num_queries} queries)")
            
            for i in range(num_queries):
                query_type = random.choice(['search_examples', 'find_similar', 'get_context'])
                logger.debug(f"{agent_type} -> RAG: {query_type}")
                
                await self.flow_tracker.track_message(
                    from_agent=agent_type,
                    to_agent='rag_service',
                    message_type='query',
                    payload_size=random.randint(50, 500),
                    duration_ms=random.randint(50, 200)
                )
                await asyncio.sleep(0.2)
                
                # RAG responds
                await self.flow_tracker.track_message(
                    from_agent='rag_service',
                    to_agent=agent_type,
                    message_type='response',
                    payload_size=random.randint(1000, 5000),
                    duration_ms=random.randint(100, 500)
                )
                await asyncio.sleep(0.1)
        
        # Simulate git operations
        if self.flow_tracker and agent_type == 'coding_agent' and random.random() > 0.5:
            await self.flow_tracker.track_message(
                from_agent=agent_type,
                to_agent='git_operations',
                message_type='command',
                payload_size=random.randint(100, 1000),
                duration_ms=random.randint(50, 150)
            )
        
            await asyncio.sleep(duration)
            
            # Update agent metrics
            metrics = {
                'tokens_used': random.randint(100, 5000),
                'requests_made': random.randint(1, 5),
                'cache_hits': random.randint(0, 10),
                'processing_time': duration
            }
            await self.registry.update_agent_metrics(agent_type, metrics)
            
            logger.info(f"{agent_type} completed {task_type} in {duration:.1f}s "
                       f"(tokens: {metrics['tokens_used']})")
            
            # Return to idle
            await self.registry.update_agent_status(agent_type, AgentStatus.IDLE)
    
    async def _simulate_agent_error(self, job_id: str, agent_type: str, task_type: str):
        """Simulate an agent error."""
        # Update agent status to error
        error_messages = [
            "Token limit exceeded",
            "API rate limit reached",
            "Model timeout",
            "Invalid response format",
            "Context length exceeded"
        ]
        
        await self.registry.update_agent_status(
            agent_type,
            AgentStatus.ERROR,
            current_task=f"{task_type} for {job_id}",
            error_message=random.choice(error_messages)
        )
        
        # Wait a bit then recover
        await asyncio.sleep(random.uniform(2, 5))
        await self.registry.update_agent_status(agent_type, AgentStatus.IDLE)


async def run_metrics_simulation(registry: AgentRegistry, queue_metrics: QueueMetrics, 
                               flow_tracker: Optional[FlowTracker] = None, duration: int = 60):
    """
    Run a metrics simulation for testing.
    
    Args:
        registry: Agent registry instance
        queue_metrics: Queue metrics instance
        flow_tracker: Optional flow tracker instance
        duration: Simulation duration in seconds
    """
    simulator = MetricsSimulator(registry, queue_metrics, flow_tracker)
    
    try:
        await simulator.start(duration)
        # Wait for completion
        if duration:
            await asyncio.sleep(duration + 1)
        else:
            # Run indefinitely until interrupted
            await asyncio.Event().wait()
    finally:
        await simulator.stop()