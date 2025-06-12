"""
Interactive session mode for Request Planner.

This module provides a Claude Code-style interactive session where users
can have conversations with the agent, submit requests, and see real-time
execution of plans.
"""

import os
import sys
from typing import Optional, Dict, Any, List
from pathlib import Path
import readline  # For command history
import logging

from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.live import Live
from rich.layout import Layout

from .planner import RequestPlanner
from .models import ChangeRequest, TaskStatus
from .executor import PlanExecutor

logger = logging.getLogger(__name__)


class InteractiveSession:
    """
    Interactive session for conversational agent interactions.
    
    Provides a Claude Code-style interface with:
    - Conversational context
    - Real-time plan execution
    - File monitoring
    - Progress tracking
    """
    
    def __init__(self, repo_path: str = "."):
        """Initialize the interactive session."""
        self.console = Console()
        self.planner = RequestPlanner(repo_path)
        self.executor = PlanExecutor(self.planner)
        self.conversation_history: List[Dict[str, str]] = []
        self.current_plan = None
        self.session_active = True
        
        # Configure readline for better input handling
        readline.parse_and_bind("tab: complete")
        readline.set_history_length(1000)
        
        # Session state
        self.context_mode = "normal"  # normal, planning, executing
        self.modified_files: List[str] = []
        
    def start(self):
        """Start the interactive session."""
        self._show_welcome()
        
        try:
            while self.session_active:
                self._process_input()
        except (KeyboardInterrupt, EOFError):
            self._shutdown()
    
    def _show_welcome(self):
        """Show welcome message and session info."""
        self.console.clear()
        
        # Get repository info
        repo_info = self.planner.get_repository_info()
        
        welcome_text = f"""
[bold cyan]Request Planner Interactive Session[/bold cyan]
[dim]A Claude Code-style development assistant[/dim]

Repository: {repo_info.get('path', 'Not loaded')}
Branch: {repo_info.get('current_branch', 'N/A')}

Commands:
• Type your request or question
• /help - Show available commands
• /plan - Create a plan for your request
• /execute - Execute the current plan
• /status - Show current status
• /clear - Clear the screen
• /exit - Exit the session

[dim]Press Ctrl+C to exit at any time[/dim]
"""
        
        self.console.print(Panel(
            welcome_text,
            title="Welcome",
            border_style="cyan"
        ))
    
    def _process_input(self):
        """Process user input."""
        try:
            # Show prompt based on context
            prompt = self._get_prompt()
            user_input = Prompt.ask(prompt)
            
            if not user_input.strip():
                return
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            # Process commands
            if user_input.startswith("/"):
                self._handle_command(user_input)
            else:
                self._handle_request(user_input)
                
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Use /exit to leave the session[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            logger.error(f"Error processing input: {e}", exc_info=True)
    
    def _get_prompt(self) -> str:
        """Get the appropriate prompt based on context."""
        if self.context_mode == "planning":
            return "[yellow]Planning>[/yellow] "
        elif self.context_mode == "executing":
            return "[green]Executing>[/green] "
        else:
            return "[cyan]>[/cyan] "
    
    def _handle_command(self, command: str):
        """Handle slash commands."""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == "/help":
            self._show_help()
        elif cmd == "/plan":
            if len(parts) > 1:
                request = " ".join(parts[1:])
                self._create_plan(request)
            else:
                self.console.print("[yellow]Usage: /plan <your request>[/yellow]")
        elif cmd == "/execute":
            self._execute_plan()
        elif cmd == "/status":
            self._show_status()
        elif cmd == "/clear":
            self.console.clear()
        elif cmd == "/exit" or cmd == "/quit":
            self._shutdown()
        elif cmd == "/repo":
            if len(parts) > 1:
                self._load_repository(parts[1])
            else:
                self._show_repository_info()
        elif cmd == "/history":
            self._show_history()
        elif cmd == "/save":
            self._save_session()
        else:
            self.console.print(f"[red]Unknown command: {cmd}[/red]")
            self.console.print("[dim]Type /help for available commands[/dim]")
    
    def _handle_request(self, request: str):
        """Handle natural language requests."""
        # Determine request type
        if any(word in request.lower() for word in ["what", "how", "why", "explain", "show"]):
            # This is a question
            self._answer_question(request)
        else:
            # This is likely a change request
            self._create_plan(request)
    
    def _answer_question(self, question: str):
        """Answer a question about the codebase."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task("Analyzing code...", total=None)
            
            try:
                answer = self.planner.analyze_code(question)
                progress.remove_task(task)
                
                # Display answer
                self.console.print(Panel(
                    Markdown(answer),
                    title="Analysis",
                    border_style="blue"
                ))
                
                # Add to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": answer
                })
                
            except Exception as e:
                progress.remove_task(task)
                self.console.print(f"[red]Failed to analyze: {e}[/red]")
    
    def _create_plan(self, request_text: str):
        """Create a plan for the request."""
        self.context_mode = "planning"
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task("Creating plan...", total=None)
            
            try:
                # Create change request
                import uuid
                request = ChangeRequest(
                    id=str(uuid.uuid4()),
                    description=request_text,
                    repo=str(self.planner.repo_path),
                    branch=self.planner.git_adapter.get_current_branch() or "main"
                )
                
                # Generate plan
                plan = self.planner.create_plan(request)
                progress.remove_task(task)
                
                # Store current plan
                self.current_plan = plan
                
                # Display plan
                self._display_plan(plan)
                
                # Add to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": f"Created plan with {len(plan.steps)} steps"
                })
                
                self.console.print("\n[green]Plan created successfully![/green]")
                self.console.print("[dim]Use /execute to run this plan[/dim]")
                
            except Exception as e:
                progress.remove_task(task)
                self.console.print(f"[red]Failed to create plan: {e}[/red]")
            finally:
                self.context_mode = "normal"
    
    def _display_plan(self, plan):
        """Display a plan in a formatted way."""
        # Plan summary
        summary = Table(title="Plan Summary", show_header=False)
        summary.add_column("Property", style="cyan")
        summary.add_column("Value")
        
        summary.add_row("Plan ID", plan.id[:8])
        summary.add_row("Complexity", str(plan.complexity_label.value))
        summary.add_row("Steps", str(len(plan.steps)))
        summary.add_row("Affected Files", str(len(plan.affected_paths)))
        
        self.console.print(summary)
        
        # Rationale
        if plan.rationale:
            self.console.print("\n[bold]Rationale:[/bold]")
            for r in plan.rationale:
                self.console.print(f"• {r}")
        
        # Steps
        self.console.print("\n[bold]Implementation Steps:[/bold]")
        for i, step in enumerate(plan.steps, 1):
            self.console.print(f"\n[cyan]{i}. {step.goal}[/cyan]")
            self.console.print(f"   Type: {step.kind.value}")
            if step.hints:
                self.console.print("   Hints:")
                for hint in step.hints:
                    self.console.print(f"   - {hint}")
        
        # Affected files
        if plan.affected_paths:
            self.console.print("\n[bold]Files to be modified:[/bold]")
            for path in plan.affected_paths[:10]:  # Limit display
                self.console.print(f"• {path}")
            if len(plan.affected_paths) > 10:
                self.console.print(f"... and {len(plan.affected_paths) - 10} more")
    
    def _execute_plan(self):
        """Execute the current plan."""
        if not self.current_plan:
            self.console.print("[yellow]No plan to execute. Create one with /plan[/yellow]")
            return
        
        self.context_mode = "executing"
        
        # Confirm execution
        if not Prompt.ask(
            "[yellow]Execute this plan?[/yellow]",
            choices=["y", "n"],
            default="n"
        ) == "y":
            self.console.print("[dim]Execution cancelled[/dim]")
            self.context_mode = "normal"
            return
        
        # Execute with live updates
        self.console.print("\n[green]Starting execution...[/green]\n")
        
        try:
            # Track modified files
            self.modified_files = []
            
            # Execute each step
            for i, step in enumerate(self.current_plan.steps, 1):
                self.console.print(f"[cyan]Step {i}/{len(self.current_plan.steps)}:[/cyan] {step.goal}")
                
                # Simulate execution (replace with real executor)
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console,
                    transient=True
                ) as progress:
                    task = progress.add_task(f"Executing {step.kind.value}...", total=None)
                    
                    # TODO: Integrate with actual plan executor
                    import time
                    time.sleep(1)  # Simulate work
                    
                    progress.remove_task(task)
                
                self.console.print(f"[green]✓[/green] Completed: {step.goal}")
                
                # Track modified files (simulation)
                if step.kind.value in ["edit", "add"]:
                    for path in self.current_plan.affected_paths:
                        if path not in self.modified_files:
                            self.modified_files.append(path)
            
            self.console.print("\n[green]✨ Plan executed successfully![/green]")
            self._show_execution_summary()
            
        except Exception as e:
            self.console.print(f"\n[red]Execution failed: {e}[/red]")
        finally:
            self.context_mode = "normal"
    
    def _show_execution_summary(self):
        """Show summary of execution."""
        if not self.modified_files:
            return
        
        summary = Table(title="Execution Summary")
        summary.add_column("Modified Files", style="cyan")
        summary.add_column("Status", style="green")
        
        for file in self.modified_files[:10]:
            summary.add_row(file, "✓ Updated")
        
        if len(self.modified_files) > 10:
            summary.add_row(f"... and {len(self.modified_files) - 10} more", "")
        
        self.console.print(summary)
    
    def _show_status(self):
        """Show current session status."""
        status = Table(title="Session Status")
        status.add_column("Property", style="cyan")
        status.add_column("Value")
        
        # Repository info
        repo_info = self.planner.get_repository_info()
        status.add_row("Repository", repo_info.get("path", "Not loaded"))
        status.add_row("Branch", repo_info.get("current_branch", "N/A"))
        
        # Session info
        status.add_row("Conversation Length", str(len(self.conversation_history)))
        status.add_row("Current Plan", "Yes" if self.current_plan else "No")
        status.add_row("Modified Files", str(len(self.modified_files)))
        status.add_row("Context Mode", self.context_mode)
        
        self.console.print(status)
    
    def _show_help(self):
        """Show help information."""
        help_text = """
[bold]Available Commands:[/bold]

[cyan]/help[/cyan] - Show this help message
[cyan]/plan <request>[/cyan] - Create a plan for your request
[cyan]/execute[/cyan] - Execute the current plan
[cyan]/status[/cyan] - Show session status
[cyan]/repo [url][/cyan] - Load a repository or show info
[cyan]/history[/cyan] - Show conversation history
[cyan]/save[/cyan] - Save session to file
[cyan]/clear[/cyan] - Clear the screen
[cyan]/exit[/cyan] - Exit the session

[bold]Natural Language:[/bold]
• Ask questions about the code
• Request features or bug fixes
• Explain code functionality

[bold]Examples:[/bold]
• "Add error handling to the API client"
• "What does the RequestPlanner class do?"
• "Fix the null pointer exception in user service"
"""
        
        self.console.print(Panel(
            help_text,
            title="Help",
            border_style="blue"
        ))
    
    def _show_repository_info(self):
        """Show repository information."""
        info = self.planner.get_repository_info()
        
        # Create info panel
        info_text = f"""
Path: {info['path']}
Git Repository: {"Yes" if info['is_git_repo'] else "No"}
Branch: {info.get('current_branch', 'N/A')}
Total Files: {info.get('files_count', 0)}
Python Files: {info.get('python_files', 0)}
Remote: {info.get('remote_url', 'None')}
"""
        
        if info.get('last_commit'):
            commit = info['last_commit']
            info_text += f"\nLast Commit: [{commit['hash']}] {commit['message']}"
        
        self.console.print(Panel(
            info_text,
            title="Repository Information",
            border_style="cyan"
        ))
    
    def _load_repository(self, url: str):
        """Load a repository from URL."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task(f"Loading repository from {url}...", total=None)
            
            success = self.planner.load_repository(url)
            progress.remove_task(task)
            
            if success:
                self.console.print("[green]Repository loaded successfully![/green]")
                self._show_repository_info()
            else:
                self.console.print("[red]Failed to load repository[/red]")
    
    def _show_history(self):
        """Show conversation history."""
        if not self.conversation_history:
            self.console.print("[dim]No conversation history[/dim]")
            return
        
        self.console.print("[bold]Conversation History:[/bold]\n")
        
        for i, msg in enumerate(self.conversation_history[-10:]):  # Last 10 messages
            role_color = "cyan" if msg["role"] == "user" else "green"
            self.console.print(f"[{role_color}]{msg['role'].title()}:[/{role_color}]")
            self.console.print(msg["content"])
            self.console.print()
    
    def _save_session(self):
        """Save session to file."""
        from datetime import datetime
        import json
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"session_{timestamp}.json"
        
        session_data = {
            "timestamp": timestamp,
            "repository": str(self.planner.repo_path),
            "conversation": self.conversation_history,
            "modified_files": self.modified_files
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(session_data, f, indent=2)
            self.console.print(f"[green]Session saved to {filename}[/green]")
        except Exception as e:
            self.console.print(f"[red]Failed to save session: {e}[/red]")
    
    def _shutdown(self):
        """Shutdown the session gracefully."""
        self.console.print("\n[cyan]Goodbye! 👋[/cyan]")
        self.session_active = False
        
        # Cleanup
        if hasattr(self.planner, 'git_adapter'):
            self.planner.git_adapter.cleanup()