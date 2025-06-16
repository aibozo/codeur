"""
Monitor command for terminal dashboard.

Provides a real-time dashboard view of agent activity.
"""

import asyncio
import click
from typing import Optional
from rich.console import Console
from rich.live import Live
from datetime import datetime

from src.ui.terminal.components import (
    AgentCard, GraphView, LogStream, MetricsBar, 
    PlanView, DashboardLayout
)
from src.ui.terminal.themes import THEME, STATUS_SYMBOLS
from src.ui.shared.state import UIState, AgentStatus
from src.core.logging import get_logger
from src.core.settings import get_settings

logger = get_logger(__name__)


class DashboardController:
    """Controls the terminal dashboard."""
    
    def __init__(self):
        """Initialize dashboard controller."""
        self.console = Console()
        self.ui_state = UIState()
        self.layout = DashboardLayout()
        
        # Components
        self.log_stream = LogStream()
        self.metrics_bar = MetricsBar()
        self.plan_view = PlanView()
        self.graph_view = GraphView(
            agents=["request_planner", "code_planner", "coding_agent"],
            connections=[
                ("request_planner", "code_planner"),
                ("code_planner", "coding_agent"),
                ("request_planner", "rag_service"),
                ("coding_agent", "git_operations")
            ]
        )
        
        # Demo data
        self._setup_demo_data()
        
    def _setup_demo_data(self):
        """Set up demo data for display."""
        # Demo agents
        self.ui_state.update_agent(
            "request_planner",
            status=AgentStatus.ACTIVE,
            model="claude-opus",
            current_task="Analyzing user request..."
        )
        
        self.ui_state.update_agent(
            "code_planner",
            status=AgentStatus.IDLE,
            model="gpt-4",
            current_task=None
        )
        
        self.ui_state.update_agent(
            "coding_agent",
            status=AgentStatus.ACTIVE,
            model="claude-3.5",
            current_task="Writing authentication module..."
        )
        
        # Demo logs
        self.log_stream.add_log("INFO", "Starting authentication implementation", "coding_agent")
        self.log_stream.add_log("DEBUG", "Token usage: 15,234 / 32,000", "request_planner")
        self.log_stream.add_log("INFO", "Writing auth.py", "coding_agent")
        
        # Demo metrics
        self.metrics_bar.update(cpu=45, memory=35, queue=3, tokens=15234)
        
        # Demo plan
        self.plan_view.plan = """## Authentication Plan

1. Install PyJWT library
2. Create authentication middleware
3. Add login/logout endpoints
4. Secure existing API routes
5. Add tests for auth flow

The agent will implement a complete JWT-based authentication system."""
        
    def render(self) -> DashboardLayout:
        """Render the dashboard."""
        # Update header
        self.layout.update_header("🤖 Codeur Monitor - Terminal Dashboard")
        
        # Render agents
        agent_panels = []
        for agent_type, agent_state in self.ui_state.agents.items():
            card = AgentCard(
                agent_type=agent_type,
                status=agent_state.status.value,
                model=agent_state.model,
                task=agent_state.current_task
            )
            agent_panels.append(card.render())
            
        # Update layout sections
        if agent_panels:
            from rich.columns import Columns
            self.layout.layout["agents"].update(Columns(agent_panels))
        
        # Update other sections
        self.layout.layout["job"].update(self.graph_view.render())
        self.layout.layout["metrics"].update(self.metrics_bar.render())
        self.layout.layout["plan"].update(self.plan_view.render())
        self.layout.layout["logs"].update(self.log_stream.render())
        
        return self.layout
        
    async def run_dashboard(self, refresh_rate: float = 1.0):
        """Run the dashboard with live updates."""
        with Live(
            self.render().render(),
            console=self.console,
            refresh_per_second=1/refresh_rate,
            screen=True
        ) as live:
            try:
                while True:
                    # Simulate updates
                    await self._simulate_updates()
                    
                    # Update display
                    live.update(self.render().render())
                    
                    # Wait
                    await asyncio.sleep(refresh_rate)
                    
            except KeyboardInterrupt:
                pass
                
    async def _simulate_updates(self):
        """Simulate real-time updates for demo."""
        # Rotate agent status
        import random
        
        # Random log entries
        if random.random() > 0.7:
            sources = ["request_planner", "code_planner", "coding_agent"]
            levels = ["INFO", "DEBUG", "WARN"]
            messages = [
                "Processing file analysis",
                "Context window usage: 8K/32K",
                "Writing implementation",
                "Running validation checks",
                "Optimizing code structure"
            ]
            
            self.log_stream.add_log(
                random.choice(levels),
                random.choice(messages),
                random.choice(sources)
            )
            
        # Update metrics
        self.metrics_bar.update(
            cpu=random.randint(20, 80),
            memory=random.randint(30, 60),
            queue=random.randint(0, 5),
            tokens=random.randint(10000, 30000)
        )


@click.command()
@click.option(
    '--dashboard',
    is_flag=True,
    help='Run in dashboard mode with live updates'
)
@click.option(
    '--refresh-rate',
    default=1.0,
    type=float,
    help='Dashboard refresh rate in seconds'
)
def monitor(dashboard: bool, refresh_rate: float):
    """
    Monitor agent system activity.
    
    Run with --dashboard for a live terminal dashboard view.
    """
    if dashboard:
        controller = DashboardController()
        
        click.echo("Starting Codeur Monitor Dashboard...")
        click.echo("Press Ctrl+C to exit")
        
        try:
            asyncio.run(controller.run_dashboard(refresh_rate))
        except KeyboardInterrupt:
            click.echo("\nDashboard stopped.")
    else:
        # Simple status display
        console = Console()
        settings = get_settings()
        
        console.print("\n[bold cyan]🤖 Codeur System Status[/bold cyan]\n")
        
        # Show configuration
        console.print("[bold]Configuration:[/bold]")
        console.print(f"  Project Root: {settings.project_root}")
        console.print(f"  Debug Mode: {settings.debug}")
        console.print(f"  Webhook Enabled: {settings.webhook.webhook_enabled}")
        
        if settings.webhook.webhook_enabled:
            console.print(f"  Webhook URL: http://{settings.webhook.webhook_host}:{settings.webhook.webhook_port}")
        
        console.print("\n[bold]Cache Backend:[/bold]")
        console.print(f"  Type: {settings.cache.cache_backend}")
        if settings.cache.cache_backend == "redis":
            console.print(f"  Redis URL: {settings.cache.redis_url}")
            
        console.print("\n[bold]LLM Configuration:[/bold]")
        console.print(f"  Default Model: {settings.llm.default_model}")
        console.print(f"  Temperature: {settings.llm.temperature}")
        console.print(f"  Max Tokens: {settings.llm.max_tokens}")
        
        console.print("\n[dim]Run with --dashboard for live terminal monitoring[/dim]")
        console.print("[dim]Or run 'agent webhook start' for the web dashboard[/dim]")


if __name__ == "__main__":
    monitor()