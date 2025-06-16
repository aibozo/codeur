"""
Cost tracking and reporting commands.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from src.core.model_cards import get_cost_tracker, MODEL_CARDS

console = Console()


@click.group()
def cost():
    """Cost tracking and reporting commands."""
    pass


@cost.command()
def summary():
    """Display cost summary for all agents."""
    tracker = get_cost_tracker()
    summary_data = tracker.get_summary()
    
    # Create main summary panel
    summary_text = Text()
    summary_text.append("Total Cost: ", style="bold")
    summary_text.append(f"${summary_data['total_cost']:.4f}\n", style="bold green")
    summary_text.append("Total Requests: ", style="bold")
    summary_text.append(str(summary_data['usage_count']), style="cyan")
    
    console.print(Panel(summary_text, title="Cost Summary", border_style="green"))
    
    # Cost by agent table
    if summary_data['cost_by_agent']:
        agent_table = Table(title="Cost by Agent", show_header=True, header_style="bold magenta")
        agent_table.add_column("Agent", style="cyan", width=20)
        agent_table.add_column("Cost (USD)", justify="right", style="green")
        agent_table.add_column("Percentage", justify="right", style="yellow")
        
        total = summary_data['total_cost']
        for agent, cost in sorted(summary_data['cost_by_agent'].items(), key=lambda x: x[1], reverse=True):
            percentage = (cost / total * 100) if total > 0 else 0
            agent_table.add_row(
                agent,
                f"${cost:.4f}",
                f"{percentage:.1f}%"
            )
        
        console.print(agent_table)
    
    # Cost by model table
    if summary_data['cost_by_model']:
        model_table = Table(title="Cost by Model", show_header=True, header_style="bold magenta")
        model_table.add_column("Model", style="cyan", width=20)
        model_table.add_column("Cost (USD)", justify="right", style="green")
        model_table.add_column("Input $/1M", justify="right", style="blue")
        model_table.add_column("Output $/1M", justify="right", style="blue")
        
        for model_id, cost in sorted(summary_data['cost_by_model'].items(), key=lambda x: x[1], reverse=True):
            card = MODEL_CARDS.get(model_id)
            if card:
                model_table.add_row(
                    card.display_name,
                    f"${cost:.4f}",
                    f"${card.input_price:.2f}",
                    f"${card.output_price:.2f}"
                )
            else:
                model_table.add_row(
                    model_id,
                    f"${cost:.4f}",
                    "N/A",
                    "N/A"
                )
        
        console.print(model_table)


@cost.command()
def models():
    """Display available models and their pricing."""
    table = Table(title="Available Models", show_header=True, header_style="bold magenta")
    table.add_column("Provider", style="cyan", width=10)
    table.add_column("Model", style="green", width=20)
    table.add_column("Input $/1M", justify="right", style="blue")
    table.add_column("Output $/1M", justify="right", style="blue")
    table.add_column("Context", justify="right", style="yellow")
    table.add_column("Features", style="dim")
    
    # Group by provider
    for provider in ["openai", "google", "anthropic"]:
        provider_cards = [
            (model_id, card) for model_id, card in MODEL_CARDS.items()
            if card.provider.value == provider
        ]
        
        # Sort by input price
        provider_cards.sort(key=lambda x: x[1].input_price)
        
        for model_id, card in provider_cards:
            features = ", ".join(card.features[:3])  # Show first 3 features
            if len(card.features) > 3:
                features += "..."
            
            table.add_row(
                card.provider.value.title(),
                card.display_name,
                f"${card.input_price:.2f}",
                f"${card.output_price:.2f}",
                f"{card.context_window:,}",
                features
            )
    
    console.print(table)


@cost.command()
def reset():
    """Reset cost tracking data."""
    if click.confirm("Are you sure you want to reset all cost tracking data?"):
        tracker = get_cost_tracker()
        tracker.reset()
        console.print("[green]Cost tracking data has been reset.[/green]")


@cost.command()
@click.argument('budget', type=float)
def set_budget(budget):
    """Set a cost budget alert."""
    console.print(f"[yellow]Budget alerts not yet implemented. Would set budget to ${budget:.2f}[/yellow]")


def register_commands(cli):
    """Register cost commands with the main CLI."""
    cli.add_command(cost)