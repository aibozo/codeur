"""
Agent configuration management commands.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from src.core.agent_config import AgentConfigManager, AgentType
from src.core.model_cards import MODEL_CARDS

console = Console()


@click.group()
def config():
    """Agent configuration management commands."""
    pass


@config.command()
def show():
    """Display current agent configurations."""
    configs = AgentConfigManager.get_all_configs()
    
    table = Table(title="Agent Configurations", show_header=True, header_style="bold magenta")
    table.add_column("Agent Type", style="cyan", width=20)
    table.add_column("Model", style="green", width=25)
    table.add_column("Temperature", justify="right", style="yellow")
    table.add_column("Max Tokens", justify="right", style="blue")
    table.add_column("Capabilities", style="dim")
    
    for agent_type, config in configs.items():
        model_name = config.get_model()
        model_card = MODEL_CARDS.get(model_name)
        display_model = model_card.display_name if model_card else model_name
        
        capabilities = ", ".join(config.capabilities[:3])
        if len(config.capabilities) > 3:
            capabilities += "..."
        
        table.add_row(
            agent_type.replace("_", " ").title(),
            display_model,
            f"{config.temperature:.1f}",
            str(config.max_tokens) if config.max_tokens else "default",
            capabilities
        )
    
    console.print(table)
    
    # Show note about environment overrides
    console.print("\n[dim]Note: Environment variables can override these defaults.[/dim]")
    console.print("[dim]Set AGENT_TYPE_MODEL in your .env file to customize.[/dim]")


@config.command()
@click.argument('agent_type')
@click.argument('model')
def set_model(agent_type, model):
    """Set the default model for an agent type."""
    try:
        # Validate agent type
        agent_enum = AgentType(agent_type.lower())
        
        # Validate model exists
        if model not in MODEL_CARDS:
            console.print(f"[red]Error: Unknown model '{model}'[/red]")
            console.print("Use 'agent cost models' to see available models.")
            return
        
        # Update configuration
        AgentConfigManager.update_default_model(agent_type, model)
        
        model_card = MODEL_CARDS[model]
        console.print(f"[green]✓ Set {agent_type} to use {model_card.display_name}[/green]")
        console.print(f"[dim]Note: This change is temporary. Set {agent_type.upper()}_MODEL in .env to persist.[/dim]")
        
    except ValueError:
        console.print(f"[red]Error: Unknown agent type '{agent_type}'[/red]")
        console.print("Valid types: architect, request_planner, coding, analyzer, code_planner, test, general")


@config.command()
@click.argument('model')
def set_all_models(model):
    """Set all agents to use the same model."""
    # Validate model exists
    if model not in MODEL_CARDS:
        console.print(f"[red]Error: Unknown model '{model}'[/red]")
        console.print("Use 'agent cost models' to see available models.")
        return
    
    # Update all configurations
    AgentConfigManager.update_all_models(model)
    
    model_card = MODEL_CARDS[model]
    console.print(f"[green]✓ Set all agents to use {model_card.display_name}[/green]")
    console.print(f"[dim]Note: This change is temporary. Update .env file to persist.[/dim]")


@config.command()
def reset():
    """Reset all agents to use gemini-2.5-flash."""
    AgentConfigManager.update_all_models("gemini-2.5-flash")
    console.print("[green]✓ Reset all agents to use Gemini 2.5 Flash[/green]")


def register_commands(cli):
    """Register config commands with the main CLI."""
    cli.add_command(config)