# Codeur Dashboard Integration Plan

## Overview
This document outlines the integration plan for connecting the Codeur web dashboard to the actual agent system, including real-time metrics, agent status tracking, and network visualization.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │ Agent Cards  │  │ System Stats │  │  Network Graph    │   │
│  └──────────────┘  └──────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ WebSocket
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    WebSocket Server (FastAPI)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │Event Bridge  │  │Metrics Coll. │  │  State Manager    │   │
│  └──────────────┘  └──────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ Message Bus
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Agent System                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │    RP    │  │    CP    │  │    CA    │  │     RAG      │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Phase 1: Agent Status Integration

### 1.1 Agent Registry Service
Create a centralized agent registry that tracks all active agents:

```python
# src/core/agent_registry.py
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
import asyncio
from enum import Enum

class AgentStatus(Enum):
    INITIALIZING = "initializing"
    IDLE = "idle"
    ACTIVE = "active"
    ERROR = "error"
    OFFLINE = "offline"

@dataclass
class AgentState:
    agent_type: str
    status: AgentStatus
    model: str
    current_task: Optional[str] = None
    last_heartbeat: datetime = None
    metrics: Dict[str, float] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.utcnow()
        if self.metrics is None:
            self.metrics = {}

class AgentRegistry:
    def __init__(self, message_bus, realtime_service):
        self.agents: Dict[str, AgentState] = {}
        self.message_bus = message_bus
        self.realtime_service = realtime_service
        self._lock = asyncio.Lock()
        
    async def register_agent(self, agent_type: str, model: str):
        """Register a new agent with the system."""
        async with self._lock:
            self.agents[agent_type] = AgentState(
                agent_type=agent_type,
                status=AgentStatus.IDLE,
                model=model
            )
        await self._broadcast_agent_update(agent_type)
    
    async def update_agent_status(self, agent_type: str, status: AgentStatus, 
                                  current_task: Optional[str] = None):
        """Update agent status and broadcast changes."""
        async with self._lock:
            if agent_type in self.agents:
                self.agents[agent_type].status = status
                self.agents[agent_type].current_task = current_task
                self.agents[agent_type].last_heartbeat = datetime.utcnow()
        await self._broadcast_agent_update(agent_type)
    
    async def update_agent_metrics(self, agent_type: str, metrics: Dict[str, float]):
        """Update agent performance metrics."""
        async with self._lock:
            if agent_type in self.agents:
                self.agents[agent_type].metrics.update(metrics)
        await self._broadcast_agent_update(agent_type)
    
    async def _broadcast_agent_update(self, agent_type: str):
        """Broadcast agent state changes via WebSocket."""
        if agent_type in self.agents:
            await self.realtime_service.broadcast_agent_update(
                agent_type=agent_type,
                status=self.agents[agent_type].status.value,
                data=asdict(self.agents[agent_type])
            )
```

### 1.2 Agent Base Class Enhancement
Modify the base agent class to automatically report status:

```python
# src/agents/base_agent.py (enhancement)
class BaseAgent:
    def __init__(self, agent_type: str, model: str, registry: AgentRegistry):
        self.agent_type = agent_type
        self.model = model
        self.registry = registry
        self._task_start_time = None
        
    async def initialize(self):
        """Initialize agent and register with system."""
        await self.registry.register_agent(self.agent_type, self.model)
        
    async def start_task(self, task_description: str):
        """Mark task start and update status."""
        self._task_start_time = time.time()
        await self.registry.update_agent_status(
            self.agent_type, 
            AgentStatus.ACTIVE,
            task_description
        )
    
    async def complete_task(self, tokens_used: int = 0):
        """Mark task completion and update metrics."""
        duration = time.time() - self._task_start_time if self._task_start_time else 0
        
        await self.registry.update_agent_metrics(self.agent_type, {
            'tasks_completed': 1,  # Increment
            'tokens_used': tokens_used,
            'avg_task_duration': duration
        })
        
        await self.registry.update_agent_status(
            self.agent_type, 
            AgentStatus.IDLE,
            None
        )
```

