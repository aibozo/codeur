"""
Agent Activity Simulator for testing the dashboard.

This module simulates realistic agent activity to test and demonstrate
the real-time dashboard functionality.
"""

import asyncio
import random
from datetime import datetime
from typing import List, Optional

from src.core.agent_registry import AgentRegistry, AgentStatus
from src.core.logging import get_logger

logger = get_logger(__name__)


class AgentSimulator:
    """Simulates agent activity for testing the dashboard."""
    
    def __init__(self, agent_registry: AgentRegistry):
        """
        Initialize the simulator.
        
        Args:
            agent_registry: The agent registry to update
        """
        self.registry = agent_registry
        self.running = False
        self.tasks = [
            "Analyzing user request",
            "Planning implementation approach", 
            "Generating code structure",
            "Writing unit tests",
            "Refactoring for clarity",
            "Optimizing performance",
            "Adding documentation",
            "Running code analysis",
            "Fixing linting issues",
            "Preparing commit"
        ]
        
    async def start(self):
        """Start the simulation."""
        self.running = True
        logger.info("Agent simulator started")
        
        # Start multiple simulation tasks
        await asyncio.gather(
            self._simulate_request_planner(),
            self._simulate_code_planner(),
            self._simulate_coding_agent(),
            self._simulate_random_errors(),
            self._simulate_metrics_updates()
        )
    
    def stop(self):
        """Stop the simulation."""
        self.running = False
        logger.info("Agent simulator stopped")
    
    async def _simulate_request_planner(self):
        """Simulate request planner agent activity."""
        while self.running:
            try:
                # Wait for next task
                await asyncio.sleep(random.uniform(5, 15))
                
                # Start task
                task = random.choice([
                    "Processing user story",
                    "Analyzing requirements",
                    "Breaking down complex request",
                    "Validating project context"
                ])
                
                await self.registry.update_agent_status(
                    'request_planner',
                    AgentStatus.ACTIVE,
                    task
                )
                
                # Work on task
                await asyncio.sleep(random.uniform(2, 5))
                
                # Update metrics
                await self.registry.update_agent_metrics('request_planner', {
                    'requests_processed': 1,
                    'avg_processing_time': random.uniform(1.5, 4.0),
                    'tokens_used': random.randint(500, 2000)
                })
                
                # Complete task
                await self.registry.update_agent_status(
                    'request_planner',
                    AgentStatus.IDLE
                )
                
            except Exception as e:
                logger.error(f"Error in request planner simulation: {e}")
                await asyncio.sleep(1)
    
    async def _simulate_code_planner(self):
        """Simulate code planner agent activity."""
        while self.running:
            try:
                # Wait for trigger from request planner
                await asyncio.sleep(random.uniform(7, 20))
                
                # Start planning
                task = random.choice([
                    "Designing solution architecture",
                    "Creating implementation plan",
                    "Analyzing code dependencies",
                    "Planning test strategy"
                ])
                
                await self.registry.update_agent_status(
                    'code_planner',
                    AgentStatus.ACTIVE,
                    task
                )
                
                # Planning phase
                await asyncio.sleep(random.uniform(3, 7))
                
                # Update metrics
                await self.registry.update_agent_metrics('code_planner', {
                    'plans_created': 1,
                    'complexity_score': random.uniform(0.3, 0.9),
                    'estimated_effort': random.randint(1, 8)
                })
                
                # Complete
                await self.registry.update_agent_status(
                    'code_planner',
                    AgentStatus.IDLE
                )
                
            except Exception as e:
                logger.error(f"Error in code planner simulation: {e}")
                await asyncio.sleep(1)
    
    async def _simulate_coding_agent(self):
        """Simulate coding agent activity."""
        while self.running:
            try:
                # Wait for task from planner
                await asyncio.sleep(random.uniform(10, 25))
                
                # Start coding
                task = random.choice(self.tasks)
                
                await self.registry.update_agent_status(
                    'coding_agent',
                    AgentStatus.ACTIVE,
                    task
                )
                
                # Simulate multiple steps
                steps = random.randint(2, 5)
                for i in range(steps):
                    await asyncio.sleep(random.uniform(1, 3))
                    
                    # Update progress
                    await self.registry.update_agent_metrics('coding_agent', {
                        'lines_written': random.randint(10, 100),
                        'files_modified': random.randint(1, 5),
                        'tests_written': random.randint(0, 10)
                    })
                
                # Complete
                await self.registry.update_agent_status(
                    'coding_agent',
                    AgentStatus.IDLE
                )
                
            except Exception as e:
                logger.error(f"Error in coding agent simulation: {e}")
                await asyncio.sleep(1)
    
    async def _simulate_random_errors(self):
        """Occasionally simulate agent errors."""
        while self.running:
            try:
                # Wait longer between errors
                await asyncio.sleep(random.uniform(30, 60))
                
                # Pick a random agent
                agent = random.choice(['request_planner', 'code_planner', 'coding_agent'])
                
                # Simulate error
                error_messages = [
                    "API rate limit exceeded",
                    "Context window overflow", 
                    "Invalid response format",
                    "Timeout waiting for model response"
                ]
                
                await self.registry.update_agent_status(
                    agent,
                    AgentStatus.ERROR,
                    error_message=random.choice(error_messages)
                )
                
                # Recovery time
                await asyncio.sleep(random.uniform(3, 10))
                
                # Recover
                await self.registry.update_agent_status(
                    agent,
                    AgentStatus.IDLE
                )
                
            except Exception as e:
                logger.error(f"Error in error simulation: {e}")
                await asyncio.sleep(1)
    
    async def _simulate_metrics_updates(self):
        """Periodically update agent metrics."""
        while self.running:
            try:
                await asyncio.sleep(5)  # Update every 5 seconds
                
                # Update various metrics for active agents
                agents = await self.registry.get_all_agents()
                
                for agent in agents:
                    if agent.status == AgentStatus.ACTIVE:
                        # Increment some metrics
                        current_metrics = agent.metrics.copy()
                        
                        if 'total_tokens' in current_metrics:
                            current_metrics['total_tokens'] += random.randint(10, 100)
                        else:
                            current_metrics['total_tokens'] = random.randint(100, 1000)
                        
                        if 'success_rate' not in current_metrics:
                            current_metrics['success_rate'] = random.uniform(0.85, 0.99)
                        
                        await self.registry.update_agent_metrics(
                            agent.agent_type,
                            current_metrics
                        )
                
            except Exception as e:
                logger.error(f"Error in metrics simulation: {e}")
                await asyncio.sleep(1)


async def run_simulation(registry: AgentRegistry, duration: Optional[int] = None):
    """
    Run the agent simulation.
    
    Args:
        registry: Agent registry instance
        duration: How long to run (seconds), None for infinite
    """
    simulator = AgentSimulator(registry)
    
    try:
        if duration:
            # Run for specified duration
            await asyncio.wait_for(simulator.start(), timeout=duration)
        else:
            # Run indefinitely
            await simulator.start()
    except asyncio.TimeoutError:
        logger.info(f"Simulation completed after {duration} seconds")
    finally:
        simulator.stop()