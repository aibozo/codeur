#!/usr/bin/env python3
"""
Test scenario generator - creates sample change requests for testing.
"""

import sys
import asyncio
import uuid
from pathlib import Path
from datetime import datetime
import click
from rich.console import Console
from rich.progress import Progress

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.messaging.factory import MessageQueueFactory
from src.messaging.config import MessagingConfig
from src.messaging.base import QueueConfig
from src.proto_gen import messages_pb2


class TestScenario:
    """Generate test scenarios for the agent system."""
    
    def __init__(self):
        self.console = Console()
        self.message_queue = None
        self.producer = None
    
    async def setup(self):
        """Set up message queue connection."""
        config = QueueConfig(
            name="test_scenario",
            broker_url="localhost:9092",
            consumer_group="test_group"
        )
        
        self.message_queue = MessageQueueFactory.create_queue(
            MessagingConfig(
                broker_url="localhost:9092",
                topics=["change_requests"]
            )
        )
        
        self.producer = self.message_queue.create_producer()
        self.console.print("[green]Connected to message queue[/green]")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.producer:
            self.producer.close()
        if self.message_queue:
            self.message_queue.close()
    
    def create_error_handling_request(self) -> messages_pb2.ChangeRequest:
        """Create a request to add error handling."""
        request = messages_pb2.ChangeRequest()
        request.id = f"req-{uuid.uuid4().hex[:8]}"
        request.requester = "test_user"
        request.repo = "test_repo"
        request.branch = "main"
        request.description_md = """
# Add Error Handling to API Client

## Description
The API client in `src/api_client.py` needs proper error handling for network failures and API errors.

## Requirements
1. Add try-except blocks around all HTTP requests
2. Implement retry logic with exponential backoff
3. Add proper logging for errors
4. Return meaningful error messages to callers

## Acceptance Criteria
- All API calls handle network errors gracefully
- Failed requests are retried up to 3 times
- Errors are logged with appropriate context
- Unit tests cover error scenarios
"""
        request.metadata["priority"] = "high"
        request.metadata["type"] = "enhancement"
        
        return request
    
    def create_refactoring_request(self) -> messages_pb2.ChangeRequest:
        """Create a request to refactor code."""
        request = messages_pb2.ChangeRequest()
        request.id = f"req-{uuid.uuid4().hex[:8]}"
        request.requester = "test_user"
        request.repo = "test_repo"
        request.branch = "main"
        request.description_md = """
# Refactor Database Connection Management

## Description
The database connection code is duplicated across multiple modules. Refactor to use a connection pool.

## Requirements
1. Create a centralized database connection manager
2. Implement connection pooling
3. Add connection health checks
4. Update all modules to use the new manager

## Technical Details
- Current files: `db_users.py`, `db_products.py`, `db_orders.py`
- Each file has its own connection logic
- Move to a single `db_manager.py` with pooling
"""
        request.metadata["priority"] = "medium"
        request.metadata["type"] = "refactoring"
        
        return request
    
    def create_feature_request(self) -> messages_pb2.ChangeRequest:
        """Create a request to add a new feature."""
        request = messages_pb2.ChangeRequest()
        request.id = f"req-{uuid.uuid4().hex[:8]}"
        request.requester = "test_user"
        request.repo = "test_repo"
        request.branch = "main"
        request.description_md = """
# Add User Authentication Middleware

## Description
Implement JWT-based authentication middleware for the REST API.

## Requirements
1. Create authentication middleware that validates JWT tokens
2. Add token generation endpoint
3. Protect all API endpoints except login/register
4. Add role-based access control

## Implementation Notes
- Use PyJWT for token handling
- Store user sessions in Redis
- Add decorator for protecting routes
- Include refresh token mechanism
"""
        request.metadata["priority"] = "high"
        request.metadata["type"] = "feature"
        
        return request
    
    def create_bug_fix_request(self) -> messages_pb2.ChangeRequest:
        """Create a request to fix a bug."""
        request = messages_pb2.ChangeRequest()
        request.id = f"req-{uuid.uuid4().hex[:8]}"
        request.requester = "test_user"
        request.repo = "test_repo"
        request.branch = "main"
        request.description_md = """
# Fix Memory Leak in Data Processing Pipeline

## Description
The data processing pipeline in `src/pipeline/processor.py` has a memory leak causing OOM errors.

## Bug Details
- Memory usage grows linearly with processed records
- Appears to be keeping references to all processed data
- Occurs in the `transform_batch` method

## Fix Requirements
1. Identify and fix the memory leak
2. Add memory profiling tests
3. Ensure processed data is properly garbage collected
4. Add monitoring for memory usage
"""
        request.metadata["priority"] = "critical"
        request.metadata["type"] = "bug"
        
        return request
    
    async def send_request(self, request: messages_pb2.ChangeRequest):
        """Send a change request to the system."""
        self.console.print(f"[blue]Sending request:[/blue] {request.id}")
        self.console.print(f"  Type: {request.metadata.get('type', 'unknown')}")
        self.console.print(f"  Priority: {request.metadata.get('priority', 'medium')}")
        
        # Serialize and send
        self.producer.produce("change_requests", request.SerializeToString())
        
        self.console.print(f"[green]✓ Request sent successfully[/green]")
    
    async def run_scenario(self, scenario: str):
        """Run a specific test scenario."""
        scenarios = {
            "error_handling": self.create_error_handling_request,
            "refactoring": self.create_refactoring_request,
            "feature": self.create_feature_request,
            "bug_fix": self.create_bug_fix_request,
            "all": None  # Special case
        }
        
        if scenario not in scenarios:
            self.console.print(f"[red]Unknown scenario: {scenario}[/red]")
            self.console.print(f"Available: {', '.join(scenarios.keys())}")
            return
        
        await self.setup()
        
        try:
            if scenario == "all":
                # Send all scenarios
                with Progress() as progress:
                    task = progress.add_task("Sending requests...", total=4)
                    
                    for name, creator in scenarios.items():
                        if name != "all" and creator:
                            request = creator()
                            await self.send_request(request)
                            await asyncio.sleep(2)  # Space out requests
                            progress.update(task, advance=1)
            else:
                # Send specific scenario
                request = scenarios[scenario]()
                await self.send_request(request)
        
        finally:
            await self.cleanup()
    
    async def monitor_results(self, duration: int = 60):
        """Monitor the system for results."""
        self.console.print(f"[blue]Monitoring for {duration} seconds...[/blue]")
        
        # Set up consumer for commit results
        config = MessagingConfig(
            broker_url="localhost:9092",
            topics=["commit_results"],
            consumer_group="monitor_group"
        )
        
        queue = MessageQueueFactory.create_queue(config)
        consumer = queue.create_consumer(["commit_results"])
        
        end_time = asyncio.get_event_loop().time() + duration
        results = []
        
        try:
            while asyncio.get_event_loop().time() < end_time:
                # Poll for messages
                message = await asyncio.to_thread(
                    consumer.poll,
                    timeout=1.0
                )
                
                if message:
                    result = messages_pb2.CommitResult()
                    result.ParseFromString(message.value)
                    results.append(result)
                    
                    status = "[green]SUCCESS[/green]" if result.success else "[red]FAILED[/red]"
                    self.console.print(f"Result: {result.task_id} - {status}")
                    if result.commit_sha:
                        self.console.print(f"  Commit: {result.commit_sha[:8]}")
        
        finally:
            consumer.close()
            queue.close()
        
        # Summary
        self.console.print(f"\n[bold]Summary:[/bold]")
        self.console.print(f"Total results: {len(results)}")
        self.console.print(f"Successful: {sum(1 for r in results if r.success)}")
        self.console.print(f"Failed: {sum(1 for r in results if not r.success)}")


@click.command()
@click.option('--scenario', '-s', default='all',
              help='Test scenario to run (error_handling, refactoring, feature, bug_fix, all)')
@click.option('--monitor', '-m', is_flag=True,
              help='Monitor for results after sending')
@click.option('--monitor-duration', default=60,
              help='How long to monitor for results (seconds)')
async def main(scenario: str, monitor: bool, monitor_duration: int):
    """Run test scenarios for the agent system."""
    tester = TestScenario()
    
    # Run the scenario
    await tester.run_scenario(scenario)
    
    # Monitor if requested
    if monitor:
        await tester.monitor_results(monitor_duration)


if __name__ == "__main__":
    asyncio.run(main())