### 1.3 Message Bus Integration
Connect agent events to the dashboard:

```python
# src/core/event_bridge.py (enhancement)
class EventBridge:
    def __init__(self, message_bus: MessageBus, realtime_service: RealtimeService):
        self.message_bus = message_bus
        self.realtime_service = realtime_service
        self._setup_subscriptions()
    
    def _setup_subscriptions(self):
        # Subscribe to agent events
        self.message_bus.subscribe('agent.task.started', self._handle_task_started)
        self.message_bus.subscribe('agent.task.completed', self._handle_task_completed)
        self.message_bus.subscribe('agent.error', self._handle_agent_error)
        self.message_bus.subscribe('job.status.changed', self._handle_job_update)
    
    async def _handle_task_started(self, event):
        await self.realtime_service.broadcast({
            'type': 'agent_update',
            'data': {
                'agent_type': event['agent_type'],
                'status': 'active',
                'current_task': event['task_description']
            }
        }, topic='agents')
```

## Phase 2: System Metrics Collection

### 2.1 Metrics Collector Service
Implement system resource monitoring:

```python
# src/core/metrics_collector.py
import psutil
import asyncio
from typing import Dict
import GPUtil

class MetricsCollector:
    def __init__(self, realtime_service, interval: int = 5):
        self.realtime_service = realtime_service
        self.interval = interval
        self._running = False
        
    async def start(self):
        """Start collecting system metrics."""
        self._running = True
        while self._running:
            metrics = await self._collect_metrics()
            await self.realtime_service.broadcast({
                'type': 'system_metrics',
                'data': metrics
            }, topic='metrics')
            await asyncio.sleep(self.interval)
    
    async def _collect_metrics(self) -> Dict[str, any]:
        """Collect current system metrics."""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        
        # GPU metrics (if available)
        gpu_metrics = []
        try:
            gpus = GPUtil.getGPUs()
            for gpu in gpus:
                gpu_metrics.append({
                    'name': gpu.name,
                    'load': gpu.load * 100,
                    'memory_used': gpu.memoryUsed,
                    'memory_total': gpu.memoryTotal,
                    'temperature': gpu.temperature
                })
        except:
            pass
        
        # Process metrics
        process = psutil.Process()
        
        return {
            'cpu': {
                'usage_percent': cpu_percent,
                'frequency_mhz': cpu_freq.current if cpu_freq else 0,
                'cores': psutil.cpu_count()
            },
            'memory': {
                'used_gb': memory.used / (1024**3),
                'total_gb': memory.total / (1024**3),
                'percent': memory.percent
            },
            'gpu': gpu_metrics,
            'process': {
                'memory_mb': process.memory_info().rss / (1024**2),
                'threads': process.num_threads()
            }
        }
```

### 2.2 Queue Metrics Integration
Track job queue statistics:

