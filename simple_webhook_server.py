#!/usr/bin/env python3
"""
Simple webhook server for the dashboard frontend.
Provides the API endpoints needed by the frontend.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random

# Import our core modules
from src.core.agent_registry import AgentRegistry
from src.core.metrics_collector import MetricsCollector
from src.core.queue_metrics import QueueMetrics
from src.core.agent_graph import AgentGraph
from src.core.flow_tracker import FlowTracker
from src.core.realtime_service import RealtimeService
from src.core.historical_data import HistoricalDataService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Codeur Agent Dashboard API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
agent_registry = AgentRegistry()
metrics_collector = MetricsCollector()
queue_metrics = QueueMetrics()
agent_graph = AgentGraph()
flow_tracker = FlowTracker(agent_graph)
realtime_service = RealtimeService()
historical_service = HistoricalDataService()

# API Models
class ModelUpdateRequest(BaseModel):
    model: str

class JobResponse(BaseModel):
    job_id: str
    title: str
    status: str
    agent_type: Optional[str]
    created_at: str
    completed_at: Optional[str]
    duration: Optional[float]
    error_message: Optional[str]
    diff: Optional[str]
    plan: Optional[str]

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Agent endpoints
@app.get("/api/agents")
async def get_agents():
    """Get all registered agents with their current status."""
    agents = agent_registry.get_all_agents()
    return {"agents": agents}

@app.post("/api/agents/{agent_type}/model")
async def update_agent_model(agent_type: str, request: ModelUpdateRequest):
    """Update the model for a specific agent."""
    # In a real implementation, this would update the agent's configuration
    logger.info(f"Updating model for agent {agent_type} to {request.model}")
    return {"status": "success", "agent_type": agent_type, "model": request.model}

# Jobs endpoints
@app.get("/api/jobs")
async def get_jobs(limit: int = 50, offset: int = 0):
    """Get recent jobs with pagination."""
    # Mock data for demonstration
    jobs = []
    for i in range(10):
        job_id = f"job_{i + offset}"
        created_at = datetime.utcnow() - timedelta(minutes=random.randint(1, 60))
        completed_at = created_at + timedelta(seconds=random.randint(10, 300))
        
        jobs.append(JobResponse(
            job_id=job_id,
            title=f"Process user request #{i + offset}",
            status=random.choice(["completed", "failed", "processing", "pending"]),
            agent_type=random.choice(["request_planner", "code_writer", "code_tester"]),
            created_at=created_at.isoformat(),
            completed_at=completed_at.isoformat() if random.random() > 0.3 else None,
            duration=random.randint(10, 300) if random.random() > 0.3 else None,
            error_message="Task failed due to timeout" if random.random() < 0.1 else None,
            diff="+ Added new functionality\n- Removed old code" if random.random() > 0.5 else None,
            plan="1. Analyze request\n2. Generate code\n3. Test implementation" if random.random() > 0.5 else None
        ))
    
    return {"jobs": jobs, "total": 100, "limit": limit, "offset": offset}

@app.get("/api/jobs/{job_id}")
async def get_job_details(job_id: str):
    """Get detailed information about a specific job."""
    # Mock data
    return JobResponse(
        job_id=job_id,
        title=f"Process user request for {job_id}",
        status="completed",
        agent_type="request_planner",
        created_at=datetime.utcnow().isoformat(),
        completed_at=(datetime.utcnow() + timedelta(seconds=45)).isoformat(),
        duration=45.0,
        diff="+ Added authentication logic\n+ Added error handling\n- Removed debug statements",
        plan="1. Parse user requirements\n2. Design solution architecture\n3. Implement core logic\n4. Add tests"
    )

# Graph endpoints
@app.get("/api/graph")
async def get_graph_data():
    """Get the agent network graph data."""
    graph_data = agent_graph.get_graph_data()
    return graph_data

@app.get("/api/graph/stats")
async def get_graph_stats():
    """Get statistics about the agent network."""
    stats = agent_graph.get_stats()
    return stats

# Metrics endpoints
@app.get("/api/metrics/system")
async def get_system_metrics():
    """Get current system metrics."""
    metrics = await metrics_collector.get_metrics()
    return metrics

@app.get("/api/metrics/queue")
async def get_queue_metrics():
    """Get current queue metrics."""
    metrics = queue_metrics.get_metrics()
    return metrics

@app.get("/api/metrics/history/{metric_name}")
async def get_metric_history(
    metric_name: str,
    window: str = "5m",
    hours: int = 1
):
    """Get historical data for a specific metric."""
    # Generate mock historical data
    data_points = []
    now = datetime.utcnow()
    
    # Determine number of points based on window
    points = 60 if window == "1m" else 12 if window == "5m" else 4
    
    for i in range(points):
        timestamp = now - timedelta(minutes=i * (60 / points))
        value = random.uniform(20, 80) if "cpu" in metric_name else random.uniform(1, 8)
        data_points.append({
            "timestamp": timestamp.isoformat(),
            "value": value
        })
    
    data_points.reverse()
    return {"metric": metric_name, "window": window, "data": data_points}

@app.get("/api/metrics/summary")
async def get_metrics_summary(hours: int = 1):
    """Get a summary of all metrics for the specified time period."""
    return {
        "period_hours": hours,
        "summary": {
            "avg_cpu": random.uniform(30, 60),
            "max_cpu": random.uniform(70, 95),
            "avg_memory": random.uniform(2, 6),
            "max_memory": random.uniform(6, 8),
            "total_jobs": random.randint(50, 200),
            "success_rate": random.uniform(85, 98),
            "avg_job_duration": random.uniform(10, 60)
        }
    }

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    client_id = f"client_{id(websocket)}"
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive and send periodic updates
        while True:
            # Wait for messages or send periodic updates
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                data = json.loads(message)
                
                if data.get("type") == "subscribe":
                    topics = data.get("topics", [])
                    logger.info(f"Client {client_id} subscribed to: {topics}")
                    
                    # Send acknowledgment
                    await websocket.send_json({
                        "type": "subscription",
                        "status": "success",
                        "topics": topics,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Occasionally send random updates
                if random.random() < 0.3:
                    await websocket.send_json({
                        "type": "system_metrics",
                        "data": await metrics_collector.get_metrics(),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass

# Lifespan management
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Codeur Dashboard API...")
    
    # Register demo agents
    await agent_registry.register_agent("request_planner", "claude-3-sonnet", {"max_tokens": 4096})
    await agent_registry.register_agent("code_writer", "claude-3-opus", {"max_tokens": 8192})
    await agent_registry.register_agent("code_tester", "claude-3-haiku", {"max_tokens": 2048})
    await agent_registry.register_agent("code_reviewer", "claude-3-sonnet", {"max_tokens": 4096})
    await agent_registry.register_agent("doc_writer", "claude-3-haiku", {"max_tokens": 2048})
    
    # Start background tasks
    asyncio.create_task(agent_registry.start_health_monitor())
    asyncio.create_task(metrics_collector.start_collection())
    asyncio.create_task(flow_tracker.start_decay_task())
    
    logger.info("All services initialized successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Codeur Dashboard API...")
    await metrics_collector.stop_collection()
    await historical_service.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8088, log_level="info")