"""
Code Planner CLI - Command-line interface for testing and running Code Planner.
"""

import click
import logging
import asyncio
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from ..proto_gen import messages_pb2
from .code_planner import CodePlanner
from .messaging_service import run_code_planner_service


console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
def cli(debug):
    """Code Planner Agent CLI."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@cli.command()
@click.option('--repo-path', default='.', help='Repository path')
@click.option('--plan-file', required=True, help='Path to plan file (JSON)')
def process(repo_path, plan_file):
    """Process a plan file and generate tasks."""
    import json
    from google.protobuf import json_format
    
    console.print(f"[bold]Processing plan from:[/bold] {plan_file}")
    
    # Load plan from JSON
    with open(plan_file, 'r') as f:
        plan_dict = json.load(f)
    
    plan = messages_pb2.Plan()
    json_format.ParseDict(plan_dict, plan)
    
    # Create Code Planner
    planner = CodePlanner(repo_path)
    
    # Process plan
    task_bundle = planner.process_plan(plan)
    
    # Display results
    display_task_bundle(task_bundle)
    
    # Optionally save to file
    output_file = Path(plan_file).with_suffix('.tasks.json')
    with open(output_file, 'w') as f:
        json.dump(json_format.MessageToDict(task_bundle), f, indent=2)
    
    console.print(f"\n[green]✓[/green] Saved tasks to: {output_file}")


@cli.command()
@click.option('--repo-path', default='.', help='Repository path')
@click.option('--file', required=True, help='File to analyze')
def analyze(repo_path, file):
    """Analyze a single file's AST."""
    from .ast_analyzer import ASTAnalyzer
    
    console.print(f"[bold]Analyzing file:[/bold] {file}")
    
    analyzer = ASTAnalyzer(repo_path)
    analysis = analyzer.analyze_file(file)
    
    if not analysis:
        console.print("[red]File not found or could not be analyzed[/red]")
        return
    
    # Display analysis
    table = Table(title=f"Analysis of {file}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Language", analysis.language)
    table.add_row("Complexity", str(analysis.complexity))
    table.add_row("Symbols", str(len(analysis.symbols)))
    table.add_row("Imports", str(len(analysis.imports)))
    table.add_row("Dependencies", ", ".join(analysis.dependencies))
    
    console.print(table)
    
    # Show symbols
    if analysis.symbols:
        tree = Tree("Symbols")
        for symbol in analysis.symbols:
            node = tree.add(f"{symbol.kind}: {symbol.name}")
            node.add(f"Lines {symbol.line_start}-{symbol.line_end}")
            node.add(f"Complexity: {symbol.complexity}")
            if symbol.calls:
                calls_node = node.add("Calls")
                for call in symbol.calls:
                    calls_node.add(call)
        
        console.print(tree)


@cli.command()
@click.option('--repo-path', default='.', help='Repository path')
@click.option('--config', help='Messaging configuration file')
def serve(repo_path, config):
    """Run Code Planner as a messaging service."""
    console.print("[bold]Starting Code Planner messaging service...[/bold]")
    
    try:
        asyncio.run(run_code_planner_service(repo_path, config))
    except KeyboardInterrupt:
        console.print("\n[yellow]Service stopped by user[/yellow]")


@cli.command()
def sample_plan():
    """Generate a sample plan for testing."""
    import json
    from google.protobuf import json_format
    
    # Create sample plan
    plan = messages_pb2.Plan()
    plan.id = "sample-plan-001"
    plan.parent_request_id = "request-001"
    
    # Add steps
    step1 = plan.steps.add()
    step1.order = 1
    step1.goal = "Refactor the validate_input function in src/utils/validation.py"
    step1.kind = messages_pb2.STEP_KIND_REFACTOR
    step1.hints.extend([
        "Split into smaller functions",
        "Add type hints",
        "Improve error messages"
    ])
    
    step2 = plan.steps.add()
    step2.order = 2
    step2.goal = "Add unit tests for the refactored validation functions"
    step2.kind = messages_pb2.STEP_KIND_TEST
    step2.hints.extend([
        "Test edge cases",
        "Test error conditions",
        "Achieve 90% coverage"
    ])
    
    # Set other fields
    plan.rationale.extend([
        "Current validation is monolithic and hard to test",
        "Breaking it down will improve maintainability"
    ])
    plan.affected_paths.extend([
        "src/utils/validation.py",
        "tests/test_validation.py"
    ])
    plan.complexity_label = messages_pb2.COMPLEXITY_MODERATE
    
    # Save to file
    output_file = "sample_plan.json"
    with open(output_file, 'w') as f:
        json.dump(json_format.MessageToDict(plan), f, indent=2)
    
    console.print(f"[green]✓[/green] Generated sample plan: {output_file}")


def display_task_bundle(bundle: messages_pb2.TaskBundle):
    """Display a TaskBundle in a nice format."""
    console.print(f"\n[bold]TaskBundle:[/bold] {bundle.id}")
    console.print(f"[bold]Strategy:[/bold] {bundle.execution_strategy}")
    console.print(f"[bold]Tasks:[/bold] {len(bundle.tasks)}")
    
    # Create table for tasks
    table = Table(title="Generated Tasks")
    table.add_column("ID", style="cyan", width=12)
    table.add_column("Goal", style="white")
    table.add_column("Files", style="green")
    table.add_column("Complexity", style="yellow")
    table.add_column("Dependencies", style="magenta")
    
    for task in bundle.tasks:
        table.add_row(
            task.id[:8] + "...",
            task.goal[:50] + ("..." if len(task.goal) > 50 else ""),
            str(len(task.paths)),
            task.complexity_label.name,
            str(len(task.depends_on))
        )
    
    console.print(table)
    
    # Show task details
    for i, task in enumerate(bundle.tasks[:3], 1):  # Show first 3
        console.print(f"\n[bold]Task {i} Details:[/bold]")
        tree = Tree(f"{task.id[:12]}...")
        tree.add(f"Goal: {task.goal}")
        
        if task.paths:
            paths_node = tree.add("Files")
            for path in task.paths[:5]:  # Show first 5
                paths_node.add(path)
            if len(task.paths) > 5:
                paths_node.add(f"... and {len(task.paths) - 5} more")
        
        if task.skeleton_patch:
            patch_node = tree.add("Skeleton Patches")
            for patch in task.skeleton_patch[:2]:  # Show first 2
                lines = patch.split('\n')
                patch_node.add(lines[0] if lines else "Empty patch")
        
        if task.depends_on:
            deps_node = tree.add("Dependencies")
            for dep in task.depends_on:
                deps_node.add(dep)
        
        console.print(tree)


if __name__ == '__main__':
    cli()