```python
# src/core/queue_metrics.py
from collections import deque
from datetime import datetime, timedelta

class QueueMetrics:
    def __init__(self, realtime_service):
        self.realtime_service = realtime_service
        self.job_history = deque(maxlen=1000)
        self.active_jobs = {}
        
    async def job_enqueued(self, job_id: str, job_type: str):
        """Track when a job is added to queue."""
        self.active_jobs[job_id] = {
            'type': job_type,
            'enqueued_at': datetime.utcnow(),
            'status': 'queued'
        }
        await self._broadcast_metrics()
    
    async def job_started(self, job_id: str, agent_type: str):
        """Track when a job starts processing."""
        if job_id in self.active_jobs:
            self.active_jobs[job_id]['started_at'] = datetime.utcnow()
            self.active_jobs[job_id]['status'] = 'processing'
            self.active_jobs[job_id]['agent_type'] = agent_type
        await self._broadcast_metrics()
    
    async def job_completed(self, job_id: str, success: bool = True):
        """Track job completion."""
        if job_id in self.active_jobs:
            job = self.active_jobs.pop(job_id)
            job['completed_at'] = datetime.utcnow()
            job['success'] = success
            job['duration'] = (job['completed_at'] - job['enqueued_at']).total_seconds()
            self.job_history.append(job)
        await self._broadcast_metrics()
    
    async def _broadcast_metrics(self):
        """Calculate and broadcast queue metrics."""
        # Calculate metrics
        queue_length = sum(1 for j in self.active_jobs.values() if j['status'] == 'queued')
        processing = sum(1 for j in self.active_jobs.values() if j['status'] == 'processing')
        
        # Calculate average wait time
        recent_jobs = list(self.job_history)[-100:]
        avg_wait_time = 0
        if recent_jobs:
            wait_times = []
            for job in recent_jobs:
                if 'started_at' in job:
                    wait = (job['started_at'] - job['enqueued_at']).total_seconds()
                    wait_times.append(wait)
            avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0
        
        await self.realtime_service.broadcast({
            'type': 'queue_metrics',
            'data': {
                'queue_length': queue_length,
                'processing': processing,
                'avg_wait_time': avg_wait_time,
                'completed_last_hour': sum(1 for j in self.job_history 
                                         if j.get('completed_at', datetime.min) > 
                                         datetime.utcnow() - timedelta(hours=1))
            }
        }, topic='metrics')
```

## Phase 3: Agent Network Graph

### 3.1 Graph Data Structure
Define the agent relationship graph:

```python
# src/core/agent_graph.py
from typing import Dict, List, Set, Tuple
import networkx as nx

class AgentGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self._initialize_graph()
        
    def _initialize_graph(self):
        """Initialize the agent dependency graph."""
        # Define nodes
        agents = [
            ('request_planner', {'label': 'RP', 'type': 'orchestrator'}),
            ('code_planner', {'label': 'CP', 'type': 'planner'}),
            ('coding_agent', {'label': 'CA', 'type': 'executor'}),
            ('rag_service', {'label': 'RAG', 'type': 'service'}),
            ('git_operations', {'label': 'Git', 'type': 'service'}),
        ]
        self.graph.add_nodes_from(agents)
        
        # Define edges (dependencies)
        edges = [
            ('request_planner', 'code_planner', {'weight': 1.0, 'type': 'delegates'}),
            ('request_planner', 'rag_service', {'weight': 0.5, 'type': 'queries'}),
            ('code_planner', 'coding_agent', {'weight': 1.0, 'type': 'assigns'}),
            ('coding_agent', 'git_operations', {'weight': 0.8, 'type': 'uses'}),
            ('rag_service', 'git_operations', {'weight': 0.3, 'type': 'indexes'}),
        ]
        self.graph.add_edges_from(edges)
    
    def get_graph_data(self, active_flows: Dict[Tuple[str, str], float] = None):
        """Get graph data for visualization."""
        nodes = []
        edges = []
        
        # Process nodes
        for node, data in self.graph.nodes(data=True):
            nodes.append({
                'id': node,
                'label': data['label'],
                'type': data['type'],
                'x': self._get_node_position(node)[0],
                'y': self._get_node_position(node)[1]
            })
        
        # Process edges
        for source, target, data in self.graph.edges(data=True):
            edge_data = {
                'source': source,
                'target': target,
                'type': data['type'],
                'weight': data['weight']
            }
            
            # Add flow information if available
            if active_flows and (source, target) in active_flows:
                edge_data['flow'] = active_flows[(source, target)]
                edge_data['active'] = True
            
            edges.append(edge_data)
        
        return {'nodes': nodes, 'edges': edges}
    
    def _get_node_position(self, node: str) -> Tuple[float, float]:
        """Calculate node position for visualization."""
        positions = {
            'request_planner': (200, 100),
            'code_planner': (400, 200),
            'coding_agent': (600, 200),
            'rag_service': (300, 350),
            'git_operations': (500, 350),
        }
        return positions.get(node, (0, 0))
```

