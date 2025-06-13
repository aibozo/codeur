"""Init command for initializing the agent system in a project."""

import click
from rich.console import Console

console = Console()


@click.command()
@click.pass_context
def init(ctx):
    """Initialize the current directory for use with the agent system."""
    project_root = ctx.obj['project_root']
    security_manager = ctx.obj['security_manager']
    dry_run = ctx.obj.get('dry_run', False)
    
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
    
    if dry_run:
        console.print("[yellow]DRY RUN: Would create configuration file: .agent-config.yml[/yellow]")
    else:
        security_manager.write_file(config_path, config_content)
        console.print("[green]✓[/green] Created configuration file: .agent-config.yml")
    
    # Create .gitignore entry
    gitignore_path = project_root / ".gitignore"
    if gitignore_path.exists():
        content = security_manager.read_file(gitignore_path)
        if ".agent-config.yml" not in content:
            updated_content = content + "\n# Agent system\n.agent-config.yml\n.agent-cache/\n"
            if dry_run:
                console.print("[yellow]DRY RUN: Would update .gitignore[/yellow]")
            else:
                security_manager.write_file(gitignore_path, updated_content)
                console.print("[green]✓[/green] Updated .gitignore")
    
    console.print("\n[bold green]Initialization complete![/bold green]")
    console.print("You can now use the agent system commands in this directory.")