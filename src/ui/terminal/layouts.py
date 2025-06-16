"""
Standard layout patterns for terminal UI.
"""

from rich.layout import Layout
from rich.panel import Panel
from rich.align import Align
from typing import Optional

from src.ui.terminal.themes import THEME, RICH_STYLES


class StandardLayouts:
    """Collection of standard layout patterns."""
    
    @staticmethod
    def dashboard() -> Layout:
        """Create main dashboard layout as per mockup."""
        layout = Layout()
        
        # Main structure
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", size=20),
            Layout(name="footer", size=12)
        )
        
        # Body section - 3 columns
        layout["body"].split_row(
            Layout(name="agents", ratio=1),
            Layout(name="job_graph", ratio=2),
            Layout(name="system", ratio=1)
        )
        
        # Job and graph area
        layout["job_graph"].split_column(
            Layout(name="graph", ratio=1),
            Layout(name="job", ratio=1)
        )
        
        # Footer section - plan and logs
        layout["footer"].split_column(
            Layout(name="controls", size=3),
            Layout(name="details", ratio=1)
        )
        
        layout["details"].split_row(
            Layout(name="plan", ratio=1),
            Layout(name="logs", ratio=1)
        )
        
        return layout
    
    @staticmethod
    def simple_monitor() -> Layout:
        """Create simplified monitoring layout."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="logs", size=10)
        )
        
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )
        
        return layout
    
    @staticmethod
    def header_panel(title: str, subtitle: Optional[str] = None) -> Panel:
        """Create standard header panel."""
        content = f"[bold {THEME['primary']}]🤖 {title}[/]"
        if subtitle:
            content += f"\n[dim]{subtitle}[/]"
            
        return Panel(
            Align.center(content),
            style=f"on {THEME['surface']}",
            border_style="none"
        )
    
    @staticmethod
    def control_panel(controls: list) -> Panel:
        """Create control panel with keyboard shortcuts."""
        control_text = "  ".join([
            f"[{THEME['primary']}]{key}[/] {action}"
            for key, action in controls
        ])
        
        return Panel(
            control_text,
            title="Controls",
            border_style="dim"
        )
    
    @staticmethod
    def empty_panel(message: str = "No data") -> Panel:
        """Create empty state panel."""
        return Panel(
            f"[dim]{message}[/]",
            border_style="dim"
        )