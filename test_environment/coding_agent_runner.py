#!/usr/bin/env python3
"""
Coding Agent runner with terminal interface.
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from agent_runner import AgentRunner
from src.coding_agent import CodingAgent, CommitStatus
from src.proto_gen import messages_pb2
from src.rag_service import RAGClient, RAGService
from src.llm import LLMClient


class CodingAgentRunner(AgentRunner):
    """Runner for Coding Agent."""
    
    def __init__(self, config_path: Optional[str] = None, repo_path: Optional[str] = None):
        super().__init__("Coding Agent", config_path)
        
        # Initialize repository path
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        
        # Initialize RAG service
        rag_dir = self.repo_path / ".rag"
        rag_service = RAGService(persist_directory=str(rag_dir))
        self.rag_client = RAGClient(service=rag_service)
        
        # Initialize LLM client
        self.llm_client = None
        try:
            self.llm_client = LLMClient()
            self.add_message("SYSTEM", "LLM client initialized")
        except Exception as e:
            self.add_message("WARNING", f"No LLM client: {e}")
        
        # Initialize Coding Agent
        self.agent = CodingAgent(
            repo_path=str(self.repo_path),
            rag_client=self.rag_client,
            llm_client=self.llm_client
        )
        
        # Track active tasks
        self.active_tasks = {}
    
    def get_topics(self) -> Dict[str, List[str]]:
        """Get topics for Coding Agent."""
        return {
            "consume": ["coding_tasks"],
            "produce": ["commit_results"]
        }
    
    async def process_message(self, message: Any) -> Optional[Any]:
        """Process a coding task."""
        if isinstance(message, messages_pb2.CodingTask):
            try:
                # Add to active tasks
                self.active_tasks[message.id] = message
                
                self.add_message("TASK", f"Starting: {message.goal[:50]}...")
                
                # Process the task
                result = await asyncio.to_thread(
                    self.agent.process_task,
                    message
                )
                
                # Convert to protobuf
                pb_result = messages_pb2.CommitResult()
                pb_result.task_id = result.task_id
                pb_result.success = (result.status == CommitStatus.SUCCESS)
                pb_result.commit_sha = result.commit_sha or ""
                pb_result.branch_name = result.branch_name or ""
                
                if not pb_result.success:
                    pb_result.error_message = "; ".join(result.notes)
                
                # Remove from active
                del self.active_tasks[message.id]
                
                status_str = "SUCCESS" if pb_result.success else "FAILED"
                self.add_message(status_str, f"Task {message.id} completed")
                
                return pb_result
                
            except Exception as e:
                self.logger.error(f"Error processing task: {e}")
                self.add_message("ERROR", str(e))
                
                # Return error result
                pb_result = messages_pb2.CommitResult()
                pb_result.task_id = message.id
                pb_result.success = False
                pb_result.error_message = str(e)
                return pb_result
    
    def _deserialize_message(self, message) -> Optional[Any]:
        """Deserialize based on topic."""
        try:
            if message.topic == "coding_tasks":
                task = messages_pb2.CodingTask()
                task.ParseFromString(message.value)
                return task
        except Exception as e:
            self.logger.error(f"Failed to deserialize: {e}")
        return None
    
    def _get_message_summary(self, message) -> str:
        """Get summary for display."""
        if isinstance(message, messages_pb2.CodingTask):
            return f"{message.id}: {message.goal[:40]}..."
        elif isinstance(message, messages_pb2.CommitResult):
            status = "✓" if message.success else "✗"
            return f"{status} {message.task_id}: {message.commit_sha[:8] if message.commit_sha else 'failed'}"
        return super()._get_message_summary(message)
    
    def render_stats(self):
        """Render enhanced stats with Coding Agent specifics."""
        from rich.table import Table
        from rich.panel import Panel
        
        # Create main stats table
        stats_table = Table(show_header=True, header_style="bold magenta")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", justify="right")
        
        stats_table.add_row("Messages Processed", str(self.stats["messages_processed"]))
        stats_table.add_row("Commits Created", str(self.stats["messages_produced"]))
        stats_table.add_row("Errors", str(self.stats["errors"]))
        stats_table.add_row("Avg Processing Time", f"{self.stats['avg_processing_time']:.2f}ms")
        
        # Add git stats if available
        if hasattr(self, 'git_stats'):
            stats_table.add_row("", "")  # Separator
            stats_table.add_row("Lines Added", str(self.git_stats.get("lines_added", 0)))
            stats_table.add_row("Lines Removed", str(self.git_stats.get("lines_removed", 0)))
            stats_table.add_row("Files Changed", str(self.git_stats.get("files_changed", 0)))
        
        return Panel(stats_table, title="Statistics", border_style="green")


async def main():
    """Run the Coding Agent."""
    import click
    
    @click.command()
    @click.option('--repo', default=".", help='Repository path to work in')
    @click.option('--config', help='Configuration file path')
    def cli(repo: str, config: Optional[str]):
        """Run Coding Agent."""
        runner = CodingAgentRunner(config, repo)
        asyncio.run(runner.start())
    
    cli()


if __name__ == "__main__":
    main()