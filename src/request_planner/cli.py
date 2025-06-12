"""
Request Planner CLI - Main interface for the agent system.

This module provides a Claude Code/Codex style interface for interacting
with the agent system. It handles user requests, plans implementations,
and orchestrates task execution.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from typing import Optional
import json
from pathlib import Path
import logging
import os
from dotenv import load_dotenv

from .planner import RequestPlanner
from .models import ChangeRequest, Plan
from .session import InteractiveSession
from .executor import PlanExecutor
from ..core.logging import setup_logging

# Load environment variables from .env file
load_dotenv()

console = Console()

# Set up logging
setup_logging(logging.INFO)


@click.group()
@click.pass_context
def cli(ctx):
    """Agent - A self-healing code generation system."""
    ctx.ensure_object(dict)
    ctx.obj['planner'] = RequestPlanner()


@cli.command()
@click.argument('url', required=False)
@click.option('--branch', '-b', default='main', help='Branch to checkout')
@click.pass_context
def repo(ctx, url, branch):
    """Load a Git repository (clone from URL or use current directory)."""
    planner = ctx.obj['planner']
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        if url:
            task = progress.add_task(f"Cloning repository from {url}...", total=None)
        else:
            task = progress.add_task("Loading current directory...", total=None)
        
        success = planner.load_repository(url, branch)
        progress.remove_task(task)
    
    if success:
        # Show repository info
        info = planner.get_repository_info()
        
        console.print(Panel(
            f"[green]✓[/green] Repository loaded successfully\n\n"
            f"Path: {info['path']}\n"
            f"Branch: {info.get('current_branch', 'N/A')}\n"
            f"Files: {info.get('files_count', 0)} total, {info.get('python_files', 0)} Python\n"
            f"Remote: {info.get('remote_url', 'None')}",
            title="Repository Information",
            border_style="green"
        ))
        
        if info.get('last_commit'):
            commit = info['last_commit']
            console.print(f"\nLast commit: [{commit['hash']}] {commit['message']}")
    else:
        console.print("[red]Failed to load repository[/red]")


@cli.command()
@click.argument('description', nargs=-1, required=True)
@click.option('--repo', '-r', default='.', help='Repository path')
@click.option('--branch', '-b', default='main', help='Target branch')
@click.option('--dry-run', is_flag=True, help='Show plan without executing')
@click.pass_context
def request(ctx, description, repo, branch, dry_run):
    """Submit a code change request."""
    description_text = ' '.join(description)
    
    console.print(f"\n[bold blue]Processing request:[/bold blue] {description_text}")
    
    # Create change request
    change_request = ChangeRequest(
        description=description_text,
        repo=repo,
        branch=branch
    )
    
    # Show progress while planning
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Understanding request...", total=None)
        
        # Get the planner instance
        planner = ctx.obj['planner']
        
        # Generate plan
        progress.update(task, description="Analyzing codebase...")
        plan = planner.create_plan(change_request)
        
        progress.update(task, description="Creating implementation plan...")
    
    # Display the plan
    _display_plan(plan)
    
    if not dry_run:
        if click.confirm("\nProceed with this plan?"):
            console.print("\n[bold green]Executing plan...[/bold green]\n")
            
            # Create executor
            executor = PlanExecutor(planner)
            
            # Execute with progress tracking
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"Executing {len(plan.steps)} steps...", 
                    total=len(plan.steps)
                )
                
                # Execute plan
                summary = executor.execute_plan(plan)
                progress.update(task, completed=len(plan.steps))
            
            # Show execution summary
            _display_execution_summary(summary)
        else:
            console.print("[yellow]Plan cancelled[/yellow]")


@cli.command()
@click.argument('query', nargs=-1, required=True)
@click.option('--limit', '-l', default=10, help='Maximum results to show')
@click.pass_context
def search(ctx, query, limit):
    """Search the codebase for information."""
    query_text = ' '.join(query)
    
    console.print(f"\n[bold blue]Searching for:[/bold blue] {query_text}")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Searching codebase...", total=None)
        
        planner = ctx.obj['planner']
        results = planner.search_codebase(query_text, limit=limit)
    
    if not results:
        console.print("[yellow]No results found[/yellow]")
        return
    
    console.print(f"\n[bold]Found {len(results)} results:[/bold]\n")
    
    for i, result in enumerate(results, 1):
        console.print(f"[bold cyan]{i}. {result['file']}:{result['line']}[/bold cyan]")
        if result.get('content'):
            syntax = Syntax(
                result['content'],
                "python",  # TODO: Detect language
                theme="monokai",
                line_numbers=True,
                start_line=result.get('line', 1)
            )
            console.print(syntax)
        console.print()


@cli.command()
@click.argument('question', nargs=-1, required=True)
@click.pass_context
def explain(ctx, question):
    """Ask questions about the codebase using AI."""
    question_text = ' '.join(question)
    
    console.print(f"\n[bold blue]Question:[/bold blue] {question_text}")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing code...", total=None)
        
        planner = ctx.obj['planner']
        analysis = planner.analyze_code(question_text)
    
    console.print("\n[bold]Answer:[/bold]\n")
    console.print(analysis)


@cli.command()
@click.pass_context
def status(ctx):
    """Show current agent status and active tasks."""
    console.print("\n[bold]Agent Status[/bold]\n")
    
    planner = ctx.obj['planner']
    status_info = planner.get_status()
    
    if not status_info['active_tasks']:
        console.print("[green]No active tasks[/green]")
    else:
        for task in status_info['active_tasks']:
            status_color = {
                'pending': 'yellow',
                'in_progress': 'blue',
                'completed': 'green',
                'failed': 'red'
            }.get(task['status'], 'white')
            
            console.print(
                f"• [{status_color}]{task['status'].upper()}[/{status_color}] "
                f"{task['description']}"
            )
    
    console.print(f"\n[dim]System: {status_info['system_status']}[/dim]")


@cli.command()
@click.option('--repo', '-r', default='.', help='Repository path')
@click.pass_context
def session(ctx, repo):
    """Start an interactive session (Claude Code style)."""
    console.print("[cyan]Starting interactive session...[/cyan]\n")
    
    # Create and start session
    interactive = InteractiveSession(repo)
    interactive.start()


@cli.command()
@click.argument('description', nargs=-1, required=True)
@click.option('--output', '-o', help='Save plan to file')
@click.pass_context
def plan(ctx, description, output):
    """Create an implementation plan without executing."""
    description_text = ' '.join(description)
    
    console.print(f"\n[bold blue]Planning:[/bold blue] {description_text}")
    
    change_request = ChangeRequest(
        description=description_text,
        repo='.',
        branch='main'
    )
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Creating plan...", total=None)
        
        planner = ctx.obj['planner']
        plan = planner.create_plan(change_request)
    
    _display_plan(plan)
    
    if output:
        plan_dict = plan.to_dict()
        Path(output).write_text(json.dumps(plan_dict, indent=2))
        console.print(f"\n[green]Plan saved to {output}[/green]")


def _display_plan(plan: Plan):
    """Display a plan in a formatted way."""
    console.print("\n[bold]Implementation Plan[/bold]\n")
    
    # Show summary
    summary_text = f"""