### 3.2 Flow Tracking
Track active message flows between agents:

```python
# src/core/flow_tracker.py
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

class FlowTracker:
    def __init__(self, agent_graph: AgentGraph, realtime_service):
        self.agent_graph = agent_graph
        self.realtime_service = realtime_service
        self.active_flows = defaultdict(float)
        self.flow_history = deque(maxlen=10000)
        
    async def track_message(self, from_agent: str, to_agent: str, message_type: str):
        """Track a message flow between agents."""
        flow_key = (from_agent, to_agent)
        self.active_flows[flow_key] += 1
        
        self.flow_history.append({
            'from': from_agent,
            'to': to_agent,
            'type': message_type,
            'timestamp': datetime.utcnow()
        })
        
        # Broadcast updated graph
        await self._broadcast_graph_update()
        
        # Decay the flow after a delay
        asyncio.create_task(self._decay_flow(flow_key))
    
    async def _decay_flow(self, flow_key: Tuple[str, str], delay: float = 2.0):
        """Gradually decay flow intensity."""
        await asyncio.sleep(delay)
        self.active_flows[flow_key] = max(0, self.active_flows[flow_key] - 1)
        if self.active_flows[flow_key] == 0:
            del self.active_flows[flow_key]
        await self._broadcast_graph_update()
    
    async def _broadcast_graph_update(self):
        """Send updated graph data to frontend."""
        graph_data = self.agent_graph.get_graph_data(dict(self.active_flows))
        
        # Add current statistics
        graph_data['stats'] = self._calculate_flow_stats()
        
        await self.realtime_service.broadcast({
            'type': 'graph_update',
            'data': graph_data
        }, topic='graph')
    
    def _calculate_flow_stats(self) -> Dict[str, any]:
        """Calculate flow statistics for the last minute."""
        cutoff = datetime.utcnow() - timedelta(minutes=1)
        recent_flows = [f for f in self.flow_history if f['timestamp'] > cutoff]
        
        # Count messages per edge
        edge_counts = defaultdict(int)
        for flow in recent_flows:
            edge_counts[(flow['from'], flow['to'])] += 1
        
        return {
            'total_messages': len(recent_flows),
            'active_edges': len(self.active_flows),
            'busiest_edge': max(edge_counts.items(), key=lambda x: x[1])[0] if edge_counts else None
        }
```

## Phase 4: Log Streaming

### 4.1 Structured Logging Integration
Enhance logging to support real-time streaming:

```python
# src/core/log_streamer.py
import logging
from typing import Optional
from datetime import datetime

class StreamingLogHandler(logging.Handler):
    def __init__(self, realtime_service, agent_type: Optional[str] = None):
        super().__init__()
        self.realtime_service = realtime_service
        self.agent_type = agent_type
        
    def emit(self, record: logging.LogRecord):
        """Emit log record to WebSocket subscribers."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'source': self.agent_type or record.name,
            'message': self.format(record),
            'thread': record.thread,
            'function': record.funcName
        }
        
        # Don't block on async operation
        asyncio.create_task(
            self.realtime_service.broadcast({
                'type': 'log_entry',
                'data': log_entry
            }, topic='logs')
        )

def setup_streaming_logs(realtime_service, agent_type: Optional[str] = None):
    """Setup log streaming for an agent or module."""
    handler = StreamingLogHandler(realtime_service, agent_type)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    logger = logging.getLogger(agent_type) if agent_type else logging.getLogger()
    logger.addHandler(handler)
    
    return logger
```

## Phase 5: Frontend Integration

### 5.1 Update Frontend Types
Add new message types:

