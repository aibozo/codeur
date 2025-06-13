"""Clean command for removing cache and temporary files."""

import shutil
import click
from rich.console import Console

console = Console()


@click.command()
@click.pass_context
def clean(ctx):
    """Clean up agent system cache and temporary files."""
    project_root = ctx.obj['project_root']
    security_manager = ctx.obj['security_manager']
    dry_run = ctx.obj.get('dry_run', False)
    
    console.print("[cyan]Cleaning up agent system files...[/cyan]")
    
    if dry_run:
        console.print("[yellow]DRY RUN MODE: Showing what would be cleaned[/yellow]\n")
    
    # Clean cache directory
    cache_dir = project_root / ".agent-cache"
    if cache_dir.exists():
        if dry_run:
            console.print("[yellow]DRY RUN: Would remove cache directory[/yellow]")
        else:
            shutil.rmtree(cache_dir)
            console.print("[green]✓[/green] Removed cache directory")
    
    # Clean logs
    log_dir = project_root / "logs"
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        if log_files:
            if dry_run:
                console.print(f"[yellow]DRY RUN: Would remove {len(log_files)} log files[/yellow]")
            else:
                for log_file in log_files:
                    if security_manager.is_safe_path(log_file):
                        log_file.unlink()
                console.print("[green]✓[/green] Cleaned log files")
    
    console.print("\n[bold green]Cleanup complete![/bold green]")