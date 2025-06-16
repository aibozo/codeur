"""
CLI commands for metrics and monitoring.
"""

import asyncio
import os
import click

from src.core.settings import get_settings
from src.webhook.server import create_webhook_server
from src.testing.metrics_simulator import run_metrics_simulation


@click.group()
def metrics():
    """Metrics and monitoring commands."""
    pass


@metrics.command()
@click.option(
    '--duration',
    '-d',
    default=60,
    help='Simulation duration in seconds (0 for indefinite)'
)
@click.option(
    '--webhook-url',
    default='http://localhost:8088',
    help='Webhook server URL'
)
def simulate(duration: int, webhook_url: str):
    """Run metrics simulation to test dashboard monitoring."""
    settings = get_settings()
    
    click.echo(f"Starting metrics simulation for {duration}s...")
    click.echo(f"Webhook server URL: {webhook_url}")
    click.echo("Make sure the webhook server is running!")
    click.echo("")
    click.echo("This will simulate:")
    click.echo("- Agent activity and status changes")
    click.echo("- Job processing with realistic workflows")
    click.echo("- System metrics collection")
    click.echo("- Random errors and recovery")
    click.echo("")
    
    async def run_simulation():
        """Run the simulation with webhook server's registries."""
        # Ensure webhook is enabled for creating server
        os.environ["AGENT_WEBHOOK_ENABLED"] = "true"
        
        # Create a minimal webhook server instance to get registries
        server = create_webhook_server()
        
        # Initialize services
        await server.realtime_service.initialize()
        await server.agent_registry.start()
        await server.metrics_collector.start()
        await server.queue_metrics.start()
        await server.flow_tracker.start()
        
        # Register default agents
        await server._register_default_agents()
        
        try:
            # Run simulation
            await run_metrics_simulation(
                server.agent_registry,
                server.queue_metrics,
                server.flow_tracker,
                duration if duration > 0 else None
            )
        finally:
            # Cleanup
            await server.agent_registry.stop()
            await server.metrics_collector.stop()
            await server.queue_metrics.stop()
            await server.flow_tracker.stop()
            await server.realtime_service.shutdown()
    
    try:
        asyncio.run(run_simulation())
    except KeyboardInterrupt:
        click.echo("\nSimulation stopped by user")


@metrics.command()
@click.option(
    '--webhook-url',
    default='http://localhost:8088',
    help='Webhook server URL'
)
def status(webhook_url: str):
    """Check current metrics status from webhook server."""
    import httpx
    
    click.echo(f"Checking metrics status at {webhook_url}...")
    
    try:
        # Check system metrics
        response = httpx.get(f"{webhook_url}/api/metrics/system")
        if response.status_code == 200:
            metrics = response.json()
            
            click.echo("\n=== System Metrics ===")
            if 'cpu' in metrics:
                cpu = metrics['cpu']
                click.echo(f"CPU Usage: {cpu.get('usage_percent', 0):.1f}%")
                click.echo(f"CPU Cores: {cpu.get('cores_physical', 0)} physical, {cpu.get('cores_logical', 0)} logical")
            
            if 'memory' in metrics:
                mem = metrics['memory']
                click.echo(f"\nMemory: {mem.get('used_gb', 0):.1f}/{mem.get('total_gb', 0):.1f} GB ({mem.get('percent', 0):.1f}%)")
            
            if 'gpu' in metrics and metrics['gpu']:
                click.echo("\n=== GPU Metrics ===")
                for gpu in metrics['gpu']:
                    click.echo(f"GPU {gpu.get('id', 0)}: {gpu.get('name', 'Unknown')}")
                    click.echo(f"  Load: {gpu.get('load_percent', 0):.1f}%")
                    click.echo(f"  Memory: {gpu.get('memory_used_mb', 0):.0f}/{gpu.get('memory_total_mb', 0):.0f} MB")
                    click.echo(f"  Temperature: {gpu.get('temperature', 0)}°C")
        
        # Check queue metrics
        response = httpx.get(f"{webhook_url}/api/metrics/queue")
        if response.status_code == 200:
            queue = response.json()
            
            click.echo("\n=== Queue Metrics ===")
            click.echo(f"Queue Length: {queue.get('queue_length', 0)}")
            click.echo(f"Processing: {queue.get('processing', 0)}")
            click.echo(f"Completed (1h): {queue.get('completed_last_hour', 0)}")
            click.echo(f"Failed (1h): {queue.get('failed_last_hour', 0)}")
            click.echo(f"Success Rate: {queue.get('success_rate', 0):.1f}%")
            click.echo(f"Avg Wait Time: {queue.get('avg_wait_time', 0):.1f}s")
            click.echo(f"Avg Process Time: {queue.get('avg_processing_time', 0):.1f}s")
            
            if queue.get('by_type'):
                click.echo("\nJobs by Type:")
                for job_type, count in queue['by_type'].items():
                    click.echo(f"  {job_type}: {count}")
            
            if queue.get('by_agent'):
                click.echo("\nJobs by Agent:")
                for agent, count in queue['by_agent'].items():
                    click.echo(f"  {agent}: {count}")
        
        # Check graph data
        response = httpx.get(f"{webhook_url}/api/graph/stats")
        if response.status_code == 200:
            stats = response.json()
            
            click.echo("\n=== Agent Graph ===")
            graph = stats.get('graph', {})
            click.echo(f"Nodes: {graph.get('node_count', 0)}")
            click.echo(f"Edges: {graph.get('edge_count', 0)}")
            click.echo(f"Density: {graph.get('density', 0):.3f}")
            
            flows = stats.get('flows', {})
            click.echo(f"\nTotal Messages: {flows.get('total_messages', 0)}")
            click.echo(f"Active Flows: {flows.get('active_flows', 0)}")
            
            if flows.get('edge_counts'):
                click.echo("\nTop Message Routes:")
                sorted_edges = sorted(flows['edge_counts'].items(), 
                                    key=lambda x: x[1], reverse=True)[:5]
                for edge, count in sorted_edges:
                    from_agent, to_agent = eval(edge)  # Parse tuple string
                    click.echo(f"  {from_agent} → {to_agent}: {count} messages")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Make sure the webhook server is running!", err=True)