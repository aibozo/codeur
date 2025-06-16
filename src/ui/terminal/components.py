"""
Reusable Rich components for terminal UI.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.syntax import Syntax
from rich.markdown import Markdown

from src.ui.terminal.themes import THEME


class AgentCard:
    """Display card for an individual agent."""
    
    def __init__(self, agent_type: str, status: str, model: str, task: Optional[str] = None):
        self.agent_type = agent_type
        self.status = status
        self.model = model
        self.task = task
        
    @property
    def icon(self) -> str:
        """Get icon for agent type."""
        icons = {
            "request_planner": "📋",
            "code_planner": "🔧",
            "coding_agent": "✏️",
            "rag_service": "🔍",
            "git_operations": "📦"
        }
        return icons.get(self.agent_type, "🤖")
        
    @property
    def status_color(self) -> str:
        """Get color for status."""
        colors = {
            "active": THEME["success"],
            "idle": THEME["warning"],
            "error": THEME["error"],
            "offline": "dim"
        }
        return colors.get(self.status, "white")
        
    def render(self) -> Panel:
        """Render agent card as Rich panel."""
        content = f"{self.icon} [bold]{self.agent_type.replace('_', ' ').title()}[/bold]\n"
        content += f"[{self.status_color}]● {self.status.upper()}[/] | {self.model}\n"
        
        if self.task:
            content += f"\n[dim]Task:[/] {self.task[:30]}..."
            
        return Panel(
            content,
            title="Agent",
            border_style=self.status_color if self.status == "active" else "dim",
            width=30
        )


class GraphView:
    """ASCII/Unicode agent relationship graph."""
    
    def __init__(self, agents: List[str], connections: List[tuple]):
        self.agents = agents
        self.connections = connections
        
    def render(self) -> Panel:
        """Render graph as ASCII art."""
        # Simple ASCII representation
        graph = """
    RP → CP → CA
     ↓         ↓  
    RAG ← ← ← Git
        """
        
        return Panel(
            graph,
            title="Agent Graph",
            border_style="dim"
        )


class LogStream:
    """Formatted, filterable log output."""
    
    def __init__(self, max_lines: int = 20):
        self.logs: List[Dict[str, Any]] = []
        self.max_lines = max_lines
        
    def add_log(self, level: str, message: str, source: str, timestamp: Optional[datetime] = None):
        """Add a log entry."""
        if timestamp is None:
            timestamp = datetime.now()
            
        self.logs.append({
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "source": source
        })
        
        # Keep only recent logs
        if len(self.logs) > self.max_lines:
            self.logs = self.logs[-self.max_lines:]
            
    def render(self) -> Panel:
        """Render log stream."""
        console = Console()
        
        log_text = ""
        for log in self.logs:
            time_str = log["timestamp"].strftime("%H:%M:%S")
            level_color = {
                "INFO": THEME["info"],
                "DEBUG": "dim",
                "WARN": THEME["warning"],
                "ERROR": THEME["error"]
            }.get(log["level"], "white")
            
            log_text += f"[dim]{time_str}[/] [{level_color}]{log['level']:5}[/] {log['source']}: {log['message']}\n"
            
        return Panel(
            log_text.strip() or "[dim]No logs yet...[/]",
            title="Logs [↓ Auto]",
            border_style="dim",
            height=10
        )


class MetricsBar:
    """Performance indicators bar."""
    
    def __init__(self):
        self.metrics = {
            "cpu": 0,
            "memory": 0,
            "queue": 0,
            "tokens": 0
        }
        
    def update(self, **kwargs):
        """Update metrics."""
        self.metrics.update(kwargs)
        
    def render(self) -> Panel:
        """Render metrics bar."""
        cpu_bar = self._create_bar("CPU", self.metrics["cpu"], 100)
        mem_bar = self._create_bar("Memory", self.metrics["memory"], 100)
        
        content = f"{cpu_bar}\n{mem_bar}\n"
        content += f"Queue:  {self.metrics['queue']} pending\n"
        content += f"Tokens: {self.metrics['tokens']:,}"
        
        return Panel(
            content,
            title="System",
            border_style="dim"
        )
        
    def _create_bar(self, label: str, value: float, max_value: float) -> str:
        """Create a simple progress bar."""
        percentage = min(value / max_value, 1.0)
        filled = int(percentage * 10)
        empty = 10 - filled
        
        bar = "▇" * filled + "░" * empty
        return f"{label:7} {bar} {value:.0f}%"


class PlanView:
    """Collapsible plan/diff viewer."""
    
    def __init__(self, plan: Optional[str] = None, diff: Optional[str] = None):
        self.plan = plan
        self.diff = diff
        self.view_mode = "plan"  # "plan" or "diff"
        
    def toggle_mode(self):
        """Toggle between plan and diff view."""
        self.view_mode = "diff" if self.view_mode == "plan" else "plan"
        
    def render(self) -> Panel:
        """Render plan or diff view."""
        if self.view_mode == "plan" and self.plan:
            content = Markdown(self.plan)
        elif self.view_mode == "diff" and self.diff:
            content = Syntax(self.diff, "diff", theme="monokai")
        else:
            content = "[dim]No content available[/]"
            
        title = f"📄 Plan" if self.view_mode == "plan" else "🔍 Diff"
        
        return Panel(
            content,
            title=title,
            border_style="dim",
            height=15
        )


class DashboardLayout:
    """Main dashboard layout manager."""
    
    def __init__(self):
        self.layout = Layout()
        self.setup_layout()
        
    def setup_layout(self):
        """Configure dashboard layout."""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=12)
        )
        
        self.layout["body"].split_row(
            Layout(name="agents", ratio=1),
            Layout(name="job", ratio=1),
            Layout(name="metrics", ratio=1)
        )
        
        self.layout["footer"].split_row(
            Layout(name="plan", ratio=2),
            Layout(name="logs", ratio=1)
        )
        
    def update_header(self, title: str):
        """Update header content."""
        header = Panel(
            f"[bold]{title}[/bold]",
            style=f"on {THEME['surface']}",
            border_style="none"
        )
        self.layout["header"].update(header)
        
    def render(self) -> Layout:
        """Get the layout for rendering."""
        return self.layout