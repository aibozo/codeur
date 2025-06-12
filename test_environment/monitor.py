#!/usr/bin/env python3
"""
Real-time monitoring dashboard for the agent system.
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque, defaultdict
from typing import Dict, List, Optional
import click
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.chart import Chart

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.messaging.factory import MessageQueueFactory
from src.messaging.config import MessagingConfig
from src.proto_gen import messages_pb2


class MessageMonitor:
    """Monitor message flow through the system."""
    
    def __init__(self):
        self.console = Console()
        self.running = True
        
        # Message tracking
        self.message_counts = defaultdict(int)
        self.message_history = deque(maxlen=100)
        self.error_messages = deque(maxlen=50)
        
        # Performance tracking
        self.processing_times = defaultdict(list)
        self.throughput_history = deque(maxlen=60)  # Last 60 seconds
        
        # Active items tracking
        self.active_requests = {}
        self.active_plans = {}
        self.active_tasks = {}
        
        # Stats
        self.start_time = datetime.now()
        self.total_commits = 0
        self.successful_commits = 0
        
    def create_layout(self) -> Layout:
        """Create the monitoring dashboard layout."""
        layout = Layout()
        
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Split body into sections
        layout["body"].split_column(
            Layout(name="overview", size=10),
            Layout(name="details")
        )
        
        layout["details"].split_row(
            Layout(name="messages", ratio=2),
            Layout(name="performance", ratio=1)
        )
        
        return layout
    
    def render_header(self) -> Panel:
        """Render the header."""
        runtime = datetime.now() - self.start_time
        
        header_text = (
            f"[bold]Agent System Monitor[/bold] | "
            f"Runtime: {runtime} | "
            f"Messages: {sum(self.message_counts.values())}"
        )
        
        return Panel(header_text, style="bold blue")
    
    def render_overview(self) -> Panel:
        """Render system overview."""
        # Create a flow diagram showing message counts
        table = Table(show_header=False, box=None)
        
        # Message flow visualization
        flow = f"""
[cyan]Change Requests[/cyan] ({self.message_counts['change_requests']})
        ↓
[yellow]Plans[/yellow] ({self.message_counts['plans']})
        ↓
[green]Task Bundles[/green] ({self.message_counts['task_bundles']})
        ↓
[blue]Coding Tasks[/blue] ({self.message_counts['coding_tasks']})
        ↓
[magenta]Commit Results[/magenta] ({self.message_counts['commit_results']})

