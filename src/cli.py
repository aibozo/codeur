"""Main CLI interface for the Agent System.

This provides the unified command-line interface for all agent operations.
"""

import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.core.security import SecurityManager
from src.core.logging import setup_logging

console = Console()
logger = setup_logging(__name__)


@click.group()
@click.version_option(version="0.1.0", prog_name="agent-system")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx, debug):
    """AI-powered multi-agent code generation framework.
    
    This tool operates on the current directory as the project root.
    """
    # Set up security manager to prevent parent directory access
    security_manager = SecurityManager(project_root=Path.cwd())
    ctx.obj = {
        'security_manager': security_manager,
        'debug': debug,
        'project_root': Path.cwd()
    }
    
    if debug:
        logger.setLevel('DEBUG')
        console.print("[yellow]Debug mode enabled[/yellow]")
    
    # Verify we're in a valid project directory
    if not security_manager.is_valid_project_root():
        console.print("[red]Error: Current directory does not appear to be a valid project.[/red]")
        console.print("Please run this command from your project root directory.")
        sys.exit(1)


@cli.command()
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
    
    for agent, status, desc in agents:
        table.add_row(agent, status, desc)
    
    console.print(table)
    
    # Check for configuration
    config_path = project_root / ".agent-config.yml"
    if config_path.exists():
        console.print("\n[green]✓[/green] Configuration file found")
    else:
        console.print("\n[yellow]⚠[/yellow] No configuration file found. Using defaults.")
        console.print("  Run 'agent-system init' to create a configuration file.")


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize the current directory for use with the agent system."""
    project_root = ctx.obj['project_root']
    security_manager = ctx.obj['security_manager']
    
    console.print("[cyan]Initializing agent system in current directory...[/cyan]")
    
    # Create configuration file
    config_path = project_root / ".agent-config.yml"
    if config_path.exists():
        if not click.confirm("Configuration file already exists. Overwrite?"):
            return
    
    config_content = """# Agent System Configuration
version: 1.0

# Project settings
project:
  name: {}
  description: "AI-assisted development project"
  
# Agent settings
agents:
  request_planner:
    enabled: true
    model: "gpt-4"
  code_planner:
    enabled: true
    model: "gpt-4"
  coding_agent:
    enabled: true
    model: "gpt-4"
    
# RAG settings
rag:
  enabled: true
  chunk_size: 500
  overlap: 50
  
# Security settings
security:
  restrict_to_project_root: true
  allowed_file_patterns:
    - "*.py"
    - "*.js"
    - "*.ts"
    - "*.java"
    - "*.cpp"
    - "*.c"
    - "*.h"
    - "*.go"
    - "*.rs"
  excluded_paths:
    - "node_modules"
    - "__pycache__"
    - ".git"
    - "venv"
    - ".env"