```typescript
// frontend/src/api/types.ts (additions)
export interface SystemMetrics {
  cpu: {
    usage_percent: number;
    frequency_mhz: number;
    cores: number;
  };
  memory: {
    used_gb: number;
    total_gb: number;
    percent: number;
  };
  gpu: Array<{
    name: string;
    load: number;
    memory_used: number;
    memory_total: number;
    temperature: number;
  }>;
  process: {
    memory_mb: number;
    threads: number;
  };
}

export interface GraphData {
  nodes: Array<{
    id: string;
    label: string;
    type: string;
    x: number;
    y: number;
  }>;
  edges: Array<{
    source: string;
    target: string;
    type: string;
    weight: number;
    flow?: number;
    active?: boolean;
  }>;
  stats: {
    total_messages: number;
    active_edges: number;
    busiest_edge: [string, string] | null;
  };
}
```

### 5.2 Create Graph Visualization Component
Using D3.js or React Flow:

```typescript
// frontend/src/components/AgentGraph.tsx
import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { GraphData } from '../api/types';

interface AgentGraphProps {
  data: GraphData;
}

export const AgentGraph: React.FC<AgentGraphProps> = ({ data }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  useEffect(() => {
    if (!svgRef.current || !data) return;
    
    const svg = d3.select(svgRef.current);
    const width = 800;
    const height = 400;
    
    // Clear previous render
    svg.selectAll("*").remove();
    
    // Create arrow markers
    svg.append("defs").selectAll("marker")
      .data(["arrow"])
      .enter().append("marker")
      .attr("id", d => d)
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 25)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#666");
    
    // Draw edges
    const edges = svg.append("g")
      .selectAll("path")
      .data(data.edges)
      .enter().append("path")
      .attr("d", d => {
        const source = data.nodes.find(n => n.id === d.source);
        const target = data.nodes.find(n => n.id === d.target);
        return `M${source.x},${source.y} L${target.x},${target.y}`;
      })
      .attr("stroke", d => d.active ? "#00D9FF" : "#666")
      .attr("stroke-width", d => d.active ? 2 + (d.flow || 0) : 1)
      .attr("fill", "none")
      .attr("marker-end", "url(#arrow)")
      .attr("opacity", d => d.active ? 1 : 0.5);
    
    // Draw nodes
    const nodes = svg.append("g")
      .selectAll("g")
      .data(data.nodes)
      .enter().append("g")
      .attr("transform", d => `translate(${d.x},${d.y})`);
    
    nodes.append("circle")
      .attr("r", 30)
      .attr("fill", d => {
        switch(d.type) {
          case 'orchestrator': return '#FF0066';
          case 'planner': return '#FFB800';
          case 'executor': return '#00FF88';
          case 'service': return '#B794F4';
          default: return '#666';
        }
      });
    
    nodes.append("text")
      .text(d => d.label)
      .attr("text-anchor", "middle")
      .attr("dy", ".35em")
      .attr("fill", "white")
      .attr("font-weight", "bold");
    
  }, [data]);
  
  return (
    <svg ref={svgRef} width="100%" height="400" viewBox="0 0 800 400" />
  );
};
```

## Phase 6: Backend API Updates

### 6.1 Update WebSocket Server
Integrate all services:

```python
# src/webhook/server.py (updates)
class WebhookServer:
    def __init__(self):
        # ... existing init ...
        
        # Initialize new services
        self.agent_registry = AgentRegistry(self.message_bus, self.realtime_service)
        self.metrics_collector = MetricsCollector(self.realtime_service)
        self.queue_metrics = QueueMetrics(self.realtime_service)
        self.agent_graph = AgentGraph()
        self.flow_tracker = FlowTracker(self.agent_graph, self.realtime_service)
        
        # Setup event bridge with all services
        self.event_bridge = EventBridge(
            self.message_bus, 
            self.realtime_service,
            self.agent_registry,
            self.flow_tracker
        )
        
    async def startup(self):
        """Start background services."""
        await self.metrics_collector.start()
        
    async def get_agents(self) -> Dict[str, Any]:
        """Get real agent status from registry."""
        return {
            "agents": [
                asdict(agent) for agent in self.agent_registry.agents.values()
            ]
        }
```

