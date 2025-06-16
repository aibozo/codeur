"""
Integrated Voice Agent with full system integration.

This agent integrates with the task graph, event system, and
other agents to provide comprehensive voice-based codebase interaction.
"""

import asyncio
from typing import Dict, Any, Set, Optional, List
from pathlib import Path

from ..core.integrated_agent_base import (
    IntegratedAgentBase, AgentContext, IntegrationLevel, AgentCapability
)
from ..core.logging import get_logger
from .voice_agent import VoiceAgent
from .audio_interfaces import AudioInput, AudioOutput

logger = get_logger(__name__)


class IntegratedVoiceAgent(IntegratedAgentBase, VoiceAgent):
    """
    Voice Agent with full system integration.
    
    This agent provides:
    - Natural language voice interaction
    - Task graph integration for complex operations
    - Event system for real-time updates
    - Multi-agent collaboration for comprehensive answers
    - Continuous learning from interactions
    """
    
    def __init__(self, context: AgentContext):
        """Initialize integrated voice agent."""
        # Initialize base classes
        IntegratedAgentBase.__init__(self, context)
        
        # Initialize voice agent with context
        VoiceAgent.__init__(
            self,
            rag_service=context.rag_client,
            audio_input=None,  # Will be set via set_audio_interfaces
            audio_output=None,
            project_path=context.project_path
        )
        
        # Track active voice sessions
        self.active_sessions: Set[str] = set()
        
        # Voice-specific configuration
        self.voice_config = {
            "max_response_length": 500,
            "thinking_mode": True,
            "context_window": 10,  # Recent messages to maintain
            "auto_summarize": True
        }
        
        logger.info(f"Initialized integrated voice agent: {context.agent_id}")
    
    def get_integration_level(self) -> IntegrationLevel:
        """Voice agent uses moderate integration."""
        return IntegrationLevel.MODERATE
    
    def get_capabilities(self) -> Set[AgentCapability]:
        """Voice agent capabilities."""
        return {
            AgentCapability.CONVERSATIONAL,
            AgentCapability.SEARCH,
            AgentCapability.DOCUMENTATION
        }
    
    def set_audio_interfaces(self, audio_input: AudioInput, audio_output: AudioOutput):
        """Set audio interfaces for voice processing."""
        self.audio_input = audio_input
        self.audio_output = audio_output
    
    async def process_voice_command(
        self,
        command: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Process a voice command with full system integration.
        
        This method enhances the base voice processing with:
        - Task creation for complex requests
        - Event emission for system updates
        - Multi-agent collaboration
        """
        # Track session
        self.active_sessions.add(session_id)
        
        # Emit voice interaction event
        await self.emit_event("voice.command_received", {
            "session_id": session_id,
            "command": command,
            "agent_id": self.context.agent_id
        })
        
        # Check if command requires task creation
        if self._requires_task_creation(command):
            return await self._handle_task_command(command, session_id)
        
        # Check if command requires multi-agent collaboration
        if self._requires_collaboration(command):
            return await self._handle_collaborative_command(command, session_id)
        
        # Standard voice processing
        response = await self.process_text(command, session_id)
        
        # Emit response event
        await self.emit_event("voice.response_generated", {
            "session_id": session_id,
            "response_preview": response[:100] + "..." if len(response) > 100 else response,
            "agent_id": self.context.agent_id
        })
        
        return {
            "response": response,
            "session_id": session_id,
            "type": "direct_response"
        }
    
    def _requires_task_creation(self, command: str) -> bool:
        """Check if command requires creating a task."""
        task_keywords = [
            "implement", "create", "build", "add feature",
            "refactor", "fix bug", "optimize", "update"
        ]
        command_lower = command.lower()
        return any(keyword in command_lower for keyword in task_keywords)
    
    def _requires_collaboration(self, command: str) -> bool:
        """Check if command requires multi-agent collaboration."""
        collab_keywords = [
            "analyze and fix", "review and improve",
            "find and update", "check and report",
            "compare", "evaluate options"
        ]
        command_lower = command.lower()
        return any(keyword in command_lower for keyword in collab_keywords)
    
    async def _handle_task_command(
        self,
        command: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Handle commands that require task creation."""
        # Create task from voice command
        if self._task_integration:
            # Parse command into task
            task_info = await self._parse_command_to_task(command)
            
            # Create task
            task_node = await self._task_integration.create_task(
                title=task_info["title"],
                description=task_info["description"],
                priority=task_info.get("priority", "medium"),
                metadata={
                    "source": "voice_command",
                    "session_id": session_id,
                    "original_command": command
                }
            )
            
            # Emit task creation event
            await self.emit_event("voice.task_created", {
                "session_id": session_id,
                "task_id": task_node.id,
                "title": task_info["title"]
            })
            
            response = f"I've created a task for you: '{task_info['title']}'. The task ID is {task_node.id}. I'll notify the appropriate agents to start working on it."
            
            return {
                "response": response,
                "session_id": session_id,
                "type": "task_created",
                "task_id": task_node.id,
                "task_info": task_info
            }
        
        # Fallback if task integration not available
        return await self.process_voice_command(
            "I understand you want me to " + command + ", but I need task management enabled to handle this request.",
            session_id
        )
    
    async def _handle_collaborative_command(
        self,
        command: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Handle commands requiring multi-agent collaboration."""
        # Determine which agents to involve
        agents_needed = self._determine_required_agents(command)
        
        # Collect responses from each agent
        responses = {}
        
        for agent_type in agents_needed:
            response = await self.request_from_agent(
                target_agent=agent_type,
                request_type="analyze",
                payload={
                    "query": command,
                    "session_id": session_id,
                    "context": self.get_session_summary(session_id)
                }
            )
            
            if response:
                responses[agent_type] = response
        
        # Synthesize combined response
        combined_response = await self._synthesize_responses(command, responses)
        
        return {
            "response": combined_response,
            "session_id": session_id,
            "type": "collaborative_response",
            "agents_involved": list(agents_needed)
        }
    
    def _determine_required_agents(self, command: str) -> Set[str]:
        """Determine which agents are needed for a command."""
        agents = set()
        command_lower = command.lower()
        
        if any(word in command_lower for word in ["analyze", "review", "check"]):
            agents.add("analyzer")
        
        if any(word in command_lower for word in ["implement", "code", "fix"]):
            agents.add("coding_agent")
        
        if any(word in command_lower for word in ["plan", "design", "architecture"]):
            agents.add("architect")
        
        return agents
    
    async def _parse_command_to_task(self, command: str) -> Dict[str, Any]:
        """Parse voice command into task structure."""
        # Use LLM to parse command
        prompt = f"""Parse this voice command into a task structure:

Command: {command}

Extract:
1. A clear, concise title (max 10 words)
2. A detailed description
3. Priority (high/medium/low)
4. Task type (feature/bug/refactor/documentation)

Respond in JSON format."""

        response = await self.llm_client.generate_with_json(
            prompt=prompt,
            temperature=0.3
        )
        
        # Ensure we have required fields
        task_info = {
            "title": response.get("title", command[:50]),
            "description": response.get("description", command),
            "priority": response.get("priority", "medium"),
            "type": response.get("task_type", "feature")
        }
        
        return task_info
    
    async def _synthesize_responses(
        self,
        original_command: str,
        agent_responses: Dict[str, Any]
    ) -> str:
        """Synthesize multiple agent responses into coherent answer."""
        # Build context from responses
        context_parts = []
        for agent, response in agent_responses.items():
            if isinstance(response, dict):
                content = response.get("analysis", response.get("response", str(response)))
            else:
                content = str(response)
            
            context_parts.append(f"{agent.upper()} Analysis:\n{content}")
        
        # Use LLM to synthesize
        prompt = f"""Synthesize these agent responses into a natural, conversational answer:

Original Question: {original_command}

{chr(10).join(context_parts)}

Create a unified response that:
1. Answers the original question comprehensively
2. Integrates insights from all agents naturally
3. Is conversational and easy to understand
4. References specific findings when relevant"""

        synthesized = await self.llm_client.generate(
            prompt=prompt,
            system_prompt="You are a helpful voice assistant synthesizing multiple expert analyses into a clear, conversational response.",
            temperature=0.7,
            max_tokens=500
        )
        
        return synthesized
    
    async def on_event_received(self, event_type: str, event_data: Dict[str, Any]):
        """Handle system events."""
        # React to relevant events
        if event_type == "task.completed":
            task_id = event_data.get("task_id")
            # Check if this task was created by voice
            task_metadata = event_data.get("metadata", {})
            if task_metadata.get("source") == "voice_command":
                session_id = task_metadata.get("session_id")
                if session_id in self.active_sessions:
                    # Notify via voice
                    notification = f"Good news! The task '{event_data.get('title')}' has been completed."
                    await self.emit_event("voice.notification", {
                        "session_id": session_id,
                        "message": notification,
                        "type": "task_completion"
                    })
        
        elif event_type == "code.validated":
            # Provide voice feedback on code validation
            logger.info("Code validation event received - could provide voice feedback")
    
    async def get_voice_insights(self) -> Dict[str, Any]:
        """Get insights about voice interactions."""
        insights = {
            "total_sessions": len(self.sessions),
            "active_sessions": len(self.active_sessions),
            "total_commands": sum(len(s.messages) // 2 for s in self.sessions.values()),
            "common_queries": self._analyze_common_queries(),
            "avg_session_duration": self._calculate_avg_session_duration()
        }
        
        return insights
    
    def _analyze_common_queries(self) -> List[Dict[str, Any]]:
        """Analyze common query patterns."""
        intent_counts = {}
        
        for session in self.sessions.values():
            for msg in session.messages:
                if msg["role"] == "user":
                    intent, _ = self._detect_intent(msg["content"])
                    intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        # Sort by frequency
        common = sorted(
            intent_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return [
            {"intent": intent, "count": count}
            for intent, count in common
        ]
    
    def _calculate_avg_session_duration(self) -> float:
        """Calculate average session duration in seconds."""
        if not self.sessions:
            return 0.0
        
        from datetime import datetime
        
        total_duration = 0
        for session in self.sessions.values():
            duration = (datetime.now() - session.started_at).total_seconds()
            total_duration += duration
        
        return total_duration / len(self.sessions)
    
    async def shutdown(self):
        """Clean up voice agent resources."""
        # Emit shutdown event for active sessions
        for session_id in self.active_sessions:
            await self.emit_event("voice.session_ended", {
                "session_id": session_id,
                "reason": "agent_shutdown"
            })
        
        # Clear sessions
        self.sessions.clear()
        self.active_sessions.clear()
        
        # Base shutdown
        await super().shutdown()