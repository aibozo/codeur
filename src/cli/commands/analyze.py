"""Analyze command for code structure and complexity analysis."""

import sys
from pathlib import Path
import click
from rich.console import Console

console = Console()


@click.command()
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
    dry_run = ctx.obj.get('dry_run', False)
    
    # Ensure path is within project root
    target_path = Path(path).resolve()
    if not security_manager.is_safe_path(target_path):
        console.print(f"[red]Error: Path '{path}' is outside the project root.[/red]")
        sys.exit(1)
    
    console.print(f"[cyan]Analyzing {target_path}...[/cyan]")
    
    if dry_run:
        console.print("[yellow]DRY RUN MODE: Showing what would be analyzed[/yellow]")
        console.print(f"Would analyze: {target_path}")
        if output:
            console.print(f"Would save results to: {output}")
        return
    
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