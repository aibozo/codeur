"""
Web UI command for starting the web dashboard.

This module provides commands to start the web interface.
"""

import click
import subprocess
import os
import sys
from pathlib import Path
from typing import Optional

from src.core.logging import get_logger
from src.core.settings import get_settings

logger = get_logger(__name__)


@click.group()
def web():
    """Manage the web dashboard interface."""
    pass


@web.command()
@click.option(
    '--backend/--no-backend',
    default=True,
    help='Also start the backend server'
)
@click.option(
    '--host',
    default='localhost',
    help='Frontend host (default: localhost)'
)
@click.option(
    '--port',
    type=int,
    default=5173,
    help='Frontend port (default: 5173 - Vite default)'
)
@click.option(
    '--backend-port',
    type=int,
    default=8088,
    help='Backend port (default: 8088)'
)
@click.option(
    '--open/--no-open',
    default=True,
    help='Open browser automatically'
)
def start(backend: bool, host: str, port: int, backend_port: int, open: bool):
    """Start the web dashboard."""
    project_root = Path(__file__).parent.parent.parent.parent
    frontend_dir = project_root / "frontend"
    
    if not frontend_dir.exists():
        click.echo("Error: Frontend directory not found. Run from project root.", err=True)
        sys.exit(1)
        
    # Check if node_modules exists
    if not (frontend_dir / "node_modules").exists():
        click.echo("Frontend dependencies not installed. Installing...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
    
    processes = []
    
    try:
        # Start backend if requested
        if backend:
            click.echo(f"Starting backend server on port {backend_port}...")
            settings = get_settings()
            
            # Enable webhook server
            os.environ["AGENT_WEBHOOK_WEBHOOK_ENABLED"] = "true"
            os.environ["AGENT_WEBHOOK_WEBHOOK_PORT"] = str(backend_port)
            
            # Create environment with webhook enabled
            backend_env = os.environ.copy()
            backend_env["AGENT_WEBHOOK_WEBHOOK_ENABLED"] = "true"
            backend_env["AGENT_WEBHOOK_WEBHOOK_PORT"] = str(backend_port)
            
            backend_proc = subprocess.Popen(
                [sys.executable, "-m", "src.webhook.server"],
                cwd=project_root,
                env=backend_env
            )
            processes.append(backend_proc)
            
            # Give backend time to start
            import time
            time.sleep(2)
        
        # Set API URL for frontend
        os.environ["VITE_API_URL"] = f"http://localhost:{backend_port}"
        
        # Start frontend
        click.echo(f"Starting frontend on http://{host}:{port}")
        frontend_cmd = ["npm", "run", "dev", "--", "--host", host, "--port", str(port)]
        
        if open:
            frontend_cmd.append("--open")
            
        frontend_proc = subprocess.Popen(frontend_cmd, cwd=frontend_dir)
        processes.append(frontend_proc)
        
        click.echo("\n" + "="*50)
        click.echo("Web Dashboard is running!")
        click.echo(f"  Frontend: http://{host}:{port}")
        if backend:
            click.echo(f"  Backend:  http://localhost:{backend_port}")
            click.echo(f"  WebSocket: ws://localhost:{backend_port}/ws")
        click.echo("\nPress Ctrl+C to stop all servers")
        click.echo("="*50 + "\n")
        
        # Wait for processes
        for proc in processes:
            proc.wait()
            
    except KeyboardInterrupt:
        click.echo("\n\nShutting down servers...")
        for proc in processes:
            proc.terminate()
            proc.wait()
        click.echo("Servers stopped.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        for proc in processes:
            proc.terminate()
        sys.exit(1)


@web.command()
def build():
    """Build the frontend for production."""
    project_root = Path(__file__).parent.parent.parent.parent
    frontend_dir = project_root / "frontend"
    
    if not frontend_dir.exists():
        click.echo("Error: Frontend directory not found.", err=True)
        sys.exit(1)
        
    # Check dependencies
    if not (frontend_dir / "node_modules").exists():
        click.echo("Installing dependencies...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
    
    # Build frontend
    click.echo("Building frontend for production...")
    subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)
    
    click.echo(f"\nFrontend built successfully!")
    click.echo(f"Output directory: {frontend_dir / 'dist'}")
    click.echo("\nThe webhook server will automatically serve the built files.")


@web.command()
def dev():
    """Start frontend in development mode only (no backend)."""
    project_root = Path(__file__).parent.parent.parent.parent
    frontend_dir = project_root / "frontend"
    
    if not frontend_dir.exists():
        click.echo("Error: Frontend directory not found.", err=True)
        sys.exit(1)
        
    click.echo("Starting frontend development server...")
    click.echo("Make sure the backend is running separately!")
    
    try:
        subprocess.run(["npm", "run", "dev"], cwd=frontend_dir, check=True)
    except KeyboardInterrupt:
        click.echo("\nFrontend stopped.")


if __name__ == "__main__":
    web()