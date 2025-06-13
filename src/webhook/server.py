"""
Webhook server implementation using FastAPI.

This module provides the main webhook server that receives and
processes incoming webhook requests.
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from src.core.logging import get_logger, set_request_id
from src.core.settings import get_settings
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
        self.app = self._create_app()
        self.handlers = {}
        
        # Register handlers
        self._register_handlers()
    
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
        
        yield
        
        # Shutdown
        logger.info("Shutting down webhook server")
        await self.executor.stop()
    
    def _create_app(self) -> FastAPI:
        """Create FastAPI application."""
        app = FastAPI(
            title="Agent Webhook Server",
            description="Webhook server for remote task execution",
            version="1.0.0",
            lifespan=self.lifespan
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


def create_webhook_server() -> WebhookServer:
    """Create and configure webhook server."""
    settings = get_settings()
    
    if not settings.webhook.webhook_enabled:
        raise RuntimeError("Webhook server is disabled in configuration")
    
    return WebhookServer()