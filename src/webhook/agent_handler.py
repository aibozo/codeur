"""
Agent Webhook Handler
====================

High-level webhook handler that integrates with the agent factory
to process webhook requests through the multi-agent system.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

from src.core.agent_factory import IntegratedAgentFactory
from src.core.event_bridge import EventBridge
from src.core.message_bus import MessageBus
from src.core.realtime import RealtimeService
from src.core.settings import Settings
from .handlers import Task, create_handler

logger = logging.getLogger(__name__)


class AgentWebhookHandler:
    """
    High-level webhook handler that processes webhooks through agents.
    """
    
    def __init__(self, factory: IntegratedAgentFactory):
        """
        Initialize with agent factory.
        
        Args:
            factory: Integrated agent factory
        """
        self.factory = factory
        self.handlers = {}
        
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook through appropriate handler and agents.
        
        Args:
            payload: Webhook payload with platform, event, and data
            
        Returns:
            Result of processing
        """
        platform = payload.get("platform", "")
        event_type = payload.get("event", "")
        data = payload.get("data", {})
        
        # Get or create platform handler
        if platform not in self.handlers:
            handler = create_handler(platform)
            if not handler:
                return {
                    "status": "error",
                    "error": f"No handler for platform: {platform}"
                }
            self.handlers[platform] = handler
            
        handler = self.handlers[platform]
        
        # Create webhook request structure
        # Create a simple webhook request object
        class WebhookRequest:
            def __init__(self, source, event_type, payload):
                self.source = source
                self.event_type = event_type
                self.payload = payload
        
        webhook_req = WebhookRequest(
            source=platform,
            event_type=event_type,
            payload=data
        )
        
        # Process through platform handler to get task
        task = await handler.process_webhook(webhook_req)
        
        if not task:
            return {
                "status": "ignored",
                "reason": "No task generated from webhook"
            }
            
        # Process task through agent system
        return await self.process_task(task)
        
    async def process_task(self, task: Task) -> Dict[str, Any]:
        """
        Process task through appropriate agents.
        
        Args:
            task: Task to process
            
        Returns:
            Processing result
        """
        try:
            # Determine task type and route to appropriate agent
            if task.command == "request":
                # Use request planner for general requests
                planner = self.factory.get_agent("request_planner")
                if planner:
                    result = await planner.process_request(task.description)
                    return {
                        "status": "success",
                        "task_id": result.get("id", "unknown"),
                        "tasks": result.get("tasks", [])
                    }
                    
            elif task.command == "analyze":
                # Use analyzer for architecture analysis
                analyzer = self.factory.get_agent("analyzer")
                if analyzer:
                    result = await analyzer.analyze_architecture()
                    return {
                        "status": "success",
                        "task_id": f"analysis_{task.source_id}",
                        "result": result
                    }
                    
            elif task.command == "code":
                # Direct coding task
                coder = self.factory.get_agent("coding_agent")
                if coder:
                    coding_task = {
                        "id": f"code_{task.source_id}",
                        "type": "coding",
                        "description": task.description,
                        "context": task.metadata
                    }
                    result = await coder.execute_task(coding_task)
                    return {
                        "status": "success",
                        "task_id": coding_task["id"],
                        "result": result
                    }
                    
            # Default: Use architect for conversation
            architect = self.factory.get_agent("architect")
            if architect:
                result = await architect.process_message(task.description)
                return {
                    "status": "success",
                    "task_id": f"arch_{task.source_id}",
                    "response": result.get("response", ""),
                    "tasks": result.get("tasks", [])
                }
                
            return {
                "status": "error",
                "error": "No suitable agent found for task"
            }
            
        except Exception as e:
            logger.error(f"Error processing task: {e}")
            return {
                "status": "error",
                "error": str(e)
            }