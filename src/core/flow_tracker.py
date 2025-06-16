"""
Message flow tracking for agent communication visualization.

This module tracks real-time message flows between agents and
provides data for animating the agent graph.
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, List, Any
import asyncio
from dataclasses import dataclass, field
from enum import Enum

from src.core.agent_graph import AgentGraph
from src.core.logging import get_logger

logger = get_logger(__name__)


class MessageType(Enum):
    """Types of messages that flow between agents."""
    REQUEST = "request"
    RESPONSE = "response"
    DELEGATION = "delegation"
    QUERY = "query"
    COMMAND = "command"
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class FlowEvent:
    """Represents a message flow event between agents."""
    from_agent: str
    to_agent: str
    message_type: MessageType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    payload_size: int = 0
    duration_ms: Optional[int] = None
    success: bool = True
    
    @property
    def edge_key(self) -> Tuple[str, str]:
        """Get the edge identifier for this flow."""
        return (self.from_agent, self.to_agent)


class FlowTracker:
    """
    Tracks message flows between agents for visualization.
    
    Maintains both current active flows and historical data
    for statistics and pattern analysis.
    """
    
    def __init__(self, agent_graph: AgentGraph, realtime_service, 
                 history_size: int = 10000, decay_time: float = 2.0):
        """
        Initialize flow tracker.
        
        Args:
            agent_graph: The agent graph structure
            realtime_service: Service for broadcasting updates
            history_size: Number of flow events to keep in history
            decay_time: Time in seconds for flow intensity to decay
        """
        self.agent_graph = agent_graph
        self.realtime_service = realtime_service
        self.flow_history = deque(maxlen=history_size)
        self.active_flows: Dict[Tuple[str, str], float] = defaultdict(float)
        self.decay_time = decay_time
        self._lock = asyncio.Lock()
        self._decay_tasks: Dict[Tuple[str, str], asyncio.Task] = {}
        self._update_task = None
        self._running = False
        
        # Statistics
        self.total_messages = 0
        self.edge_message_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        self.agent_message_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {'sent': 0, 'received': 0})
        
    async def start(self):
        """Start the flow tracker."""
        if self._running:
            return
            
        self._running = True
        self._update_task = asyncio.create_task(self._periodic_update())
        logger.info("Started flow tracker")
        
    async def stop(self):
        """Stop the flow tracker."""
        self._running = False
        
        # Cancel all decay tasks
        for task in self._decay_tasks.values():
            task.cancel()
        
        # Cancel update task
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
                
        logger.info("Stopped flow tracker")
    
    async def track_message(self, from_agent: str, to_agent: str, 
                          message_type: str = "request",
                          payload_size: int = 0,
                          duration_ms: Optional[int] = None,
                          success: bool = True) -> None:
        """
        Track a message flow between agents.
        
        Args:
            from_agent: Source agent ID
            to_agent: Target agent ID
            message_type: Type of message
            payload_size: Size of message payload in bytes
            duration_ms: Processing duration in milliseconds
            success: Whether the message was processed successfully
        """
        # Convert string to enum if needed
        if isinstance(message_type, str):
            try:
                msg_type = MessageType(message_type)
            except ValueError:
                msg_type = MessageType.REQUEST
        else:
            msg_type = message_type
            
        # Create flow event
        event = FlowEvent(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=msg_type,
            payload_size=payload_size,
            duration_ms=duration_ms,
            success=success
        )
        
        async with self._lock:
            # Add to history
            self.flow_history.append(event)
            
            # Update statistics
            self.total_messages += 1
            self.edge_message_counts[event.edge_key] += 1
            self.agent_message_counts[from_agent]['sent'] += 1
            self.agent_message_counts[to_agent]['received'] += 1
            
            # Update active flows
            self.active_flows[event.edge_key] += 1.0
            
            # Cancel existing decay task if any
            if event.edge_key in self._decay_tasks:
                self._decay_tasks[event.edge_key].cancel()
            
            # Schedule decay
            self._decay_tasks[event.edge_key] = asyncio.create_task(
                self._decay_flow(event.edge_key)
            )
        
        # Broadcast update immediately for responsiveness
        await self._broadcast_graph_update()
        
        logger.debug(f"Tracked message: {from_agent} -> {to_agent} ({msg_type.value})")
    
    async def _decay_flow(self, edge_key: Tuple[str, str]) -> None:
        """Gradually decay flow intensity for an edge."""
        decay_steps = 10
        decay_interval = self.decay_time / decay_steps
        
        try:
            for _ in range(decay_steps):
                await asyncio.sleep(decay_interval)
                
                async with self._lock:
                    if edge_key in self.active_flows:
                        self.active_flows[edge_key] *= 0.8  # Exponential decay
                        if self.active_flows[edge_key] < 0.1:
                            del self.active_flows[edge_key]
                            del self._decay_tasks[edge_key]
                            break
                            
        except asyncio.CancelledError:
            # Clean up on cancellation
            async with self._lock:
                if edge_key in self._decay_tasks:
                    del self._decay_tasks[edge_key]
    
    async def _periodic_update(self) -> None:
        """Periodically broadcast graph updates."""
        while self._running:
            try:
                await asyncio.sleep(1.0)  # Update every second
                await self._broadcast_graph_update()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic update: {e}")
    
    async def _broadcast_graph_update(self) -> None:
        """Send updated graph data to frontend."""
        try:
            # Get current graph data with active flows
            graph_data = self.agent_graph.get_graph_data(dict(self.active_flows))
            
            # Add flow statistics
            graph_data['stats'] = await self._calculate_flow_stats()
            
            # Broadcast update
            await self.realtime_service.broadcast({
                'type': 'graph_update',
                'timestamp': datetime.utcnow().isoformat(),
                'data': graph_data
            }, topic='graph')
            
        except Exception as e:
            logger.error(f"Error broadcasting graph update: {e}")
    
    async def _calculate_flow_stats(self) -> Dict[str, Any]:
        """Calculate flow statistics for display."""
        async with self._lock:
            # Time-based statistics
            now = datetime.utcnow()
            cutoff_1m = now - timedelta(minutes=1)
            cutoff_5m = now - timedelta(minutes=5)
            
            recent_1m = [f for f in self.flow_history if f.timestamp > cutoff_1m]
            recent_5m = [f for f in self.flow_history if f.timestamp > cutoff_5m]
            
            # Calculate message rates
            messages_per_minute = len(recent_1m)
            messages_per_5min = len(recent_5m)
            
            # Find busiest edge
            edge_counts_1m = defaultdict(int)
            for flow in recent_1m:
                edge_counts_1m[flow.edge_key] += 1
            
            busiest_edge = None
            if edge_counts_1m:
                busiest_edge = max(edge_counts_1m.items(), key=lambda x: x[1])
                busiest_edge = {
                    'from': busiest_edge[0][0],
                    'to': busiest_edge[0][1],
                    'count': busiest_edge[1]
                }
            
            # Calculate average latency
            latencies = [f.duration_ms for f in recent_1m if f.duration_ms is not None]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            
            # Success rate
            success_count = sum(1 for f in recent_1m if f.success)
            success_rate = (success_count / len(recent_1m) * 100) if recent_1m else 100
            
            # Message type distribution
            type_distribution = defaultdict(int)
            for flow in recent_1m:
                type_distribution[flow.message_type.value] += 1
            
            return {
                'total_messages': self.total_messages,
                'messages_per_minute': messages_per_minute,
                'messages_per_5min': messages_per_5min,
                'active_flows': len(self.active_flows),
                'busiest_edge': busiest_edge,
                'avg_latency_ms': round(avg_latency, 1),
                'success_rate': round(success_rate, 1),
                'message_types': dict(type_distribution),
                'top_agents': self._get_top_agents(recent_1m)
            }
    
    def _get_top_agents(self, flows: List[FlowEvent], limit: int = 3) -> List[Dict[str, Any]]:
        """Get the most active agents."""
        agent_activity = defaultdict(int)
        
        for flow in flows:
            agent_activity[flow.from_agent] += 1
            agent_activity[flow.to_agent] += 1
        
        top_agents = sorted(agent_activity.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return [
            {'agent': agent, 'messages': count}
            for agent, count in top_agents
        ]
    
    def get_edge_history(self, from_agent: str, to_agent: str, 
                        limit: int = 100) -> List[Dict[str, Any]]:
        """Get message history for a specific edge."""
        edge_key = (from_agent, to_agent)
        edge_flows = [
            {
                'timestamp': f.timestamp.isoformat(),
                'type': f.message_type.value,
                'payload_size': f.payload_size,
                'duration_ms': f.duration_ms,
                'success': f.success
            }
            for f in self.flow_history
            if f.edge_key == edge_key
        ]
        
        return edge_flows[-limit:]
    
    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get statistics for a specific agent."""
        return {
            'messages_sent': self.agent_message_counts[agent_id]['sent'],
            'messages_received': self.agent_message_counts[agent_id]['received'],
            'total_messages': (self.agent_message_counts[agent_id]['sent'] + 
                             self.agent_message_counts[agent_id]['received']),
            'connections': {
                'outgoing': list({f.to_agent for f in self.flow_history if f.from_agent == agent_id}),
                'incoming': list({f.from_agent for f in self.flow_history if f.to_agent == agent_id})
            }
        }