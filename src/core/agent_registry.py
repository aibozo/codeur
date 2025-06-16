"""
Agent Registry Service for tracking and managing agent states.

This module provides centralized tracking of all active agents in the system,
including their status, current tasks, and performance metrics.
"""

from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
import asyncio
from enum import Enum
import logging

from src.core.logging import get_logger

logger = get_logger(__name__)


class AgentStatus(Enum):
    """Possible states for an agent."""
    INITIALIZING = "initializing"
    IDLE = "idle"
    ACTIVE = "active"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class AgentState:
    """Represents the current state of an agent."""
    agent_type: str
    status: AgentStatus
    model: str
    current_task: Optional[str] = None
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    metrics: Dict[str, float] = field(default_factory=dict)
    error_message: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        data['last_heartbeat'] = self.last_heartbeat.isoformat()
        # Frontend expects 'type' not 'agent_type'
        data['type'] = data.pop('agent_type')
        return data
    
    def is_healthy(self, timeout_seconds: int = 60) -> bool:
        """Check if agent is healthy based on heartbeat."""
        return (datetime.utcnow() - self.last_heartbeat).total_seconds() < timeout_seconds


class AgentRegistry:
    """
    Central registry for tracking all agents in the system.
    
    Provides methods for registering agents, updating their status,
    and broadcasting state changes via WebSocket.
    """
    
    def __init__(self, message_bus=None, realtime_service=None):
        """
        Initialize the agent registry.
        
        Args:
            message_bus: Optional message bus for event publishing
            realtime_service: Optional realtime service for WebSocket broadcasting
        """
        self.agents: Dict[str, AgentState] = {}
        self.message_bus = message_bus
        self.realtime_service = realtime_service
        self._lock = asyncio.Lock()
        self._health_check_task = None
        self._health_check_interval = 30  # seconds
        
    async def start(self):
        """Start background tasks like health monitoring."""
        if not self._health_check_task:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("Agent registry started with health monitoring")
    
    async def stop(self):
        """Stop background tasks."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            logger.info("Agent registry stopped")
    
    async def register_agent(
        self, 
        agent_type: str, 
        model: str,
        capabilities: List[str] = None
    ) -> None:
        """
        Register a new agent with the system.
        
        Args:
            agent_type: Type/name of the agent (e.g., 'request_planner')
            model: LLM model the agent is using
            capabilities: List of agent capabilities
        """
        async with self._lock:
            self.agents[agent_type] = AgentState(
                agent_type=agent_type,
                status=AgentStatus.IDLE,
                model=model,
                capabilities=capabilities or []
            )
            
        logger.info(f"Registered agent: {agent_type} with model {model}")
        await self._broadcast_agent_update(agent_type)
        
        # For now, skip message bus integration until we create proper event types
    
    async def unregister_agent(self, agent_type: str) -> None:
        """Remove an agent from the registry."""
        async with self._lock:
            if agent_type in self.agents:
                del self.agents[agent_type]
                
        logger.info(f"Unregistered agent: {agent_type}")
        
        # Notify about removal
        if self.realtime_service:
            await self.realtime_service.broadcast({
                'type': 'agent_removed',
                'data': {'agent_type': agent_type}
            }, topic='agents')
    
    async def update_agent_status(
        self, 
        agent_type: str, 
        status: AgentStatus,
        current_task: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update agent status and broadcast changes.
        
        Args:
            agent_type: Type of agent to update
            status: New status
            current_task: Description of current task (if active)
            error_message: Error message (if status is ERROR)
        """
        async with self._lock:
            if agent_type not in self.agents:
                logger.warning(f"Attempted to update unregistered agent: {agent_type}")
                return
                
            agent = self.agents[agent_type]
            old_status = agent.status
            
            agent.status = status
            agent.current_task = current_task if status == AgentStatus.ACTIVE else None
            agent.error_message = error_message if status == AgentStatus.ERROR else None
            agent.last_heartbeat = datetime.utcnow()
            
        logger.info(f"Agent {agent_type} status changed: {old_status.value} -> {status.value}")
        await self._broadcast_agent_update(agent_type)
        
        # For now, skip message bus integration until we create proper event types
    
    async def update_agent_metrics(
        self, 
        agent_type: str, 
        metrics: Dict[str, float]
    ) -> None:
        """
        Update agent performance metrics.
        
        Args:
            agent_type: Type of agent
            metrics: Dictionary of metric names to values
        """
        async with self._lock:
            if agent_type not in self.agents:
                logger.warning(f"Attempted to update metrics for unregistered agent: {agent_type}")
                return
                
            agent = self.agents[agent_type]
            agent.metrics.update(metrics)
            agent.last_heartbeat = datetime.utcnow()
            
        await self._broadcast_agent_update(agent_type)
    
    async def update_agent_model(self, agent_type: str, model: str) -> None:
        """Update the model used by an agent."""
        async with self._lock:
            if agent_type not in self.agents:
                logger.warning(f"Attempted to update model for unregistered agent: {agent_type}")
                return
                
            old_model = self.agents[agent_type].model
            self.agents[agent_type].model = model
            
        logger.info(f"Agent {agent_type} model changed: {old_model} -> {model}")
        await self._broadcast_agent_update(agent_type)
        
        # For now, skip message bus integration until we create proper event types
    
    async def heartbeat(self, agent_type: str) -> None:
        """Update agent heartbeat timestamp."""
        async with self._lock:
            if agent_type in self.agents:
                self.agents[agent_type].last_heartbeat = datetime.utcnow()
    
    async def get_agent(self, agent_type: str) -> Optional[AgentState]:
        """Get current state of a specific agent."""
        async with self._lock:
            return self.agents.get(agent_type)
    
    async def get_all_agents(self) -> List[AgentState]:
        """Get current state of all agents."""
        async with self._lock:
            return list(self.agents.values())
    
    async def get_active_agents(self) -> List[AgentState]:
        """Get all agents that are currently active."""
        async with self._lock:
            return [
                agent for agent in self.agents.values() 
                if agent.status == AgentStatus.ACTIVE
            ]
    
    async def _broadcast_agent_update(self, agent_type: str) -> None:
        """Broadcast agent state changes via WebSocket."""
        if not self.realtime_service:
            return
            
        agent = self.agents.get(agent_type)
        if not agent:
            return
            
        try:
            await self.realtime_service.broadcast({
                'type': 'agent_update',
                'data': {
                    'agent_type': agent_type,
                    'agent': agent.to_dict()
                }
            }, topic='agents')
        except Exception as e:
            logger.error(f"Failed to broadcast agent update: {e}")
    
    async def _health_check_loop(self) -> None:
        """Periodically check agent health and mark unhealthy agents as offline."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                async with self._lock:
                    for agent_type, agent in self.agents.items():
                        if (agent.status != AgentStatus.OFFLINE and 
                            not agent.is_healthy(timeout_seconds=60)):
                            
                            logger.warning(f"Agent {agent_type} failed health check")
                            agent.status = AgentStatus.OFFLINE
                            agent.current_task = None
                            
                            # Schedule broadcast outside lock
                            asyncio.create_task(self._broadcast_agent_update(agent_type))
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about registered agents."""
        total = len(self.agents)
        by_status = {}
        
        for agent in self.agents.values():
            status = agent.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            'total': total,
            'by_status': by_status,
            'active_count': by_status.get('active', 0),
            'error_count': by_status.get('error', 0),
            'offline_count': by_status.get('offline', 0)
        }