[bold]ID:[/bold] {plan.id}
[bold]Complexity:[/bold] {plan.complexity_label}
[bold]Estimated tokens:[/bold] {plan.estimated_tokens}
[bold]Files affected:[/bold] {len(plan.affected_paths)}
    """
    
    console.print(Panel(summary_text.strip(), title="Summary", expand=False))
    
    # Show steps
    console.print("\n[bold]Steps:[/bold]\n")
    for i, step in enumerate(plan.steps, 1):
        step_text = f"[bold cyan]{i}. {step.goal}[/bold cyan]"
        if step.hints:
            step_text += f"\n   [dim]Hints: {', '.join(step.hints)}[/dim]"
        console.print(step_text)
    
    # Show rationale
    if plan.rationale:
        console.print("\n[bold]Rationale:[/bold]")
        for point in plan.rationale:
            console.print(f"  • {point}")
    
    # Show affected files
    if plan.affected_paths:
        console.print("\n[bold]Affected files:[/bold]")
        for path in plan.affected_paths:
            console.print(f"  • {path}")


def _display_execution_summary(summary: Dict[str, Any]):
    """Display execution summary."""
    status = summary.get('status', 'unknown')
    status_color = {
        'completed': 'green',
        'failed': 'red',
        'partial': 'yellow'
    }.get(status, 'white')
    
    console.print(f"\n[bold {status_color}]Execution {status.upper()}[/bold {status_color}]")
    
    # Stats
    stats_text = f"""
Total steps: {summary.get('total_steps', 0)}
Completed: {summary.get('completed_steps', 0)}
Failed: {summary.get('failed_steps', 0)}
Modified files: {len(summary.get('modified_files', []))}
"""
    console.print(Panel(stats_text.strip(), title="Execution Stats", expand=False))
    
    # Show results
    if summary.get('results'):
        console.print("\n[bold]Step Results:[/bold]\n")
        for result in summary['results']:
            status_icon = {
                'completed': '✓',
                'failed': '✗'
            }.get(result['status'], '•')
            
            status_color = {
                'completed': 'green',
                'failed': 'red'
            }.get(result['status'], 'yellow')
            
            console.print(f"[{status_color}]{status_icon}[/{status_color}] Step {result['step']}: {result['goal']}")
            
            if result.get('output'):
                console.print(f"   [dim]{result['output']}[/dim]")
            if result.get('error'):
                console.print(f"   [red]Error: {result['error']}[/red]")
    
    # Show modified files
    if summary.get('modified_files'):
        console.print("\n[bold]Modified Files:[/bold]")
        for file in summary['modified_files']:
            console.print(f"  • {file}")


def main():
    """Main entry point for the CLI."""
    cli(obj={})


if __name__ == '__main__':
    main()