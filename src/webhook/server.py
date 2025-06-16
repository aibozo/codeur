"""
Webhook server implementation using FastAPI.

This module provides the main webhook server that receives and
processes incoming webhook requests.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends, Header, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from src.core.logging import get_logger, set_request_id
from src.core.settings import get_settings
from src.core.message_bus import MessageBus
from src.core.realtime import RealtimeService
from src.core.event_bridge import EventBridge
from src.core.agent_registry import AgentRegistry, AgentStatus
from src.core.metrics_collector import MetricsCollector
from src.core.queue_metrics import QueueMetrics
from src.core.agent_graph import AgentGraph
from src.core.flow_tracker import FlowTracker
from src.core.log_streamer import setup_streaming_logs
from src.core.historical_data import get_historical_service, HistoricalDataService
from src.core.dashboard_optimizer import DashboardOptimizer, cached_endpoint
from src.webhook.security import WebhookSecurity
from src.webhook.handlers import create_handler
from src.webhook.executor import TaskExecutor

logger = get_logger(__name__)


class WebhookRequest(BaseModel):
    """Base webhook request model."""
    source: str  # discord, github, slack, etc.
    event_type: str
    payload: Dict[str, Any]
    signature: Optional[str] = None


class WebhookResponse(BaseModel):
    """Webhook response model."""
    success: bool
    message: str
    task_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class WebhookServer:
    """Main webhook server implementation."""
    
    def __init__(self):
        """Initialize webhook server."""
        self.settings = get_settings()
        self.security = WebhookSecurity()
        self.executor = TaskExecutor()
        self.message_bus = MessageBus()
        self.realtime_service = RealtimeService(self.message_bus)
        self.agent_registry = AgentRegistry(self.message_bus, self.realtime_service)
        self.metrics_collector = MetricsCollector(self.realtime_service)
        self.queue_metrics = QueueMetrics(self.realtime_service)
        self.agent_graph = AgentGraph()
        self.flow_tracker = FlowTracker(self.agent_graph, self.realtime_service)
        self.event_bridge = EventBridge(
            self.message_bus, 
            self.realtime_service,
            self.agent_registry,
            self.flow_tracker
        )
        self.dashboard_optimizer = DashboardOptimizer()
        self.historical_service: Optional[HistoricalDataService] = None
        self.app = self._create_app()
        self.handlers = {}
        
        # Register handlers
        self._register_handlers()
        
        # Default agents will be registered during startup
    
    def _register_handlers(self):
        """Register webhook handlers."""
        # Auto-register handlers based on configuration
        if self.settings.webhook.project_mappings:
            for source in self.settings.webhook.project_mappings:
                handler = create_handler(source)
                if handler:
                    self.handlers[source] = handler
                    logger.info(f"Registered handler for {source}")
    
    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Manage server lifecycle."""
        # Startup
        logger.info("Starting webhook server")
        await self.executor.start()
        await self.realtime_service.initialize()
        await self.agent_registry.start()
        await self.metrics_collector.start()
        await self.queue_metrics.start()
        await self.flow_tracker.start()
        
        # Register default agents
        await self._register_default_agents()
        
        # Set up log streaming
        setup_streaming_logs(self.realtime_service, min_level=logging.INFO)
        logger.info("Log streaming enabled")
        
        # Initialize historical data service
        self.historical_service = await get_historical_service()
        
        # Start optimizer
        await self.dashboard_optimizer.start(self._handle_buffered_metrics)
        
        yield
        
        # Shutdown
        logger.info("Shutting down webhook server")
        await self.executor.stop()
        await self.agent_registry.stop()
        await self.metrics_collector.stop()
        await self.queue_metrics.stop()
        await self.flow_tracker.stop()
        await self.dashboard_optimizer.stop()
        if self.historical_service:
            await self.historical_service.stop()
        await self.realtime_service.shutdown()
    
    def _create_app(self) -> FastAPI:
        """Create FastAPI application."""
        app = FastAPI(
            title="Agent Webhook Server",
            description="Webhook server for remote task execution",
            version="1.0.0",
            lifespan=self.lifespan
        )
        
        # Add CORS middleware for frontend development
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default ports
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add middleware
        @app.middleware("http")
        async def add_request_id(request: Request, call_next):
            """Add request ID to context."""
            request_id = request.headers.get("X-Request-ID")
            set_request_id(request_id)
            
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id or ""
            return response
        
        # Add routes
        app.add_api_route(
            "/webhook",
            self.handle_webhook,
            methods=["POST"],
            response_model=WebhookResponse,
            summary="Handle incoming webhooks"
        )
        
        app.add_api_route(
            "/health",
            self.health_check,
            methods=["GET"],
            summary="Health check endpoint"
        )
        
        app.add_api_route(
            "/status/{task_id}",
            self.get_task_status,
            methods=["GET"],
            summary="Get task status"
        )
        
        # Add WebSocket endpoint
        app.add_api_websocket_route(
            "/ws",
            self.websocket_endpoint
        )
        
        # Add API endpoints for frontend
        app.add_api_route(
            "/api/agents",
            self.get_agents,
            methods=["GET"],
            summary="Get all agents status"
        )
        
        app.add_api_route(
            "/api/agents/{agent_type}/model",
            self.set_agent_model,
            methods=["POST"],
            summary="Set model for specific agent type"
        )
        
        app.add_api_route(
            "/api/jobs",
            self.get_jobs,
            methods=["GET"],
            summary="Get job history"
        )
        
        app.add_api_route(
            "/api/jobs/{job_id}",
            self.get_job_details,
            methods=["GET"],
            summary="Get job details including plan and diff"
        )
        
        app.add_api_route(
            "/api/metrics/system",
            self.get_system_metrics,
            methods=["GET"],
            summary="Get current system metrics"
        )
        
        app.add_api_route(
            "/api/metrics/queue",
            self.get_queue_metrics,
            methods=["GET"],
            summary="Get queue metrics and statistics"
        )
        
        app.add_api_route(
            "/api/graph",
            self.get_graph_data,
            methods=["GET"],
            summary="Get agent graph structure and current flows"
        )
        
        app.add_api_route(
            "/api/graph/stats",
            self.get_graph_stats,
            methods=["GET"],
            summary="Get graph statistics"
        )
        
        app.add_api_route(
            "/api/metrics/history/{metric_name}",
            self.get_metric_history,
            methods=["GET"],
            summary="Get historical metric data"
        )
        
        app.add_api_route(
            "/api/metrics/summary",
            self.get_metrics_summary,
            methods=["GET"],
            summary="Get system metrics summary"
        )
        
        # Serve static files if frontend is built
        frontend_dist = Path("frontend/dist")
        if frontend_dist.exists():
            app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
        
        return app
    
    async def handle_webhook(
        self,
        request: Request,
        webhook_req: WebhookRequest,
        authorization: Optional[str] = Header(None)
    ) -> WebhookResponse:
        """
        Handle incoming webhook request.
        
        Args:
            request: FastAPI request object
            webhook_req: Parsed webhook request
            authorization: Authorization header
            
        Returns:
            WebhookResponse with task details
        """
        try:
            # Verify authentication
            if not await self.security.verify_request(
                request,
                webhook_req,
                authorization
            ):
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            # Get handler for source
            handler = self.handlers.get(webhook_req.source)
            if not handler:
                raise HTTPException(
                    status_code=400,
                    detail=f"No handler registered for source: {webhook_req.source}"
                )
            
            # Process webhook
            task = await handler.process_webhook(webhook_req)
            
            if not task:
                return WebhookResponse(
                    success=False,
                    message="Webhook processed but no task created"
                )
            
            # Execute task
            task_id = await self.executor.submit_task(task)
            
            return WebhookResponse(
                success=True,
                message=f"Task submitted successfully",
                task_id=task_id,
                details={
                    "project": task.project_path,
                    "command": task.command,
                    "source": webhook_req.source
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "handlers": list(self.handlers.keys()),
            "executor": {
                "active_tasks": self.executor.active_task_count(),
                "completed_tasks": self.executor.completed_task_count()
            }
        }
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a specific task."""
        status = await self.executor.get_task_status(task_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return status
    
    async def websocket_endpoint(self, websocket: WebSocket):
        """Handle WebSocket connections."""
        await self.realtime_service.handle_websocket(websocket)
        
    async def get_agents(self) -> Dict[str, Any]:
        """Get status of all agents from the registry."""
        agents = await self.agent_registry.get_all_agents()
        return {
            "agents": [agent.to_dict() for agent in agents]
        }
        
    async def set_agent_model(self, agent_type: str, request: Request) -> Dict[str, Any]:
        """Set model for a specific agent type."""
        data = await request.json()
        model = data.get("model")
        
        if not model:
            raise HTTPException(status_code=400, detail="Model name required")
            
        # Update model in registry
        await self.agent_registry.update_agent_model(agent_type, model)
        
        return {"success": True, "agent_type": agent_type, "model": model}
        
    async def get_jobs(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Get job history with pagination."""
        # Get job history from queue metrics
        jobs = self.queue_metrics.get_job_history(limit)
        return {
            "jobs": jobs,
            "total": len(jobs),
            "limit": limit,
            "offset": offset
        }
        
    async def get_job_details(self, job_id: str) -> Dict[str, Any]:
        """Get detailed job information."""
        job_state = await self.realtime_service.get_job_state(job_id)
        
        if not job_state:
            raise HTTPException(status_code=404, detail="Job not found")
            
        return job_state
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        return self.metrics_collector.get_last_metrics()
    
    async def get_queue_metrics(self) -> Dict[str, Any]:
        """Get queue metrics and statistics."""
        return self.queue_metrics.get_metrics()
    
    async def get_graph_data(self) -> Dict[str, Any]:
        """Get agent graph structure with current flows."""
        # Get active flows from flow tracker
        active_flows = dict(self.flow_tracker.active_flows)
        
        # Get graph data with flows
        graph_data = self.agent_graph.get_graph_data(active_flows)
        
        # Add flow statistics
        graph_data['stats'] = await self.flow_tracker._calculate_flow_stats()
        
        return graph_data
    
    async def get_graph_stats(self) -> Dict[str, Any]:
        """Get detailed graph statistics."""
        return {
            'graph': self.agent_graph.get_graph_stats(),
            'flows': {
                'total_messages': self.flow_tracker.total_messages,
                'active_flows': len(self.flow_tracker.active_flows),
                'edge_counts': dict(self.flow_tracker.edge_message_counts),
                'agent_counts': dict(self.flow_tracker.agent_message_counts)
            }
        }
    
    @cached_endpoint(ttl=30)
    async def get_metric_history(self, metric_name: str, window: str = "5m",
                               hours: int = 1) -> Dict[str, Any]:
        """Get historical data for a specific metric."""
        if not self.historical_service:
            return {'error': 'Historical data service not available'}
        
        from src.core.historical_data import TimeWindow
        
        # Map window string to enum
        window_map = {
            "1m": TimeWindow.MINUTE_1,
            "5m": TimeWindow.MINUTE_5,
            "15m": TimeWindow.MINUTE_15,
            "1h": TimeWindow.HOUR_1,
            "4h": TimeWindow.HOUR_4,
            "1d": TimeWindow.DAY_1,
            "1w": TimeWindow.WEEK_1
        }
        
        time_window = window_map.get(window, TimeWindow.MINUTE_5)
        
        # Get historical data
        data = await self.historical_service.get_metric_history(
            metric_name,
            time_window
        )
        
        # Optimize data for transmission
        optimized_data = self.dashboard_optimizer.aggregator.downsample_timeseries(
            [{'timestamp': p.timestamp.isoformat(), 'value': p.value} 
             for p in data.points],
            max_points=200
        )
        
        return {
            'metric': metric_name,
            'window': window,
            'data': optimized_data
        }
    
    @cached_endpoint(ttl=60)
    async def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get system metrics summary."""
        if not self.historical_service:
            return {'error': 'Historical data service not available'}
        
        summary = await self.historical_service.get_system_metrics_summary(hours)
        
        # Add current values
        current_metrics = self.metrics_collector.get_last_metrics()
        if current_metrics:
            summary['current'] = {
                'cpu': current_metrics.get('cpu', {}).get('usage_percent', 0),
                'memory': current_metrics.get('memory', {}).get('percent', 0),
                'process_memory': current_metrics.get('process', {}).get('memory_mb', 0)
            }
        
        return summary
    
    async def _handle_buffered_metrics(self, metrics: Dict[str, List]) -> None:
        """Handle buffered metrics from optimizer."""
        # Store in historical service
        if self.historical_service:
            for metric_type, entries in metrics.items():
                for entry in entries:
                    await self.historical_service.record_metric(
                        metric_type,
                        entry['data'].get('value', 0),
                        entry['data']
                    )
    
    def run(self, host: Optional[str] = None, port: Optional[int] = None):
        """Run the webhook server."""
        host = host or self.settings.webhook.webhook_host
        port = port or self.settings.webhook.webhook_port
        
        logger.info(f"Starting webhook server on {host}:{port}")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_config={
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    },
                },
                "handlers": {
                    "default": {
                        "formatter": "default",
                        "class": "logging.StreamHandler",
                        "stream": "ext://sys.stdout",
                    },
                },
                "root": {
                    "level": "INFO",
                    "handlers": ["default"],
                },
            }
        )
        
    async def _register_default_agents(self):
        """Register default agents with the system."""
        default_agents = [
            {
                'type': 'request_planner',
                'model': self.settings.llm.default_model or 'gpt-4',
                'capabilities': ['planning', 'orchestration', 'task_decomposition']
            },
            {
                'type': 'code_planner',
                'model': self.settings.llm.default_model or 'gpt-4',
                'capabilities': ['code_analysis', 'implementation_planning', 'architecture_design']
            },
            {
                'type': 'coding_agent',
                'model': self.settings.llm.default_model or 'gpt-4',
                'capabilities': ['code_generation', 'debugging', 'refactoring', 'testing']
            },
            {
                'type': 'rag_service',
                'model': 'embedding-model',
                'capabilities': ['semantic_search', 'code_retrieval', 'documentation_lookup']
            },
            {
                'type': 'git_operations',
                'model': 'none',
                'capabilities': ['git_commands', 'version_control', 'diff_analysis']
            }
        ]
        
        for agent_config in default_agents:
            try:
                await self.agent_registry.register_agent(
                    agent_type=agent_config['type'],
                    model=agent_config['model'],
                    capabilities=agent_config['capabilities']
                )
            except Exception as e:
                logger.error(f"Failed to register agent {agent_config['type']}: {e}")


def create_webhook_server() -> WebhookServer:
    """Create and configure webhook server."""
    settings = get_settings()
    
    if not settings.webhook.webhook_enabled:
        raise RuntimeError("Webhook server is disabled in configuration")
    
    return WebhookServer()


if __name__ == "__main__":
    """Run the webhook server when executed as a module."""
    import os
    
    # Ensure webhook is enabled
    os.environ["AGENT_WEBHOOK_ENABLED"] = "true"
    
    # Create and run server
    server = create_webhook_server()
    server.run()