Success Rate: {self._get_success_rate():.1f}% | Total Commits: {self.total_commits}
"""
        
        table.add_column()
        table.add_row(flow)
        
        return Panel(table, title="Message Flow", border_style="green")
    
    def render_messages(self) -> Panel:
        """Render recent messages."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Time", style="cyan", width=12)
        table.add_column("Type", style="yellow", width=15)
        table.add_column("ID", style="white", width=20)
        table.add_column("Details", style="dim")
        
        # Show recent messages
        for msg in list(self.message_history)[-20:]:
            table.add_row(
                msg['time'].strftime("%H:%M:%S"),
                msg['type'],
                msg['id'][:12] + "..." if len(msg['id']) > 12 else msg['id'],
                msg['details']
            )
        
        return Panel(table, title="Recent Messages", border_style="blue")
    
    def render_performance(self) -> Panel:
        """Render performance metrics."""
        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        
        # Calculate metrics
        current_throughput = self._calculate_throughput()
        avg_processing_time = self._calculate_avg_processing_time()
        
        table.add_row("Messages/sec", f"{current_throughput:.1f}")
        table.add_row("Avg Processing", f"{avg_processing_time:.0f}ms")
        table.add_row("", "")
        table.add_row("[bold]Active Items[/bold]", "")
        table.add_row("Requests", str(len(self.active_requests)))
        table.add_row("Plans", str(len(self.active_plans)))
        table.add_row("Tasks", str(len(self.active_tasks)))
        table.add_row("", "")
        table.add_row("[bold]Errors[/bold]", str(len(self.error_messages)))
        
        return Panel(table, title="Performance", border_style="yellow")
    
    def render_footer(self) -> Panel:
        """Render the footer."""
        footer_text = (
            "Press [bold]Ctrl+C[/bold] to exit | "
            "[bold]r[/bold] to reset stats | "
            "[bold]e[/bold] to show errors"
        )
        return Panel(footer_text, style="dim")
    
    def _get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_commits == 0:
            return 0.0
        return (self.successful_commits / self.total_commits) * 100
    
    def _calculate_throughput(self) -> float:
        """Calculate current throughput."""
        if not self.throughput_history:
            return 0.0
        
        # Count messages in the last second
        now = datetime.now()
        recent = [t for t in self.throughput_history if now - t < timedelta(seconds=1)]
        return len(recent)
    
    def _calculate_avg_processing_time(self) -> float:
        """Calculate average processing time."""
        all_times = []
        for times in self.processing_times.values():
            all_times.extend(times[-10:])  # Last 10 for each type
        
        if not all_times:
            return 0.0
        return sum(all_times) / len(all_times)
    
    def process_message(self, topic: str, message: any):
        """Process a monitored message."""
        msg_info = {
            'time': datetime.now(),
            'type': topic,
            'id': '',
            'details': ''
        }
        
        # Extract details based on message type
        if topic == "change_requests" and hasattr(message, 'id'):
            msg_info['id'] = message.id
            msg_info['details'] = message.description_md[:50] + "..."
            self.active_requests[message.id] = message
            
        elif topic == "plans" and hasattr(message, 'id'):
            msg_info['id'] = message.id
            msg_info['details'] = f"{len(message.steps)} steps"
            self.active_plans[message.id] = message
            
        elif topic == "task_bundles" and hasattr(message, 'id'):
            msg_info['id'] = message.id
            msg_info['details'] = f"{len(message.tasks)} tasks"
            
        elif topic == "coding_tasks" and hasattr(message, 'id'):
            msg_info['id'] = message.id
            msg_info['details'] = message.goal[:40] + "..."
            self.active_tasks[message.id] = message
            
        elif topic == "commit_results" and hasattr(message, 'task_id'):
            msg_info['id'] = message.task_id
            self.total_commits += 1
            if message.success:
                self.successful_commits += 1
                msg_info['details'] = f"✓ {message.commit_sha[:8]}"
            else:
                msg_info['details'] = f"✗ {message.error_message[:30]}"
                self.error_messages.append(message)
            
            # Remove from active tasks
            self.active_tasks.pop(message.task_id, None)
        
        # Update tracking
        self.message_counts[topic] += 1
        self.message_history.append(msg_info)
        self.throughput_history.append(datetime.now())
    
    async def monitor_topic(self, topic: str, consumer):
        """Monitor a specific topic."""
        while self.running:
            try:
                # Poll for messages
                message = await asyncio.to_thread(
                    consumer.poll,
                    timeout=0.1
                )
                
                if message:
                    # Deserialize based on topic
                    decoded = self._deserialize_message(topic, message.value)
                    if decoded:
                        self.process_message(topic, decoded)
                        
            except Exception as e:
                self.console.print(f"[red]Error monitoring {topic}: {e}[/red]")
    
    def _deserialize_message(self, topic: str, data: bytes) -> Optional[any]:
        """Deserialize message based on topic."""
        try:
            if topic == "change_requests":
                msg = messages_pb2.ChangeRequest()
            elif topic == "plans":
                msg = messages_pb2.Plan()
            elif topic == "task_bundles":
                msg = messages_pb2.TaskBundle()
            elif topic == "coding_tasks":
                msg = messages_pb2.CodingTask()
            elif topic == "commit_results":
                msg = messages_pb2.CommitResult()
            else:
                return None
            
            msg.ParseFromString(data)
            return msg
            
        except Exception as e:
            self.console.print(f"[red]Failed to deserialize {topic}: {e}[/red]")
            return None
    
    async def run(self):
        """Run the monitoring dashboard."""
        # Set up consumers for all topics
        topics = [
            "change_requests",
            "plans", 
            "task_bundles",
            "coding_tasks",
            "commit_results"
        ]
        
        config = MessagingConfig(
            broker_url="localhost:9092",
            topics=topics,
            consumer_group="monitor_group"
        )
        
        queue = MessageQueueFactory.create_queue(config)
        consumers = {}
        tasks = []
        
        try:
            # Create consumers
            for topic in topics:
                consumer = queue.create_consumer([topic])
                consumers[topic] = consumer
                task = asyncio.create_task(self.monitor_topic(topic, consumer))
                tasks.append(task)
            
            # Create layout
            layout = self.create_layout()
            
            # Run the UI
            with Live(layout, refresh_per_second=2) as live:
                while self.running:
                    # Update display
                    layout["header"].update(self.render_header())
                    layout["overview"].update(self.render_overview())
                    layout["messages"].update(self.render_messages())
                    layout["performance"].update(self.render_performance())
                    layout["footer"].update(self.render_footer())
                    
                    await asyncio.sleep(0.5)
                    
        except KeyboardInterrupt:
            self.running = False
            
        finally:
            # Clean up
            for task in tasks:
                task.cancel()
            for consumer in consumers.values():
                consumer.close()
            queue.close()


@click.command()
def main():
    """Run the monitoring dashboard."""
    monitor = MessageMonitor()
    asyncio.run(monitor.run())


if __name__ == "__main__":
    main()