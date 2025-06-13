"""Main CLI interface for the Agent System (Facade).

This provides the unified command-line interface for all agent operations.
"""

import sys
from pathlib import Path

import click
from rich.console import Console

from src.core.security import SecurityManager
from src.core.logging import setup_logging

# Import command modules
from .commands import status, init, run, analyze, search, clean

console = Console()
logger = setup_logging(__name__)


@click.group()
@click.version_option(version="0.1.0", prog_name="agent-system")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@click.pass_context
def cli(ctx, debug, dry_run):
    """AI-powered multi-agent code generation framework.
    
    This tool operates on the current directory as the project root.
    """
    # Set up security manager to prevent parent directory access
    security_manager = SecurityManager(project_root=Path.cwd())
    ctx.obj = {
        'security_manager': security_manager,
        'debug': debug,
        'dry_run': dry_run,
        'project_root': Path.cwd()
    }
    
    if debug:
        logger.setLevel('DEBUG')
        console.print("[yellow]Debug mode enabled[/yellow]")
    
    if dry_run:
        console.print("[yellow]Dry-run mode enabled - no changes will be made[/yellow]")
    
    # Verify we're in a valid project directory
    if not security_manager.is_valid_project_root():
        console.print("[red]Error: Current directory does not appear to be a valid project.[/red]")
        console.print("Please run this command from your project root directory.")
        sys.exit(1)


# Register commands
cli.add_command(status.status)
cli.add_command(init.init)
cli.add_command(run.run)
cli.add_command(analyze.analyze)
cli.add_command(search.search)
cli.add_command(clean.clean)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()