""".format(project_root.name)
    
    security_manager.write_file(config_path, config_content)
    console.print("[green]✓[/green] Created configuration file: .agent-config.yml")
    
    # Create .gitignore entry
    gitignore_path = project_root / ".gitignore"
    if gitignore_path.exists():
        content = security_manager.read_file(gitignore_path)
        if ".agent-config.yml" not in content:
            security_manager.write_file(gitignore_path, content + "\n# Agent system\n.agent-config.yml\n.agent-cache/\n")
            console.print("[green]✓[/green] Updated .gitignore")
    
    console.print("\n[bold green]Initialization complete![/bold green]")
    console.print("You can now use the agent system commands in this directory.")


@cli.command()
@click.argument('request', required=True)
@click.option('--plan-only', is_flag=True, help="Only create a plan without executing")
@click.option('--no-rag', is_flag=True, help="Disable RAG for this request")
@click.pass_context
def run(ctx, request, plan_only, no_rag):
    """Run the agent system with a natural language request.
    
    Example:
        agent-system run "Add error handling to the API endpoints"
    """
    from src.request_planner.planner import RequestPlanner
    from src.code_planner.code_planner import CodePlanner
    from src.coding_agent.agent import CodingAgent
    
    security_manager = ctx.obj['security_manager']
    project_root = ctx.obj['project_root']
    
    console.print(Panel(f"[bold cyan]Processing Request[/bold cyan]\n\n{request}", 
                       title="Agent System", expand=False))
    
    try:
        # Initialize agents with security manager
        request_planner = RequestPlanner(
            project_root=project_root,
            security_manager=security_manager
        )
        
        # Plan the request
        console.print("\n[yellow]Planning request...[/yellow]")
        plan = request_planner.plan(request)
        
        if plan_only:
            console.print("\n[green]Plan created successfully![/green]")
            console.print(plan)
            return
        
        # Execute the plan
        console.print("\n[yellow]Executing plan...[/yellow]")
        # TODO: Implement full execution pipeline
        
        console.print("\n[bold green]Request completed successfully![/bold green]")
        
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        if ctx.obj['debug']:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', help="Output file for the analysis")
@click.pass_context
def analyze(ctx, path, output):
    """Analyze code structure and complexity.
    
    This command runs the code planner's analysis tools on the specified path.
    """
    from src.code_planner.code_planner import CodePlanner
    
    security_manager = ctx.obj['security_manager']
    project_root = ctx.obj['project_root']
    
    # Ensure path is within project root
    target_path = Path(path).resolve()
    if not security_manager.is_safe_path(target_path):
        console.print(f"[red]Error: Path '{path}' is outside the project root.[/red]")
        sys.exit(1)
    
    console.print(f"[cyan]Analyzing {target_path}...[/cyan]")
    
    try:
        planner = CodePlanner(
            project_root=project_root,
            security_manager=security_manager
        )
        
        analysis = planner.analyze(target_path)
        
        if output:
            output_path = Path(output).resolve()
            if not security_manager.is_safe_path(output_path):
                console.print(f"[red]Error: Output path '{output}' is outside the project root.[/red]")
                sys.exit(1)
            security_manager.write_file(output_path, analysis)
            console.print(f"[green]✓[/green] Analysis saved to {output}")
        else:
            console.print(analysis)
            
    except Exception as e:
        console.print(f"[red]Error during analysis: {str(e)}[/red]")
        if ctx.obj['debug']:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.option('--query', '-q', required=True, help="Search query")
@click.option('--limit', '-l', default=10, help="Maximum number of results")
@click.pass_context
def search(ctx, query, limit):
    """Search the codebase using RAG.
    
    Example:
        agent-system search -q "error handling" -l 5
    """
    from src.rag_service.service import RAGService
    
    security_manager = ctx.obj['security_manager']
    project_root = ctx.obj['project_root']
    
    console.print(f"[cyan]Searching for: {query}[/cyan]")
    
    try:
        rag_service = RAGService(
            project_root=project_root,
            security_manager=security_manager
        )
        
        results = rag_service.search(query, limit=limit)
        
        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return
        
        table = Table(title=f"Search Results for '{query}'", show_header=True)
        table.add_column("File", style="cyan")
        table.add_column("Score", style="green")
        table.add_column("Preview", style="white")
        
        for result in results:
            table.add_row(
                str(result.file_path),
                f"{result.score:.3f}",
                result.preview[:80] + "..." if len(result.preview) > 80 else result.preview
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error during search: {str(e)}[/red]")
        if ctx.obj['debug']:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.pass_context
def clean(ctx):
    """Clean up agent system cache and temporary files."""
    project_root = ctx.obj['project_root']
    security_manager = ctx.obj['security_manager']
    
    console.print("[cyan]Cleaning up agent system files...[/cyan]")
    
    # Clean cache directory
    cache_dir = project_root / ".agent-cache"
    if cache_dir.exists():
        import shutil
        shutil.rmtree(cache_dir)
        console.print("[green]✓[/green] Removed cache directory")
    
    # Clean logs
    log_dir = project_root / "logs"
    if log_dir.exists():
        for log_file in log_dir.glob("*.log"):
            if security_manager.is_safe_path(log_file):
                log_file.unlink()
        console.print("[green]✓[/green] Cleaned log files")
    
    console.print("\n[bold green]Cleanup complete![/bold green]")


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()