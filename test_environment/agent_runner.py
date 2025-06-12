#!/usr/bin/env python3
"""
Base agent runner with terminal interface.
"""

import sys
import os
import asyncio
import signal
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import click
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.messaging.factory import MessageQueueFactory
from src.messaging.config import MessagingConfig
from src.core.logging import setup_logging
from src.proto_gen import messages_pb2


class AgentRunner(ABC):
    """Base class for running agents with terminal UI."""
    
    def __init__(self, agent_name: str, config_path: Optional[str] = None):
        self.agent_name = agent_name
        self.console = Console()
        self.running = False
        self.message_count = 0
        self.error_count = 0
        self.start_time = datetime.now()
        
        # Set up logging
        self.logger = setup_logging(logging.INFO)
        
        # Load messaging config
        self.messaging_config = self._load_config(config_path)
        self.message_queue = None
        self.producer = None
        self.consumer = None
        
        # Stats tracking
        self.stats = {
            "messages_processed": 0,
            "messages_produced": 0,
            "errors": 0,
            "avg_processing_time": 0.0
        }
        
        # Message history
        self.message_history = []
        
    def _load_config(self, config_path: Optional[str]) -> MessagingConfig:
        """Load messaging configuration."""
        if config_path:
            return MessagingConfig.from_file(config_path)
        else:
            # Default config for testing
            return MessagingConfig(
                broker_url=os.getenv("KAFKA_BROKER", "localhost:9092"),
                topics=self.get_topics(),
                consumer_group=f"{self.agent_name}_group"
            )
    
    @abstractmethod
    def get_topics(self) -> Dict[str, List[str]]:
        """Get topics to consume and produce.
        
        Returns:
            Dict with 'consume' and 'produce' lists
        """
        pass
    
    @abstractmethod
    async def process_message(self, message: Any) -> Optional[Any]:
        """Process a single message.
        
        Args:
            message: The decoded protobuf message
            
        Returns:
            Optional response message(s) to publish
        """
        pass
    
    def create_layout(self) -> Layout:
        """Create the terminal UI layout."""
        layout = Layout()
        
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        layout["body"].split_row(
            Layout(name="stats", ratio=1),
            Layout(name="messages", ratio=2)
        )
        
        return layout
    
    def render_header(self) -> Panel:
        """Render the header panel."""
        runtime = datetime.now() - self.start_time
        status = "[green]Running[/green]" if self.running else "[yellow]Stopped[/yellow]"
        
        header_text = f"[bold]{self.agent_name}[/bold] | Status: {status} | Runtime: {runtime}"
        return Panel(header_text, style="bold blue")
    
    def render_stats(self) -> Panel:
        """Render statistics panel."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        
        table.add_row("Messages Processed", str(self.stats["messages_processed"]))
        table.add_row("Messages Produced", str(self.stats["messages_produced"]))
        table.add_row("Errors", str(self.stats["errors"]))
        table.add_row("Avg Processing Time", f"{self.stats['avg_processing_time']:.2f}ms")
        
        return Panel(table, title="Statistics", border_style="green")
    
    def render_messages(self) -> Panel:
        """Render recent messages panel."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Time", style="cyan", width=12)
        table.add_column("Type", style="yellow")
        table.add_column("Message", style="white")
        
        # Show last 10 messages
        for entry in self.message_history[-10:]:
            table.add_row(
                entry["time"].strftime("%H:%M:%S"),
                entry["type"],
                entry["summary"]
            )
        
        return Panel(table, title="Recent Messages", border_style="blue")
    
    def render_footer(self) -> Panel:
        """Render the footer panel."""
        footer_text = "Press [bold]Ctrl+C[/bold] to stop | [bold]r[/bold] to restart | [bold]c[/bold] to clear"
        return Panel(footer_text, style="dim")
    
    def update_display(self, layout: Layout):
        """Update the display with current information."""
        layout["header"].update(self.render_header())
        layout["stats"].update(self.render_stats())
        layout["messages"].update(self.render_messages())
        layout["footer"].update(self.render_footer())
    
    def add_message(self, msg_type: str, summary: str):
        """Add a message to the history."""
        self.message_history.append({
            "time": datetime.now(),
            "type": msg_type,
            "summary": summary[:80]  # Truncate long messages
        })
        
        # Keep only last 100 messages
        if len(self.message_history) > 100:
            self.message_history = self.message_history[-100:]
    
    async def start(self):
        """Start the agent."""
        self.console.print(f"[bold green]Starting {self.agent_name}...[/bold green]")
        
        # Create message queue
        self.message_queue = MessageQueueFactory.create_queue(self.messaging_config)
        
        # Create producer
        self.producer = self.message_queue.create_producer()
        
        # Create consumer for input topics
        topics = self.get_topics()
        if topics.get("consume"):
            self.consumer = self.message_queue.create_consumer(topics["consume"])
        
        self.running = True
        self.add_message("SYSTEM", f"{self.agent_name} started")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Create layout
        layout = self.create_layout()
        
        # Start message processing in background
        process_task = asyncio.create_task(self._process_messages())
        
        # Run the UI
        with Live(layout, refresh_per_second=4) as live:
            while self.running:
                self.update_display(layout)
                await asyncio.sleep(0.25)
        
        # Clean up
        process_task.cancel()
        await self.cleanup()
    
    async def _process_messages(self):
        """Process messages in the background."""
        if not self.consumer:
            return
            
        while self.running:
            try:
                # Poll for messages with short timeout
                message = await asyncio.to_thread(
                    self.consumer.poll,
                    timeout=0.1
                )
                
                if message:
                    start_time = datetime.now()
                    
                    # Deserialize message based on topic
                    decoded_msg = self._deserialize_message(message)
                    
                    if decoded_msg:
                        # Add to history
                        self.add_message(
                            type(decoded_msg).__name__,
                            self._get_message_summary(decoded_msg)
                        )
                        
                        # Process the message
                        response = await self.process_message(decoded_msg)
                        
                        # Send response if any
                        if response:
                            await self._send_response(response)
                        
                        # Update stats
                        processing_time = (datetime.now() - start_time).total_seconds() * 1000
                        self._update_stats(processing_time)
                        
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
                self.stats["errors"] += 1
                self.add_message("ERROR", str(e))
    
    def _deserialize_message(self, message) -> Optional[Any]:
        """Deserialize a message based on its topic."""
        # This should be implemented based on your message types
        # For now, return a mock message
        return message
    
    def _get_message_summary(self, message) -> str:
        """Get a summary of the message for display."""
        if hasattr(message, 'id'):
            return f"ID: {message.id}"
        return str(message)[:80]
    
    async def _send_response(self, response):
        """Send response message(s)."""
        if isinstance(response, list):
            for msg in response:
                await self._send_single_response(msg)
        else:
            await self._send_single_response(response)
    
    async def _send_single_response(self, message):
        """Send a single response message."""
        # Determine topic based on message type
        topic = self._get_topic_for_message(message)
        if topic:
            self.producer.produce(topic, message.SerializeToString())
            self.stats["messages_produced"] += 1
            self.add_message(f"SENT->{topic}", self._get_message_summary(message))
    
    def _get_topic_for_message(self, message) -> Optional[str]:
        """Get the appropriate topic for a message type."""
        # Map message types to topics
        type_to_topic = {
            "Plan": "plans",
            "TaskBundle": "task_bundles",
            "CommitResult": "commit_results",
            "TestPlan": "test_plans"
        }
        
        msg_type = type(message).__name__
        return type_to_topic.get(msg_type)
    
    def _update_stats(self, processing_time: float):
        """Update statistics."""
        self.stats["messages_processed"] += 1
        
        # Update average processing time
        n = self.stats["messages_processed"]
        avg = self.stats["avg_processing_time"]
        self.stats["avg_processing_time"] = (avg * (n - 1) + processing_time) / n
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.console.print("\n[yellow]Shutting down...[/yellow]")
        self.running = False
    
    async def cleanup(self):
        """Clean up resources."""
        if self.producer:
            self.producer.close()
        if self.consumer:
            self.consumer.close()
        if self.message_queue:
            self.message_queue.close()
        
        self.console.print(f"[green]{self.agent_name} stopped.[/green]")


@click.command()
@click.option('--config', help='Path to configuration file')
@click.option('--agent', required=True, help='Agent type to run')
def main(config: Optional[str], agent: str):
    """Run an agent with terminal UI."""
    # This will be implemented by specific agent runners
    click.echo(f"Starting {agent} agent...")


if __name__ == "__main__":
    main()