"""
Webhook system for remote task execution.

This module provides webhook endpoints for receiving tasks from
external services like Discord, GitHub, etc.
"""

from .server import WebhookServer, create_webhook_server
from .handlers import WebhookHandler, DiscordHandler, GitHubHandler
from .security import WebhookSecurity
from .executor import TaskExecutor

__all__ = [
    'WebhookServer',
    'create_webhook_server',
    'WebhookHandler',
    'DiscordHandler',
    'GitHubHandler',
    'WebhookSecurity',
    'TaskExecutor',
]