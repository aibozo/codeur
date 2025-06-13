"""
Webhook handlers for different platforms.

This module provides handlers for processing webhooks from various
sources like Discord, GitHub, Slack, etc.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pathlib import Path
import re

from pydantic import BaseModel

from src.core.logging import get_logger
from src.core.settings import get_settings

logger = get_logger(__name__)


class Task(BaseModel):
    """Task to be executed by the agent."""
    project_path: str
    command: str
    args: List[str] = []
    environment: Dict[str, str] = {}
    description: str = ""
    source: str
    source_id: str  # ID from source system
    priority: int = 5  # 1-10, higher is more important
    metadata: Dict[str, Any] = {}


class WebhookHandler(ABC):
    """Base webhook handler interface."""
    
    def __init__(self):
        """Initialize handler."""
        self.settings = get_settings()
        self.project_mappings = self.settings.webhook.project_mappings
    
    @abstractmethod
    async def process_webhook(self, webhook_req: Any) -> Optional[Task]:
        """
        Process webhook and return task if applicable.
        
        Args:
            webhook_req: Webhook request data
            
        Returns:
            Task object or None if no action needed
        """
        pass
    
    def get_project_path(self, identifier: str) -> Optional[str]:
        """
        Get project path from identifier.
        
        Args:
            identifier: Project identifier from webhook
            
        Returns:
            Absolute project path or None
        """
        # Check direct mapping
        if identifier in self.project_mappings:
            return str(Path(self.project_mappings[identifier]).resolve())
        
        # Check pattern matching
        for pattern, path in self.project_mappings.items():
            if re.match(pattern, identifier):
                return str(Path(path).resolve())
        
        return None


class DiscordHandler(WebhookHandler):
    """Handler for Discord webhooks."""
    
    async def process_webhook(self, webhook_req: Any) -> Optional[Task]:
        """Process Discord webhook."""
        payload = webhook_req.payload
        
        # Extract message content
        content = payload.get("content", "")
        author = payload.get("author", {})
        channel = payload.get("channel", {})
        
        # Parse command from message
        command_match = re.match(r"!agent\s+(\w+)\s+(.+)", content)
        if not command_match:
            logger.info("No agent command found in Discord message")
            return None
        
        action = command_match.group(1)
        args_str = command_match.group(2)
        
        # Parse project and command
        parts = args_str.split(maxsplit=1)
        if len(parts) < 2:
            logger.warning("Invalid Discord command format")
            return None
        
        project_id = parts[0]
        command_args = parts[1]
        
        # Get project path
        project_path = self.get_project_path(project_id)
        if not project_path:
            logger.warning(f"No project mapping for: {project_id}")
            return None
        
        # Map Discord actions to agent commands
        command_map = {
            "analyze": "analyze",
            "fix": "run",
            "test": "test",
            "search": "search",
        }
        
        command = command_map.get(action, action)
        
        return Task(
            project_path=project_path,
            command=command,
            args=command_args.split(),
            description=f"Discord command from {author.get('username', 'unknown')}",
            source="discord",
            source_id=payload.get("id", ""),
            metadata={
                "author": author,
                "channel": channel,
                "original_content": content
            }
        )


class GitHubHandler(WebhookHandler):
    """Handler for GitHub webhooks."""
    
    async def process_webhook(self, webhook_req: Any) -> Optional[Task]:
        """Process GitHub webhook."""
        payload = webhook_req.payload
        event_type = webhook_req.event_type
        
        # Handle different GitHub events
        if event_type == "issues":
            return await self._handle_issue_event(payload)
        elif event_type == "pull_request":
            return await self._handle_pr_event(payload)
        elif event_type == "push":
            return await self._handle_push_event(payload)
        elif event_type == "issue_comment":
            return await self._handle_comment_event(payload)
        else:
            logger.info(f"Unhandled GitHub event type: {event_type}")
            return None
    
    async def _handle_issue_event(self, payload: Dict[str, Any]) -> Optional[Task]:
        """Handle GitHub issue events."""
        action = payload.get("action")
        issue = payload.get("issue", {})
        repo = payload.get("repository", {})
        
        if action != "opened":
            return None
        
        # Check if issue has agent label
        labels = [label.get("name", "") for label in issue.get("labels", [])]
        if "agent" not in labels and "bot" not in labels:
            return None
        
        # Parse issue body for commands
        body = issue.get("body", "")
        command_match = re.search(r"/agent\s+(\w+)\s*(.*)", body)
        
        if not command_match:
            return None
        
        command = command_match.group(1)
        args = command_match.group(2).strip()
        
        # Get project path from repo
        repo_name = repo.get("full_name", "")
        project_path = self.get_project_path(repo_name)
        
        if not project_path:
            logger.warning(f"No project mapping for repo: {repo_name}")
            return None
        
        return Task(
            project_path=project_path,
            command=command,
            args=args.split() if args else [],
            description=f"GitHub issue #{issue.get('number')}: {issue.get('title')}",
            source="github",
            source_id=str(issue.get("id", "")),
            priority=7,  # Issues get higher priority
            metadata={
                "issue_number": issue.get("number"),
                "issue_url": issue.get("html_url"),
                "author": issue.get("user", {}).get("login"),
                "repo": repo_name
            }
        )
    
    async def _handle_pr_event(self, payload: Dict[str, Any]) -> Optional[Task]:
        """Handle GitHub pull request events."""
        action = payload.get("action")
        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})
        
        if action not in ["opened", "synchronize"]:
            return None
        
        # Check for agent review request
        requested_reviewers = pr.get("requested_reviewers", [])
        if not any(r.get("login") == "agent-bot" for r in requested_reviewers):
            return None
        
        repo_name = repo.get("full_name", "")
        project_path = self.get_project_path(repo_name)
        
        if not project_path:
            return None
        
        return Task(
            project_path=project_path,
            command="review",
            args=[f"pr/{pr.get('number')}"],
            description=f"Review PR #{pr.get('number')}: {pr.get('title')}",
            source="github",
            source_id=str(pr.get("id", "")),
            priority=8,  # PR reviews are high priority
            metadata={
                "pr_number": pr.get("number"),
                "pr_url": pr.get("html_url"),
                "author": pr.get("user", {}).get("login"),
                "repo": repo_name,
                "base": pr.get("base", {}).get("ref"),
                "head": pr.get("head", {}).get("ref")
            }
        )
    
    async def _handle_push_event(self, payload: Dict[str, Any]) -> Optional[Task]:
        """Handle GitHub push events."""
        # Only handle pushes to main/master that break tests
        ref = payload.get("ref", "")
        if ref not in ["refs/heads/main", "refs/heads/master"]:
            return None
        
        repo = payload.get("repository", {})
        repo_name = repo.get("full_name", "")
        
        # Check commit messages for agent commands
        commits = payload.get("commits", [])
        for commit in commits:
            message = commit.get("message", "")
            if "/agent fix" in message or "[agent-fix]" in message:
                project_path = self.get_project_path(repo_name)
                if project_path:
                    return Task(
                        project_path=project_path,
                        command="fix",
                        args=["--auto"],
                        description=f"Auto-fix after push to {ref}",
                        source="github",
                        source_id=commit.get("id", ""),
                        priority=6,
                        metadata={
                            "commit_sha": commit.get("id"),
                            "commit_message": message,
                            "author": commit.get("author", {}).get("name"),
                            "repo": repo_name
                        }
                    )
        
        return None
    
    async def _handle_comment_event(self, payload: Dict[str, Any]) -> Optional[Task]:
        """Handle GitHub issue/PR comment events."""
        action = payload.get("action")
        if action != "created":
            return None
        
        comment = payload.get("comment", {})
        issue = payload.get("issue", {})
        repo = payload.get("repository", {})
        
        # Parse comment for agent commands
        body = comment.get("body", "")
        command_match = re.search(r"@agent\s+(\w+)\s*(.*)", body)
        
        if not command_match:
            return None
        
        command = command_match.group(1)
        args = command_match.group(2).strip()
        
        repo_name = repo.get("full_name", "")
        project_path = self.get_project_path(repo_name)
        
        if not project_path:
            return None
        
        return Task(
            project_path=project_path,
            command=command,
            args=args.split() if args else [],
            description=f"Comment on #{issue.get('number')}: {command}",
            source="github",
            source_id=str(comment.get("id", "")),
            priority=7,
            metadata={
                "issue_number": issue.get("number"),
                "comment_url": comment.get("html_url"),
                "author": comment.get("user", {}).get("login"),
                "repo": repo_name
            }
        )


class SlackHandler(WebhookHandler):
    """Handler for Slack webhooks."""
    
    async def process_webhook(self, webhook_req: Any) -> Optional[Task]:
        """Process Slack webhook."""
        payload = webhook_req.payload
        
        # Handle Slack slash commands
        if "command" in payload:
            return await self._handle_slash_command(payload)
        
        # Handle Slack events
        if "event" in payload:
            return await self._handle_event(payload)
        
        return None
    
    async def _handle_slash_command(self, payload: Dict[str, Any]) -> Optional[Task]:
        """Handle Slack slash commands."""
        command = payload.get("command", "")
        text = payload.get("text", "")
        
        if command != "/agent":
            return None
        
        # Parse command text
        parts = text.split(maxsplit=2)
        if len(parts) < 2:
            return None
        
        project_id = parts[0]
        agent_command = parts[1]
        args = parts[2] if len(parts) > 2 else ""
        
        project_path = self.get_project_path(project_id)
        if not project_path:
            return None
        
        return Task(
            project_path=project_path,
            command=agent_command,
            args=args.split() if args else [],
            description=f"Slack command from {payload.get('user_name', 'unknown')}",
            source="slack",
            source_id=payload.get("trigger_id", ""),
            metadata={
                "user_id": payload.get("user_id"),
                "user_name": payload.get("user_name"),
                "channel_id": payload.get("channel_id"),
                "team_id": payload.get("team_id")
            }
        )
    
    async def _handle_event(self, payload: Dict[str, Any]) -> Optional[Task]:
        """Handle Slack events."""
        event = payload.get("event", {})
        
        if event.get("type") != "app_mention":
            return None
        
        text = event.get("text", "")
        
        # Parse mention text
        command_match = re.search(r"<@\w+>\s+(\w+)\s+(\w+)\s*(.*)", text)
        if not command_match:
            return None
        
        project_id = command_match.group(1)
        command = command_match.group(2)
        args = command_match.group(3).strip()
        
        project_path = self.get_project_path(project_id)
        if not project_path:
            return None
        
        return Task(
            project_path=project_path,
            command=command,
            args=args.split() if args else [],
            description=f"Slack mention in {event.get('channel')}",
            source="slack",
            source_id=event.get("ts", ""),
            metadata={
                "user": event.get("user"),
                "channel": event.get("channel"),
                "ts": event.get("ts"),
                "thread_ts": event.get("thread_ts")
            }
        )


def create_handler(source: str) -> Optional[WebhookHandler]:
    """
    Create appropriate webhook handler for source.
    
    Args:
        source: Webhook source (discord, github, slack, etc.)
        
    Returns:
        Handler instance or None
    """
    handlers = {
        "discord": DiscordHandler,
        "github": GitHubHandler,
        "slack": SlackHandler,
    }
    
    handler_class = handlers.get(source.lower())
    if handler_class:
        return handler_class()
    
    logger.warning(f"No handler available for source: {source}")
    return None