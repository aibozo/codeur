#!/usr/bin/env python3
"""
Demo the terminal UI for monitoring agents.
"""

import asyncio
import time
from datetime import datetime
from collections import deque
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn


def create_agent_status_table():
    """Create a table showing agent status."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Agent", style="cyan", width=20)
    table.add_column("Status", width=10)
    table.add_column("Messages", justify="right", width=10)
    table.add_column("Current Task", width=40)
    
    # Simulated agent statuses
    table.add_row(
        "Request Planner",
        "[green]Running[/green]",
        "142",
        "Processing: Add error handling..."
    )
    table.add_row(
        "Code Planner",
        "[green]Running[/green]",
        "89",
        "Creating tasks for plan-fac9769a"
    )
    table.add_row(
        "Coding Agent 1",
        "[yellow]Waiting[/yellow]",
        "34",
        "Idle"
    )
    table.add_row(
        "Coding Agent 2",
        "[green]Running[/green]",
        "67",
        "Generating patch for api_client.py"
    )
    
    return Panel(table, title="Agent Status", border_style="green")


def create_message_flow_panel(messages):
    """Create a panel showing message flow."""
    table = Table(show_header=False, box=None)
    
    flow_text = """[cyan]Change Requests[/cyan] → [yellow]Plans[/yellow] → [green]Task Bundles[/green] → [blue]Tasks[/blue] → [magenta]Commits[/magenta]
    ↓                ↓              ↓                  ↓            ↓
    3                8              8                  24           19
    
Recent Activity:
"""
    
    table.add_column()
    table.add_row(flow_text)
    
    # Add recent messages
    for msg in list(messages)[-5:]:
        table.add_row(f"  {msg}")
    
    return Panel(table, title="Message Flow", border_style="blue")


def create_performance_panel():
    """Create performance metrics panel."""
    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    
    table.add_row("Messages/sec", "12.4")
    table.add_row("Avg Processing", "342ms")
    table.add_row("Success Rate", "94.2%")
    table.add_row("", "")
    table.add_row("Total Commits", "19")
    table.add_row("Lines Added", "+2,847")
    table.add_row("Lines Removed", "-982")
    table.add_row("Files Changed", "42")
    
    return Panel(table, title="Performance", border_style="yellow")


async def demo_terminal_ui():
    """Demo the terminal UI."""
    console = Console()
    
    # Simulated message stream
    messages = deque(maxlen=10)
    messages.extend([
        f"{datetime.now().strftime('%H:%M:%S')} [cyan]REQUEST[/cyan] req-e71b2546: Add error handling",
        f"{datetime.now().strftime('%H:%M:%S')} [yellow]PLAN[/yellow] plan-fac9769a: 3 steps created",
        f"{datetime.now().strftime('%H:%M:%S')} [green]BUNDLE[/green] bundle-08e3a15b: 3 tasks",
        f"{datetime.now().strftime('%H:%M:%S')} [blue]TASK[/blue] task-512726fb: Processing",
        f"{datetime.now().strftime('%H:%M:%S')} [magenta]COMMIT[/magenta] abc123: Error handling added"
    ])
    
    # Create layout
    layout = Layout()
    
    layout.split(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    
    layout["body"].split_column(
        Layout(name="agents", size=10),
        Layout(name="flow", size=12),
        Layout(name="stats", size=10)
    )
    
    # Header
    header = Panel(
        "[bold]Agent System Monitor[/bold] | Status: [green]Running[/green] | Uptime: 00:15:32",
        style="bold blue"
    )
    
    # Footer with progress
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    )
    
    task1 = progress.add_task("[cyan]Processing requests...", total=100)
    task2 = progress.add_task("[yellow]Generating code...", total=100)
    
    footer = Panel(progress, style="dim")
    
    # Run the live display
    with Live(layout, refresh_per_second=4, console=console) as live:
        for i in range(30):  # Run for 30 iterations
            # Update layout
            layout["header"].update(header)
            layout["agents"].update(create_agent_status_table())
            layout["flow"].update(create_message_flow_panel(messages))
            layout["stats"].update(create_performance_panel())
            layout["footer"].update(footer)
            
            # Simulate new messages
            if i % 3 == 0:
                msg_types = ["REQUEST", "PLAN", "BUNDLE", "TASK", "COMMIT", "ERROR"]
                msg_type = msg_types[i % len(msg_types)]
                color = ["cyan", "yellow", "green", "blue", "magenta", "red"][i % 6]
                messages.append(
                    f"{datetime.now().strftime('%H:%M:%S')} [{color}]{msg_type}[/{color}] "
                    f"id-{i:04d}: Sample message {i}"
                )
            
            # Update progress
            progress.update(task1, advance=3)
            progress.update(task2, advance=2)
            
            # Reset progress if complete
            if task1.completed:
                progress.reset(task1)
            if task2.completed:
                progress.reset(task2)
            
            await asyncio.sleep(0.5)
    
    console.print("\n[green]Demo complete![/green]")
    console.print("This is what the agent monitoring looks like in real-time.")


if __name__ == "__main__":
    print("\n=== Terminal UI Demo ===\n")
    print("Showing what the agent monitoring dashboard looks like...")
    print("(This is a simulation - real agents would show live data)\n")
    
    asyncio.run(demo_terminal_ui())