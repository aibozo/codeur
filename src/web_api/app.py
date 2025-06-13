"""
FastAPI application for the agent system web interface.

Provides REST and WebSocket endpoints for:
- Interacting with the request planner
- Real-time system metrics
- Task progress monitoring
- Agent state visualization
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.request_planner import RequestPlanner
from src.proto_gen import messages_pb2
from src.core.message_bus import MessageBus
from src.core.logging import setup_logging

# Setup logging
setup_logging(logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Agent System API", version="1.0.0")

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
active_connections: List[WebSocket] = []
message_bus = MessageBus()
request_planner = None
system_metrics = {
    "start_time": datetime.now(),
    "total_requests": 0,
    "active_agents": 0,
    "completed_tasks": 0,
    "failed_tasks": 0,
    "average_task_time": 0,
}


class ChatMessage(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class SystemStatus(BaseModel):
    healthy: bool
    uptime_seconds: float
    metrics: Dict[str, Any]
    active_tasks: List[Dict[str, Any]]
    agent_states: Dict[str, str]


class TaskProgress(BaseModel):
    task_id: str
    progress: float
    status: str
    current_step: str
    logs: List[str]


@app.on_event("startup")
async def startup_event():
    """Initialize the system on startup."""
    global request_planner
    
    logger.info("Starting Agent System API...")
    
    # Initialize request planner
    request_planner = RequestPlanner(message_bus=message_bus)
    
    # Start background tasks
    asyncio.create_task(metrics_updater())
    asyncio.create_task(event_broadcaster())
    
    logger.info("Agent System API started successfully")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Agent System API", "version": "1.0.0"}


@app.get("/api/status", response_model=SystemStatus)
async def get_status():
    """Get current system status and metrics."""
    uptime = (datetime.now() - system_metrics["start_time"]).total_seconds()
    
    # Get active tasks from request planner
    active_tasks = []
    if request_planner and hasattr(request_planner, 'active_requests'):
        for req_id, req_info in request_planner.active_requests.items():
            active_tasks.append({
                "id": req_id,
                "type": req_info.get("type", "unknown"),
                "status": req_info.get("status", "active"),
                "progress": req_info.get("progress", 0),
                "started_at": req_info.get("started_at", ""),
            })
    
    # Get agent states
    agent_states = {}
    if request_planner:
        # This would query actual agent states
        agent_states = {
            "code_planner": "idle",
            "coding_agent": "active",
            "request_planner": "active",
            "rag_service": "healthy",
        }
    
    return SystemStatus(
        healthy=True,
        uptime_seconds=uptime,
        metrics=system_metrics,
        active_tasks=active_tasks,
        agent_states=agent_states
    )


@app.post("/api/chat")
async def chat_with_planner(message: ChatMessage):
    """Chat with the request planner."""
    global system_metrics
    system_metrics["total_requests"] += 1
    
    if not request_planner:
        raise HTTPException(status_code=503, detail="Request planner not initialized")
    
    try:
        # Create a user request
        user_request = messages_pb2.UserRequest()
        user_request.id = f"req_{datetime.now().timestamp()}"
        user_request.goal = message.message
        user_request.timestamp.GetCurrentTime()
        
        if message.context:
            for key, value in message.context.items():
                user_request.context[key] = str(value)
        
        # Process with request planner
        response = await request_planner.process_request_async(user_request)
        
        # Broadcast update to all connected clients
        await broadcast_update({
            "type": "new_request",
            "request_id": user_request.id,
            "goal": user_request.goal,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "request_id": user_request.id,
            "response": response.reasoning if hasattr(response, 'reasoning') else "Processing...",
            "status": "accepted"
        }
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Agent System",
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive and handle messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif message.get("type") == "subscribe":
                    # Handle subscription to specific events
                    pass
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
                
    finally:
        active_connections.remove(websocket)


async def broadcast_update(update: Dict[str, Any]):
    """Broadcast update to all connected WebSocket clients."""
    disconnected = []
    
    for connection in active_connections:
        try:
            await connection.send_json(update)
        except:
            disconnected.append(connection)
    
    # Clean up disconnected clients
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


async def metrics_updater():
    """Background task to update system metrics."""
    while True:
        try:
            # Update metrics
            update = {
                "type": "metrics_update",
                "timestamp": datetime.now().isoformat(),
                "metrics": {
                    "cpu_usage": get_cpu_usage(),
                    "memory_usage": get_memory_usage(),
                    "active_agents": system_metrics["active_agents"],
                    "queue_length": get_queue_length(),
                }
            }
            
            await broadcast_update(update)
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
        
        await asyncio.sleep(5)  # Update every 5 seconds


async def event_broadcaster():
    """Background task to broadcast system events."""
    # Subscribe to message bus events
    async def handle_event(event):
        try:
            # Convert protobuf events to JSON
            event_data = {
                "type": "system_event",
                "event_type": type(event).__name__,
                "timestamp": datetime.now().isoformat(),
            }
            
            # Add event-specific data
            if hasattr(event, 'task_id'):
                event_data["task_id"] = event.task_id
            if hasattr(event, 'status'):
                event_data["status"] = event.status
            if hasattr(event, 'progress'):
                event_data["progress"] = event.progress
            
            await broadcast_update(event_data)
            
        except Exception as e:
            logger.error(f"Error broadcasting event: {e}")
    
    # Subscribe to various event types
    message_bus.subscribe(messages_pb2.TaskCompleted, handle_event)
    message_bus.subscribe(messages_pb2.TaskFailed, handle_event)
    message_bus.subscribe(messages_pb2.AgentStateChange, handle_event)


# Utility functions
def get_cpu_usage() -> float:
    """Get current CPU usage percentage."""
    try:
        import psutil
        return psutil.cpu_percent(interval=0.1)
    except:
        return 0.0


def get_memory_usage() -> float:
    """Get current memory usage percentage."""
    try:
        import psutil
        return psutil.virtual_memory().percent
    except:
        return 0.0


def get_queue_length() -> int:
    """Get current task queue length."""
    # This would query actual queue length
    return 0


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)