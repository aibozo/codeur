#!/usr/bin/env python3
"""
Request Planner agent runner with terminal interface.
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from agent_runner import AgentRunner
from src.request_planner import RequestPlanner
from src.proto_gen import messages_pb2
from src.rag_service import RAGClient, RAGService


class RequestPlannerRunner(AgentRunner):
    """Runner for Request Planner agent."""
    
    def __init__(self, config_path: Optional[str] = None):
        super().__init__("Request Planner", config_path)
        
        # Initialize Request Planner
        self.planner = RequestPlanner()
        
        # Initialize RAG service
        rag_dir = Path.home() / ".agent_rag"
        rag_service = RAGService(persist_directory=str(rag_dir))
        self.rag_client = RAGClient(service=rag_service)
        
        # Track active requests
        self.active_requests = {}
    
    def get_topics(self) -> Dict[str, List[str]]:
        """Get topics for Request Planner."""
        return {
            "consume": ["change_requests"],
            "produce": ["plans"]
        }
    
    async def process_message(self, message: Any) -> Optional[Any]:
        """Process a change request."""
        if isinstance(message, messages_pb2.ChangeRequest):
            try:
                # Add to active requests
                self.active_requests[message.id] = message
                
                self.add_message("REQUEST", f"Processing: {message.description_md[:50]}...")
                
                # Create plan using the planner
                plan = await asyncio.to_thread(
                    self.planner.create_plan,
                    message
                )
                
                # Convert to protobuf
                pb_plan = messages_pb2.Plan()
                pb_plan.id = plan.id
                pb_plan.parent_request_id = plan.parent_request_id
                pb_plan.affected_paths.extend(plan.affected_paths)
                pb_plan.complexity_label = getattr(
                    messages_pb2,
                    f"COMPLEXITY_{plan.complexity_label.value.upper()}"
                )
                pb_plan.estimated_tokens = plan.estimated_tokens
                pb_plan.rationale.extend(plan.rationale)
                
                # Add steps
                for step in plan.steps:
                    pb_step = pb_plan.steps.add()
                    pb_step.order = step.order
                    pb_step.goal = step.goal
                    pb_step.kind = getattr(
                        messages_pb2,
                        f"STEP_KIND_{step.kind.value.upper()}"
                    )
                    pb_step.hints.extend(step.hints)
                
                # Remove from active
                del self.active_requests[message.id]
                
                self.add_message("PLAN", f"Created plan with {len(plan.steps)} steps")
                
                return pb_plan
                
            except Exception as e:
                self.logger.error(f"Error processing request: {e}")
                self.add_message("ERROR", str(e))
                return None
    
    def _deserialize_message(self, message) -> Optional[Any]:
        """Deserialize based on topic."""
        try:
            if message.topic == "change_requests":
                req = messages_pb2.ChangeRequest()
                req.ParseFromString(message.value)
                return req
        except Exception as e:
            self.logger.error(f"Failed to deserialize: {e}")
        return None
    
    def _get_message_summary(self, message) -> str:
        """Get summary for display."""
        if isinstance(message, messages_pb2.ChangeRequest):
            return f"{message.id}: {message.description_md[:50]}..."
        elif isinstance(message, messages_pb2.Plan):
            return f"{message.id}: {len(message.steps)} steps, {message.complexity_label}"
        return super()._get_message_summary(message)


async def main():
    """Run the Request Planner."""
    runner = RequestPlannerRunner()
    await runner.start()


if __name__ == "__main__":
    asyncio.run(main())