## Phase 7: Testing & Monitoring

### 7.1 Test Harness
Create a test harness to simulate agent activity:

```python
# src/testing/dashboard_simulator.py
import asyncio
import random
from datetime import datetime

class DashboardSimulator:
    def __init__(self, registry, flow_tracker, queue_metrics):
        self.registry = registry
        self.flow_tracker = flow_tracker
        self.queue_metrics = queue_metrics
        self.agents = ['request_planner', 'code_planner', 'coding_agent']
        
    async def simulate_activity(self):
        """Simulate realistic agent activity."""
        while True:
            # Simulate a job flow
            job_id = f"job_{datetime.utcnow().timestamp()}"
            
            # Job enters queue
            await self.queue_metrics.job_enqueued(job_id, "code_generation")
            
            # RP picks it up
            await self.registry.update_agent_status(
                'request_planner', 
                AgentStatus.ACTIVE,
                f"Planning {job_id}"
            )
            await self.flow_tracker.track_message('user', 'request_planner', 'request')
            await asyncio.sleep(random.uniform(1, 3))
            
            # RP delegates to CP
            await self.flow_tracker.track_message('request_planner', 'code_planner', 'plan_request')
            await self.registry.update_agent_status('request_planner', AgentStatus.IDLE)
            
            # CP processes
            await self.registry.update_agent_status(
                'code_planner', 
                AgentStatus.ACTIVE,
                f"Creating plan for {job_id}"
            )
            await asyncio.sleep(random.uniform(2, 5))
            
            # CP assigns to CA
            await self.flow_tracker.track_message('code_planner', 'coding_agent', 'task_assignment')
            await self.registry.update_agent_status('code_planner', AgentStatus.IDLE)
            
            # CA executes
            await self.registry.update_agent_status(
                'coding_agent', 
                AgentStatus.ACTIVE,
                f"Coding {job_id}"
            )
            
            # Simulate some Git operations
            for _ in range(random.randint(1, 3)):
                await self.flow_tracker.track_message('coding_agent', 'git_operations', 'git_command')
                await asyncio.sleep(0.5)
            
            await asyncio.sleep(random.uniform(3, 8))
            
            # Complete
            await self.registry.update_agent_status('coding_agent', AgentStatus.IDLE)
            await self.queue_metrics.job_completed(job_id, True)
            
            # Wait before next job
            await asyncio.sleep(random.uniform(5, 15))
```

## Implementation Steps

1. **Week 1**: Implement Agent Registry and Status Tracking
   - Create agent registry service
   - Update base agent class
   - Test with mock agents

2. **Week 2**: Add System Metrics Collection
   - Implement metrics collector
   - Add GPU support
   - Create queue metrics tracker

3. **Week 3**: Build Agent Graph Visualization
   - Implement graph data structure
   - Create flow tracking
   - Build D3.js visualization

4. **Week 4**: Complete Integration
   - Wire up all services
   - Add log streaming
   - Test end-to-end

5. **Week 5**: Polish and Optimize
   - Performance optimization
   - Add historical data storage
   - Create admin controls

## Monitoring & Alerts

Add monitoring for the dashboard itself:

```python
# src/monitoring/dashboard_monitor.py
class DashboardMonitor:
    def __init__(self, realtime_service):
        self.realtime_service = realtime_service
        self.connection_health = {}
        
    async def check_health(self):
        """Monitor dashboard component health."""
        checks = {
            'websocket_connections': len(self.realtime_service.connection_manager.active_connections),
            'agent_registry': all(agent.last_heartbeat > datetime.utcnow() - timedelta(minutes=5) 
                                for agent in self.agent_registry.agents.values()),
            'metrics_collector': self.metrics_collector.is_running,
            'message_throughput': self.calculate_throughput()
        }
        
        return checks
```

This comprehensive plan provides a complete integration path from the current mock dashboard to a fully functional real-time monitoring system for your agent framework.