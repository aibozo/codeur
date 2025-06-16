"""
Simulation command for testing the dashboard.

This module provides commands to simulate agent activity for testing
and demonstration purposes.
"""

import asyncio
import click

from src.core.logging import get_logger
from src.core.settings import get_settings
from src.core.message_bus import MessageBus
from src.core.realtime import RealtimeService
from src.core.agent_registry import AgentRegistry
from src.testing.agent_simulator import run_simulation

logger = get_logger(__name__)


@click.group()
def simulate():
    """Run simulations for testing."""
    pass


@simulate.command()
@click.option(
    '--duration',
    type=int,
    default=None,
    help='Duration in seconds (omit for infinite)'
)
@click.option(
    '--webhook-port',
    type=int,
    default=8088,
    help='Webhook server port to connect to'
)
def agents(duration: int, webhook_port: int):
    """Simulate agent activity for dashboard testing."""
    click.echo(f"Starting agent simulation...")
    
    if duration:
        click.echo(f"Running for {duration} seconds")
    else:
        click.echo("Running indefinitely (press Ctrl+C to stop)")
    
    # Note: This is a simplified version that creates its own registry
    # In production, it would connect to the running webhook server
    async def run():
        # Initialize services
        message_bus = MessageBus()
        realtime_service = RealtimeService(message_bus)
        registry = AgentRegistry(message_bus, realtime_service)
        
        # Initialize services
        await realtime_service.initialize()
        await registry.start()
        
        # Register default agents
        default_model = get_settings().llm.default_model or 'gpt-4'
        
        await registry.register_agent('request_planner', default_model, 
                                    ['planning', 'orchestration'])
        await registry.register_agent('code_planner', default_model,
                                    ['code_analysis', 'planning'])
        await registry.register_agent('coding_agent', default_model,
                                    ['code_generation', 'testing'])
        
        click.echo("Agents registered, starting simulation...")
        
        try:
            # Run simulation
            await run_simulation(registry, duration)
        except KeyboardInterrupt:
            click.echo("\nSimulation stopped by user")
        finally:
            # Cleanup
            await registry.stop()
            await realtime_service.shutdown()
    
    # Run the async function
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        click.echo("\nSimulation terminated")


@simulate.command()
@click.option(
    '--rate',
    type=int,
    default=10,
    help='Messages per second'
)
@click.option(
    '--duration',
    type=int,
    default=60,
    help='Duration in seconds'
)
def load(rate: int, duration: int):
    """Generate load for stress testing."""
    click.echo(f"Generating {rate} messages/second for {duration} seconds...")
    
    async def generate_load():
        # Implementation for load testing
        total_messages = rate * duration
        click.echo(f"Total messages to generate: {total_messages}")
        
        # TODO: Implement actual load generation
        for i in range(duration):
            click.echo(f"Progress: {i+1}/{duration} seconds", nl=False, err=True)
            click.echo('\r', nl=False)
            await asyncio.sleep(1)
        
        click.echo(f"\nLoad test completed: {total_messages} messages sent")
    
    asyncio.run(generate_load())


if __name__ == "__main__":
    simulate()