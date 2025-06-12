#!/usr/bin/env python3
"""
Code Planner agent runner with terminal interface.
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from agent_runner import AgentRunner
from src.code_planner import CodePlanner
from src.proto_gen import messages_pb2


class CodePlannerRunner(AgentRunner):
    """Runner for Code Planner agent."""
    
    def __init__(self, config_path: Optional[str] = None, repo_path: Optional[str] = None):
        super().__init__("Code Planner", config_path)
        
        # Initialize Code Planner
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.planner = CodePlanner(str(self.repo_path))
        
        # Track active plans
        self.active_plans = {}
    
    def get_topics(self) -> Dict[str, List[str]]:
        """Get topics for Code Planner."""
        return {
            "consume": ["plans"],
            "produce": ["task_bundles"]
        }
    
    async def process_message(self, message: Any) -> Optional[Any]:
        """Process a plan and create task bundle."""
        if isinstance(message, messages_pb2.Plan):
            try:
                # Add to active plans
                self.active_plans[message.id] = message
                
                self.add_message("PLAN", f"Processing plan with {len(message.steps)} steps")
                
                # Create task bundle
                bundle = await asyncio.to_thread(
                    self.planner.process_plan,
                    message
                )
                
                # Remove from active
                del self.active_plans[message.id]
                
                self.add_message("BUNDLE", f"Created {len(bundle.tasks)} tasks")
                
                return bundle
                
            except Exception as e:
                self.logger.error(f"Error processing plan: {e}")
                self.add_message("ERROR", str(e))
                return None
    
    def _deserialize_message(self, message) -> Optional[Any]:
        """Deserialize based on topic."""
        try:
            if message.topic == "plans":
                plan = messages_pb2.Plan()
                plan.ParseFromString(message.value)
                return plan
        except Exception as e:
            self.logger.error(f"Failed to deserialize: {e}")
        return None
    
    def _get_message_summary(self, message) -> str:
        """Get summary for display."""
        if isinstance(message, messages_pb2.Plan):
            return f"{message.id}: {len(message.steps)} steps"
        elif isinstance(message, messages_pb2.TaskBundle):
            return f"{message.id}: {len(message.tasks)} tasks"
        return super()._get_message_summary(message)
    
    def render_stats(self):
        """Render enhanced stats with Code Planner specifics."""
        panel = super().render_stats()
        
        # Add Code Planner specific stats
        from rich.table import Table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Code Analysis", style="cyan")
        table.add_column("Value", justify="right")
        
        if hasattr(self.planner, 'analyzer') and self.planner.analyzer.metrics:
            metrics = self.planner.analyzer.metrics
            table.add_row("Files Analyzed", str(metrics.get("files_analyzed", 0)))
            table.add_row("Functions Found", str(metrics.get("functions_found", 0)))
            table.add_row("Cache Hits", str(metrics.get("cache_hits", 0)))
        
        return panel


async def main():
    """Run the Code Planner."""
    import click
    
    @click.command()
    @click.option('--repo', default=".", help='Repository path to analyze')
    @click.option('--config', help='Configuration file path')
    def cli(repo: str, config: Optional[str]):
        """Run Code Planner agent."""
        runner = CodePlannerRunner(config, repo)
        asyncio.run(runner.start())
    
    cli()


if __name__ == "__main__":
    main()