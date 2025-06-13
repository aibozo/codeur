"""
Request Planner for the Agent System.

This module handles user requests and orchestrates agent actions.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RequestPlan:
    """Represents a plan for handling a user request."""
    request_id: str
    goal: str
    steps: List[str] = field(default_factory=list)
    reasoning: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    

class RequestPlanner:
    """Plans and orchestrates user requests."""
    
    def __init__(self, message_bus=None):
        self.message_bus = message_bus
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
        
    async def initialize(self):
        """Initialize the request planner."""
        if not self._initialized:
            logger.info("Initializing RequestPlanner")
            self._initialized = True
            
    async def process_request_async(self, user_request) -> RequestPlan:
        """Process a user request asynchronously."""
        await self.initialize()
        
        request_id = user_request.id
        goal = user_request.goal
        
        # Track active request
        self.active_requests[request_id] = {
            "type": "user_request",
            "status": "planning",
            "progress": 0,
            "started_at": datetime.now().isoformat(),
            "goal": goal
        }
        
        # Create a plan (simplified for now)
        plan = RequestPlan(
            request_id=request_id,
            goal=goal,
            reasoning="I'll help you with this request by breaking it down into actionable steps."
        )
        
        # Analyze the goal to create steps
        if "build" in goal.lower() or "create" in goal.lower():
            plan.steps = [
                "Analyze requirements",
                "Design architecture",
                "Implement core functionality",
                "Add tests",
                "Review and refine"
            ]
        elif "fix" in goal.lower() or "debug" in goal.lower():
            plan.steps = [
                "Identify the issue",
                "Analyze root cause",
                "Implement fix",
                "Test the solution",
                "Verify resolution"
            ]
        elif "refactor" in goal.lower() or "improve" in goal.lower():
            plan.steps = [
                "Analyze current implementation",
                "Identify improvement areas",
                "Plan refactoring approach",
                "Implement changes",
                "Ensure backward compatibility"
            ]
        else:
            plan.steps = [
                "Understand the request",
                "Plan approach",
                "Execute solution",
                "Validate results"
            ]
            
        # Update request status
        self.active_requests[request_id]["status"] = "active"
        self.active_requests[request_id]["progress"] = 10
        
        return plan
        
    def process_request(self, user_request) -> RequestPlan:
        """Synchronous wrapper for process_request_async."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.process_request_async(user_request))
        finally:
            loop.close()