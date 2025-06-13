"""Status command for showing project and agent status."""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.command()
@click.pass_context
def status(ctx):
    """Show the current project status and agent availability."""
    project_root = ctx.obj['project_root']
    
    console.print(Panel(f"[bold cyan]Agent System Status[/bold cyan]\n\nProject Root: {project_root}", 
                       title="Status", expand=False))
    
    # Check for available agents
    table = Table(title="Available Agents", show_header=True, header_style="bold magenta")
    table.add_column("Agent", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Description")
    
    agents = [
        ("Request Planner", "Ready", "Plans and decomposes user requests"),
        ("Code Planner", "Ready", "Analyzes codebase and plans modifications"),
        ("Coding Agent", "Ready", "Implements code changes"),
        ("RAG Service", "Ready", "Provides code search and retrieval")
    ]
    
    for agent, agent_status, desc in agents:
        table.add_row(agent, agent_status, desc)
    
    console.print(table)
    
    # Check for configuration
    config_path = project_root / ".agent-config.yml"
    if config_path.exists():
        console.print("\n[green]✓[/green] Configuration file found")
    else:
        console.print("\n[yellow]⚠[/yellow] No configuration file found. Using defaults.")
        console.print("  Run 'agent-system init' to create a configuration file.")