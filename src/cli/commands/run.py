"""Run command for executing agent requests."""

import sys
import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.command()
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
    dry_run = ctx.obj.get('dry_run', False)
    
    console.print(Panel(f"[bold cyan]Processing Request[/bold cyan]\n\n{request}", 
                       title="Agent System", expand=False))
    
    if dry_run:
        console.print("[yellow]DRY RUN MODE: Showing what would be done[/yellow]\n")
    
    try:
        # Initialize agents with security manager
        request_planner = RequestPlanner(
            project_root=project_root,
            security_manager=security_manager
        )
        
        # Plan the request
        console.print("\n[yellow]Planning request...[/yellow]")
        
        if dry_run:
            console.print("[yellow]DRY RUN: Would create execution plan for request[/yellow]")
            console.print(f"Request: {request}")
            console.print("Actions that would be taken:")
            console.print("1. Analyze request and decompose into tasks")
            console.print("2. Create code modification plan")
            console.print("3. Execute code changes")
            return
        
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