"""
Security module for webhook authentication and authorization.

This module provides security features including signature verification,
rate limiting, and token authentication.
"""

import hmac
import hashlib
import time
from typing import Optional, Dict, Any, List
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

from fastapi import Request, HTTPException
from pydantic import SecretStr

from src.core.logging import get_logger
from src.core.settings import get_settings

logger = get_logger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, requests: int, window_seconds: int):
        """
        Initialize rate limiter.
        
        Args:
            requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.requests = requests
        self.window_seconds = window_seconds
        self.clients = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def check_rate_limit(self, client_id: str) -> bool:
        """
        Check if client has exceeded rate limit.
        
        Args:
            client_id: Client identifier (IP, token, etc.)
            
        Returns:
            True if within limits, False otherwise
        """
        async with self.lock:
            now = time.time()
            
            # Clean old entries
            self.clients[client_id] = [
                timestamp for timestamp in self.clients[client_id]
                if now - timestamp < self.window_seconds
            ]
            
            # Check limit
            if len(self.clients[client_id]) >= self.requests:
                return False
            
            # Add new request
            self.clients[client_id].append(now)
            return True
    
    async def cleanup(self):
        """Periodic cleanup of old entries."""
        while True:
            await asyncio.sleep(self.window_seconds)
            async with self.lock:
                now = time.time()
                for client_id in list(self.clients.keys()):
                    self.clients[client_id] = [
                        timestamp for timestamp in self.clients[client_id]
                        if now - timestamp < self.window_seconds
                    ]
                    if not self.clients[client_id]:
                        del self.clients[client_id]


class WebhookSecurity:
    """Handles webhook security and authentication."""
    
    def __init__(self):
        """Initialize webhook security."""
        self.settings = get_settings()
        self.rate_limiter = None
        
        if self.settings.webhook.rate_limit_enabled:
            self.rate_limiter = RateLimiter(
                self.settings.webhook.rate_limit_requests,
                self.settings.webhook.rate_limit_window_seconds
            )
            
            # Cleanup task will be started when event loop is available
    
    async def verify_request(
        self,
        request: Request,
        webhook_req: Any,
        authorization: Optional[str] = None
    ) -> bool:
        """
        Verify webhook request authentication and authorization.
        
        Args:
            request: FastAPI request
            webhook_req: Webhook request data
            authorization: Authorization header
            
        Returns:
            True if authorized, False otherwise
        """
        # Check rate limiting
        if self.rate_limiter:
            client_id = self._get_client_id(request)
            if not await self.rate_limiter.check_rate_limit(client_id):
                logger.warning(f"Rate limit exceeded for {client_id}")
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Check authentication
        if self.settings.webhook.webhook_auth_enabled:
            if not await self._verify_auth(request, webhook_req, authorization):
                return False
        
        # Verify signature if provided
        if webhook_req.signature and self.settings.webhook.webhook_secret_key:
            if not self._verify_signature(webhook_req):
                logger.warning("Invalid webhook signature")
                return False
        
        return True
    
    async def _verify_auth(
        self,
        request: Request,
        webhook_req: Any,
        authorization: Optional[str]
    ) -> bool:
        """Verify authentication token."""
        if not authorization:
            logger.warning("Missing authorization header")
            return False
        
        # Extract token (Bearer token)
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
        
        # Check against configured tokens
        valid_tokens = [
            t.get_secret_value() for t in self.settings.webhook.webhook_auth_tokens
        ]
        
        if not valid_tokens:
            logger.warning("No auth tokens configured")
            return False
        
        if token not in valid_tokens:
            logger.warning("Invalid auth token")
            return False
        
        return True
    
    def _verify_signature(self, webhook_req: Any) -> bool:
        """
        Verify webhook signature.
        
        Args:
            webhook_req: Webhook request with signature
            
        Returns:
            True if signature is valid
        """
        if not self.settings.webhook.webhook_secret_key:
            return True
        
        secret = self.settings.webhook.webhook_secret_key.get_secret_value()
        
        # Different signature verification based on source
        if webhook_req.source == "github":
            return self._verify_github_signature(
                webhook_req.payload,
                webhook_req.signature,
                secret
            )
        elif webhook_req.source == "discord":
            return self._verify_discord_signature(
                webhook_req.payload,
                webhook_req.signature,
                secret
            )
        else:
            # Generic HMAC verification
            return self._verify_hmac_signature(
                webhook_req.payload,
                webhook_req.signature,
                secret
            )
    
    def _verify_github_signature(
        self,
        payload: Dict[str, Any],
        signature: str,
        secret: str
    ) -> bool:
        """Verify GitHub webhook signature."""
        import json
        
        # GitHub uses HMAC-SHA256
        if not signature.startswith("sha256="):
            return False
        
        expected_signature = signature[7:]  # Remove "sha256=" prefix
        
        # Calculate HMAC
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        calculated = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(calculated, expected_signature)
    
    def _verify_discord_signature(
        self,
        payload: Dict[str, Any],
        signature: str,
        secret: str
    ) -> bool:
        """Verify Discord webhook signature."""
        # Discord doesn't use signatures by default
        # This is a placeholder for custom Discord bot implementations
        return True
    
    def _verify_hmac_signature(
        self,
        payload: Dict[str, Any],
        signature: str,
        secret: str
    ) -> bool:
        """Generic HMAC signature verification."""
        import json
        
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        calculated = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(calculated, signature)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get real IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get first IP in chain
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"