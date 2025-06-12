#!/usr/bin/env python3
"""
Orchestrator for running and monitoring all agents.
"""

import sys
import os
import asyncio
import subprocess
import signal
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import click
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
import psutil

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.messaging.factory import MessageQueueFactory
from src.messaging.config import MessagingConfig
from src.messaging.base import QueueConfig
from src.proto_gen import messages_pb2


class AgentProcess:
    """Represents a running agent process."""
    
    def __init__(self, name: str, command: List[str]):
        self.name = name
        self.command = command
        self.process = None
        self.status = "stopped"
        self.start_time = None
        self.cpu_percent = 0
        self.memory_mb = 0
        self.messages_processed = 0
    
    def start(self):
        """Start the agent process."""
        self.process = subprocess.Popen(
            self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        self.status = "running"
        self.start_time = datetime.now()
    
    def stop(self):
        """Stop the agent process."""
        if self.process:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process.wait()
            self.process = None
        self.status = "stopped"
    
    def is_running(self) -> bool:
        """Check if process is running."""
        if self.process:
            return self.process.poll() is None
        return False
    
    def update_stats(self):
        """Update process statistics."""
        if self.process and self.is_running():
            try:
                p = psutil.Process(self.process.pid)
                self.cpu_percent = p.cpu_percent()
                self.memory_mb = p.memory_info().rss / 1024 / 1024
            except:
                pass


class Orchestrator:
    """Orchestrates all agents and services."""
    
    def __init__(self, repo_path: str = ".", config_path: Optional[str] = None):
        self.console = Console()
        self.repo_path = Path(repo_path).absolute()
        self.config_path = config_path
        self.running = False
        
        # Agent processes
        self.agents = self._create_agents()
        
        # Service processes
        self.services = self._create_services()
        
        # Message queue for monitoring
        self.message_queue = None
        self.stats = {
            "total_messages": 0,
            "messages_per_minute": 0,
            "errors": 0,
            "uptime": 0
        }
        
        self.start_time = datetime.now()
    
    def _create_agents(self) -> Dict[str, AgentProcess]:
        """Create agent process definitions."""
        base_cmd = [sys.executable]
        
        agents = {
            "request_planner": AgentProcess(
                "Request Planner",
                base_cmd + ["request_planner_runner.py", "--repo", str(self.repo_path)]
            ),
            "code_planner": AgentProcess(
                "Code Planner",
                base_cmd + ["code_planner_runner.py", "--repo", str(self.repo_path)]
            ),
            "coding_agent_1": AgentProcess(
                "Coding Agent 1",
                base_cmd + ["coding_agent_runner.py", "--repo", str(self.repo_path)]
            ),
            "coding_agent_2": AgentProcess(
                "Coding Agent 2",
                base_cmd + ["coding_agent_runner.py", "--repo", str(self.repo_path)]
            )
        }
        
        # Add config if provided
        if self.config_path:
            for agent in agents.values():
                agent.command.extend(["--config", self.config_path])
        
        return agents
    
    def _create_services(self) -> Dict[str, AgentProcess]:
        """Create service process definitions."""
        return {
            "kafka": AgentProcess(
                "Kafka",
                ["docker-compose", "-f", "docker-compose.yml", "up", "kafka"]
            ),
            "redis": AgentProcess(
                "Redis",
                ["docker-compose", "-f", "docker-compose.yml", "up", "redis"]
            )
        }
    
    def create_layout(self) -> Layout:
        """Create the terminal UI layout."""
        layout = Layout()
        
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        layout["body"].split_row(
            Layout(name="agents", ratio=2),
            Layout(name="stats", ratio=1)
        )
        
        return layout
    
    def render_header(self) -> Panel:
        """Render the header panel."""
        runtime = datetime.now() - self.start_time
        status = "[green]Running[/green]" if self.running else "[yellow]Stopped[/yellow]"
        
        header_text = f"[bold]Agent Orchestrator[/bold] | Status: {status} | Runtime: {runtime}"
        return Panel(header_text, style="bold blue")
    
    def render_agents(self) -> Panel:
        """Render agents status panel."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Agent", style="cyan", width=20)
        table.add_column("Status", width=10)
        table.add_column("CPU %", justify="right", width=8)
        table.add_column("Memory", justify="right", width=10)
        table.add_column("Messages", justify="right", width=10)
        
        # Services
        for name, service in self.services.items():
            status_color = "green" if service.is_running() else "red"
            table.add_row(
                service.name,
                f"[{status_color}]{service.status}[/{status_color}]",
                f"{service.cpu_percent:.1f}",
                f"{service.memory_mb:.1f} MB",
                "-"
            )
        
        # Separator
        table.add_row("", "", "", "", "")
        
        # Agents
        for name, agent in self.agents.items():
            status_color = "green" if agent.is_running() else "red"
            table.add_row(
                agent.name,
                f"[{status_color}]{agent.status}[/{status_color}]",
                f"{agent.cpu_percent:.1f}",
                f"{agent.memory_mb:.1f} MB",
                str(agent.messages_processed)
            )
        
        return Panel(table, title="Agents & Services", border_style="green")
    
    def render_stats(self) -> Panel:
        """Render statistics panel."""
        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        
        table.add_row("Total Messages", str(self.stats["total_messages"]))
        table.add_row("Messages/min", f"{self.stats['messages_per_minute']:.1f}")
        table.add_row("Total Errors", str(self.stats["errors"]))
        table.add_row("", "")
        
        # Queue stats
        table.add_row("[bold]Message Queues[/bold]", "")
        table.add_row("Change Requests", "0")
        table.add_row("Plans", "0")
        table.add_row("Task Bundles", "0")
        table.add_row("Commit Results", "0")
        
        return Panel(table, title="System Statistics", border_style="blue")
    
    def render_footer(self) -> Panel:
        """Render the footer panel."""
        footer_text = (
            "Commands: [bold]s[/bold]tart all | [bold]t[/bold]op all | "
            "[bold]r[/bold]estart agent | [bold]q[/bold]uit | "
            "[bold]m[/bold]onitor messages"
        )
        return Panel(footer_text, style="dim")
    
    def update_display(self, layout: Layout):
        """Update the display with current information."""
        # Update stats for all processes
        for agent in self.agents.values():
            agent.update_stats()
        for service in self.services.values():
            service.update_stats()
        
        layout["header"].update(self.render_header())
        layout["agents"].update(self.render_agents())
        layout["stats"].update(self.render_stats())
        layout["footer"].update(self.render_footer())
    
    async def start_all(self):
        """Start all services and agents."""
        self.console.print("[bold]Starting all services and agents...[/bold]")
        
        # Start services first
        for name, service in self.services.items():
            self.console.print(f"Starting {service.name}...")
            service.start()
            await asyncio.sleep(2)  # Give services time to start
        
        # Wait for services to be ready
        await asyncio.sleep(5)
        
        # Start agents
        for name, agent in self.agents.items():
            self.console.print(f"Starting {agent.name}...")
            agent.start()
            await asyncio.sleep(1)
        
        self.running = True
        self.console.print("[green]All services started![/green]")
    
    async def stop_all(self):
        """Stop all agents and services."""
        self.console.print("[bold]Stopping all agents and services...[/bold]")
        
        # Stop agents first
        for agent in self.agents.values():
            if agent.is_running():
                self.console.print(f"Stopping {agent.name}...")
                agent.stop()
        
        # Stop services
        for service in self.services.values():
            if service.is_running():
                self.console.print(f"Stopping {service.name}...")
                service.stop()
        
        self.running = False
        self.console.print("[green]All services stopped![/green]")
    
    async def run(self):
        """Run the orchestrator UI."""
        # Set up signal handlers
        signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(self.stop_all()))
        
        # Create layout
        layout = self.create_layout()
        
        # Start monitoring in background
        monitor_task = asyncio.create_task(self._monitor_queues())
        
        # Run the UI
        with Live(layout, refresh_per_second=2) as live:
            while True:
                self.update_display(layout)
                
                # Check for user input (non-blocking)
                # In a real implementation, you'd handle keyboard input here
                
                await asyncio.sleep(0.5)
        
        # Clean up
        monitor_task.cancel()
        await self.stop_all()
    
    async def _monitor_queues(self):
        """Monitor message queues for statistics."""
        # This would connect to Kafka and monitor queue depths
        # For now, just update stats periodically
        while True:
            await asyncio.sleep(10)
            # Update stats here


@click.command()
@click.option('--repo', default=".", help='Repository path to work in')
@click.option('--config', help='Configuration file path')
@click.option('--start-all', is_flag=True, help='Start all services immediately')
def main(repo: str, config: Optional[str], start_all: bool):
    """Run the agent orchestrator."""
    orchestrator = Orchestrator(repo, config)
    
    async def run():
        if start_all:
            await orchestrator.start_all()
        await orchestrator.run()
    
    asyncio.run(run())


if __name__ == "__main__":
    main()