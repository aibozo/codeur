#!/usr/bin/env python3
"""
Show a static version of the terminal UI.
"""

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from datetime import datetime


def main():
    console = Console()
    
    # Create layout
    layout = Layout()
    
    layout.split(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    
    layout["body"].split_column(
        Layout(name="overview", size=12),
        Layout(name="details", size=20)
    )
    
    layout["details"].split_row(
        Layout(name="agents", ratio=1),
        Layout(name="logs", ratio=1)
    )
    
    # Header
    header = Panel(
        "[bold blue]Multi-Agent System Monitor[/bold blue] | "
        f"Time: {datetime.now().strftime('%H:%M:%S')} | "
        "Status: [green]All Systems Operational[/green]",
        style="bold on black"
    )
    layout["header"].update(header)
    
    # Message flow overview
    flow_table = Table(show_header=False, box=None)
    flow_table.add_column()
    
    flow_diagram = """
[bold cyan]Change Request[/bold cyan] → [bold yellow]Plan[/bold yellow] → [bold green]Task Bundle[/bold green] → [bold blue]Coding Tasks[/bold blue] → [bold magenta]Commits[/bold magenta]

Example Flow:
1. [cyan]req-e71b2546[/cyan]: "Add error handling to API client"
   ↓
2. [yellow]plan-fac9769a[/yellow]: 3 steps (add try-except, retry logic, tests)
   ↓
3. [green]bundle-08e3a15b[/green]: 3 parallel tasks generated
   ↓
4. [blue]task-512726fb[/blue]: "Add try-except blocks to api_client.py"
   [blue]task-1fcecf2f[/blue]: "Add retry logic with exponential backoff"
   [blue]task-434146a9[/blue]: "Update tests to cover error scenarios"
   ↓
5. [magenta]commit-abc123[/magenta]: "feat: add error handling to API client"
   [magenta]commit-def456[/magenta]: "feat: add retry logic with backoff"
   [magenta]commit-789ghi[/magenta]: "test: add error scenario tests"
"""
    
    flow_table.add_row(flow_diagram)
    layout["overview"].update(Panel(flow_table, title="System Message Flow", border_style="cyan"))
    
    # Agent status
    agent_table = Table(show_header=True, header_style="bold magenta")
    agent_table.add_column("Agent", style="cyan")
    agent_table.add_column("Status")
    agent_table.add_column("Msgs/Min", justify="right")
    
    agent_table.add_row("Request Planner", "[green]●[/green] Active", "12")
    agent_table.add_row("Code Planner", "[green]●[/green] Active", "8")
    agent_table.add_row("Coding Agent 1", "[green]●[/green] Active", "4")
    agent_table.add_row("Coding Agent 2", "[yellow]●[/yellow] Idle", "0")
    agent_table.add_row("", "", "")
    agent_table.add_row("[bold]Kafka[/bold]", "[green]●[/green] Running", "24")
    agent_table.add_row("[bold]Redis[/bold]", "[green]●[/green] Running", "-")
    
    layout["agents"].update(Panel(agent_table, title="Agent Status", border_style="green"))
    
    # Recent logs
    log_table = Table(show_header=False, box=None, padding=0)
    log_table.add_column("Time", style="dim", width=8)
    log_table.add_column("Level", width=6)
    log_table.add_column("Message")
    
    logs = [
        ("19:08:47", "[green]INFO[/green]", "Request Planner received: req-e71b2546"),
        ("19:08:48", "[green]INFO[/green]", "Created plan with 3 steps"),
        ("19:08:49", "[green]INFO[/green]", "Code Planner analyzing codebase"),
        ("19:08:50", "[yellow]WARN[/yellow]", "No RAG embeddings available"),
        ("19:08:51", "[green]INFO[/green]", "Generated 3 coding tasks"),
        ("19:08:52", "[green]INFO[/green]", "Coding Agent 1 processing task"),
        ("19:08:53", "[green]INFO[/green]", "Patch generated successfully"),
        ("19:08:54", "[green]INFO[/green]", "Validation passed"),
        ("19:08:55", "[green]INFO[/green]", "Commit created: abc123"),
    ]
    
    for time, level, msg in logs:
        log_table.add_row(time, level, msg)
    
    layout["logs"].update(Panel(log_table, title="Recent Activity", border_style="blue"))
    
    # Footer
    footer = Panel(
        "Commands: [bold]q[/bold]uit | [bold]r[/bold]efresh | [bold]f[/bold]ilter | "
        "[bold]↑↓[/bold] scroll | [bold]Enter[/bold] details",
        style="dim"
    )
    layout["footer"].update(footer)
    
    # Display
    console.print(layout)
    
    # Show sample code change
    console.print("\n[bold]Sample Code Change Generated:[/bold]\n")
    
    diff = '''--- a/src/api_client.py
+++ b/src/api_client.py
@@ -1,5 +1,6 @@
 """
 Simple API client that needs error handling.
 """
 
 import requests
+from time import sleep
 
 
 class APIClient:
@@ -11,8 +12,16 @@ class APIClient:
     
     def get_user(self, user_id):
         """Get user by ID."""
-        response = requests.get(f"{self.base_url}/users/{user_id}")
-        return response.json()
+        for attempt in range(3):
+            try:
+                response = requests.get(
+                    f"{self.base_url}/users/{user_id}",
+                    timeout=10
+                )
+                response.raise_for_status()
+                return response.json()
+            except requests.exceptions.RequestException as e:
+                if attempt == 2:
+                    raise
+                sleep(2 ** attempt)  # Exponential backoff'''
    
    syntax = Syntax(diff, "diff", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="Generated Patch", border_style="magenta"))
    
    console.print("\n[dim]This is a static demonstration of the agent monitoring system.[/dim]")


if __name__ == "__main__":
    main()