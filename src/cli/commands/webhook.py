"""
CLI command for webhook server management.

This module provides commands to start and manage the webhook server
for remote task execution.
"""

import click
import asyncio
from pathlib import Path
from typing import Optional

from src.core.logging import setup_logging, get_logger
from src.core.settings import get_settings, load_settings
from src.webhook import create_webhook_server

logger = get_logger(__name__)


@click.group()
def webhook():
    """Manage webhook server for remote task execution."""
    pass


@webhook.command()
@click.option(
    '--host',
    default=None,
    help='Host to bind webhook server to'
)
@click.option(
    '--port',
    type=int,
    default=None,
    help='Port to bind webhook server to'
)
@click.option(
    '--config',
    type=click.Path(exists=True, path_type=Path),
    help='Path to configuration file'
)
def start(host: Optional[str], port: Optional[int], config: Optional[Path]):
    """Start the webhook server."""
    # Setup logging
    setup_logging()
    
    # Load settings
    if config:
        settings = load_settings(config)
    else:
        settings = get_settings()
    
    # Check if webhooks are enabled
    if not settings.webhook.webhook_enabled:
        click.echo("Webhooks are disabled in configuration. Enable with AGENT_WEBHOOK_ENABLED=true")
        return
    
    # Check for auth tokens if auth is enabled
    if settings.webhook.webhook_auth_enabled and not settings.webhook.webhook_auth_tokens:
        click.echo("Warning: Authentication is enabled but no tokens are configured!")
        click.echo("Set AGENT_WEBHOOK_AUTH_TOKENS environment variable")
    
    # Show configuration
    click.echo(f"Starting webhook server...")
    click.echo(f"Host: {host or settings.webhook.webhook_host}")
    click.echo(f"Port: {port or settings.webhook.webhook_port}")
    click.echo(f"Authentication: {'enabled' if settings.webhook.webhook_auth_enabled else 'disabled'}")
    click.echo(f"Rate limiting: {'enabled' if settings.webhook.rate_limit_enabled else 'disabled'}")
    
    # Show project mappings
    if settings.webhook.project_mappings:
        click.echo("\nProject mappings:")
        for source, path in settings.webhook.project_mappings.items():
            click.echo(f"  {source} -> {path}")
    else:
        click.echo("\nWarning: No project mappings configured!")
    
    try:
        # Create and run server
        server = create_webhook_server()
        server.run(host=host, port=port)
    except KeyboardInterrupt:
        click.echo("\nShutting down webhook server...")
    except Exception as e:
        click.echo(f"Error starting webhook server: {e}", err=True)
        raise


@webhook.command()
@click.option(
    '--output',
    type=click.Path(path_type=Path),
    default=Path('.agent-webhook.yaml'),
    help='Output file for example configuration'
)
def init(output: Path):
    """Generate example webhook configuration."""
    example_config = """# Agent Webhook Configuration Example
# Save this as .agent-webhook.yaml or set via environment variables

webhook:
  # Enable webhook server
  enabled: true
  
  # Server binding
  host: "0.0.0.0"
  port: 8080
  
  # Authentication
  auth_enabled: true
  auth_tokens:
    - "your-secret-token-here"
    - "another-token-for-different-service"
  
  # Optional: Webhook signing secret for signature verification
  # secret_key: "your-signing-secret"
  
  # Rate limiting
  rate_limit_enabled: true
  rate_limit_requests: 100
  rate_limit_window_seconds: 60
  
  # Project mappings
  # Map webhook sources to local project directories
  project_mappings:
    # Discord project IDs
    "my-project": "/path/to/my-project"
    "another-project": "/path/to/another-project"
    
    # GitHub repositories
    "myorg/myrepo": "/path/to/myrepo"
    "myorg/.*": "/path/to/org/repos"  # Pattern matching
    
    # Slack workspaces
    "workspace-1": "/path/to/workspace1-projects"

# Security settings
security:
  # Enable git sandboxing for webhook tasks
  sandbox_git_operations: true
  
  # Directory for git sandbox operations
  git_sandbox_dir: "/tmp/agent-sandbox"

# Example environment variables:
# AGENT_WEBHOOK_ENABLED=true
# AGENT_WEBHOOK_PORT=8080
# AGENT_WEBHOOK_AUTH_TOKENS=["token1", "token2"]
# AGENT_WEBHOOK_PROJECT_MAPPINGS='{"project1": "/path/to/project1"}'
"""
    
    # Write example config
    output.write_text(example_config)
    click.echo(f"Created example webhook configuration at: {output}")
    click.echo("\nTo use this configuration:")
    click.echo(f"1. Edit {output} with your settings")
    click.echo(f"2. Run: agent webhook start --config {output}")


@webhook.command()
@click.argument('token', required=False)
def generate_token(token: Optional[str]):
    """Generate a secure webhook token."""
    import secrets
    
    if token:
        # Hash provided token for storage
        import hashlib
        hashed = hashlib.sha256(token.encode()).hexdigest()
        click.echo(f"Token hash for configuration: {hashed}")
    else:
        # Generate new token
        new_token = secrets.token_urlsafe(32)
        click.echo(f"Generated token: {new_token}")
        click.echo("\nAdd this to your configuration:")
        click.echo(f'auth_tokens: ["{new_token}"]')


@webhook.command()
@click.option(
    '--source',
    type=click.Choice(['discord', 'github', 'slack']),
    required=True,
    help='Webhook source type'
)
@click.option(
    '--payload',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to JSON payload file'
)
@click.option(
    '--project',
    required=True,
    help='Project identifier'
)
def test(source: str, payload: Path, project: str):
    """Test webhook handling with a sample payload."""
    import json
    import httpx
    
    # Load payload
    with open(payload) as f:
        payload_data = json.load(f)
    
    # Get settings
    settings = get_settings()
    
    # Build webhook URL
    host = settings.webhook.webhook_host
    port = settings.webhook.webhook_port
    url = f"http://{host}:{port}/webhook"
    
    # Prepare request
    webhook_data = {
        "source": source,
        "event_type": "test",
        "payload": payload_data
    }
    
    headers = {}
    if settings.webhook.webhook_auth_enabled and settings.webhook.webhook_auth_tokens:
        headers["Authorization"] = f"Bearer {settings.webhook.webhook_auth_tokens[0].get_secret_value()}"
    
    # Send request
    click.echo(f"Sending test webhook to {url}")
    
    try:
        response = httpx.post(url, json=webhook_data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        click.echo(f"Success: {result['message']}")
        if result.get('task_id'):
            click.echo(f"Task ID: {result['task_id']}")
            
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        if hasattr(e, 'response') and e.response is not None:
            click.echo(f"Response: {e.response.text}", err=True)