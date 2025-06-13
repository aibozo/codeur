#!/usr/bin/env python3
"""
Example webhook client for Codeur.

This shows how to trigger agent tasks programmatically via webhooks.
"""

import requests
import json
import time
from typing import Dict, Any

class CodeurWebhookClient:
    """Client for interacting with Codeur webhook server."""
    
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        })
    
    def send_task(self, 
                  task: str,
                  project: str = None,
                  dry_run: bool = False,
                  platform: str = 'api') -> Dict[str, Any]:
        """Send a task to the webhook server."""
        payload = {
            'task': task,
            'project': project,
            'dry_run': dry_run,
            'user': 'api-client',
            'timestamp': time.time()
        }
        
        response = self.session.post(
            f'{self.base_url}/webhook/{platform}',
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def discord_command(self, command: str, channel: str = 'general') -> Dict[str, Any]:
        """Send a Discord-style command."""
        payload = {
            'content': f'!agent {command}',
            'channel': {'name': channel},
            'author': {'username': 'api-client'}
        }
        
        response = self.session.post(
            f'{self.base_url}/webhook/discord',
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def github_issue(self, 
                     title: str,
                     body: str,
                     repo: str = 'my-repo') -> Dict[str, Any]:
        """Simulate a GitHub issue webhook."""
        payload = {
            'action': 'opened',
            'issue': {
                'title': title,
                'body': body,
                'number': 123,
                'user': {'login': 'api-client'}
            },
            'repository': {'full_name': f'user/{repo}'}
        }
        
        response = self.session.post(
            f'{self.base_url}/webhook/github',
            json=payload,
            headers={'X-GitHub-Event': 'issues'}
        )
        response.raise_for_status()
        return response.json()
    
    def check_health(self) -> bool:
        """Check if the webhook server is healthy."""
        try:
            response = self.session.get(f'{self.base_url}/health')
            return response.status_code == 200
        except:
            return False


def main():
    """Example usage of the webhook client."""
    # Initialize client
    client = CodeurWebhookClient(
        base_url='http://localhost:8080',
        auth_token='your-auth-token-here'  # Generate with: agent-system webhook generate-token
    )
    
    # Check health
    if not client.check_health():
        print("❌ Webhook server is not running!")
        print("Start it with: agent-system webhook start")
        return
    
    print("✅ Webhook server is healthy!")
    
    # Example 1: Simple task
    print("\n📝 Sending simple task...")
    result = client.send_task(
        task="Add docstrings to all public methods",
        project="backend"
    )
    print(f"Task ID: {result['task_id']}")
    print(f"Status: {result['status']}")
    
    # Example 2: Discord-style command
    print("\n💬 Sending Discord command...")
    result = client.discord_command(
        command="analyze src/core/ --verbose",
        channel="dev-chat"
    )
    print(f"Response: {result}")
    
    # Example 3: GitHub issue
    print("\n🐛 Simulating GitHub issue...")
    result = client.github_issue(
        title="Bug: API returns 500 on invalid input",
        body="The /api/users endpoint crashes when given invalid email.\n\nSteps to reproduce:\n1. POST to /api/users\n2. Use email without @ symbol\n3. Server returns 500 instead of 400",
        repo="my-api"
    )
    print(f"Task created: {result}")
    
    # Example 4: Dry run mode
    print("\n🧪 Testing with dry-run...")
    result = client.send_task(
        task="Refactor the authentication module to use JWT",
        project="backend",
        dry_run=True
    )
    print(f"Dry run result: {result}")
    
    # Example 5: Batch operations
    print("\n📦 Sending batch tasks...")
    tasks = [
        "Update dependencies in requirements.txt",
        "Add type hints to utility functions",
        "Fix linting errors in tests/",
        "Update README with new API endpoints"
    ]
    
    for task in tasks:
        result = client.send_task(task, project="backend")
        print(f"  ✓ {task}: {result['task_id']}")
        time.sleep(1)  # Respect rate limits


if __name__ == '__main__':
    main()


# Advanced usage with async monitoring
async def monitor_task(client: CodeurWebhookClient, task_id: str):
    """Monitor a task until completion (would need WebSocket in real implementation)."""
    import asyncio
    
    while True:
        # In a real implementation, this would use WebSocket or SSE
        # For now, just demonstrate the concept
        status = await check_task_status(task_id)
        if status['completed']:
            print(f"✅ Task {task_id} completed!")
            print(f"Result: {status['result']}")
            break
        
        print(f"⏳ Task {task_id} is {status['progress']}% complete...")
        await asyncio.sleep(5)


# Example: Custom automation script
class CodeReviewBot:
    """Automated code review bot using Codeur webhooks."""
    
    def __init__(self, client: CodeurWebhookClient):
        self.client = client
    
    def review_pr(self, pr_files: list, pr_number: int):
        """Review a pull request."""
        # Analyze changed files
        for file in pr_files:
            if file.endswith('.py'):
                self.client.send_task(
                    f"Analyze {file} for security issues and code style",
                    project="main"
                )
        
        # Generate summary
        self.client.send_task(
            f"Generate code review summary for PR #{pr_number}",
            project="main"
        )
    
    def daily_maintenance(self):
        """Run daily maintenance tasks."""
        tasks = [
            ("Update dependencies and check for vulnerabilities", "all"),
            ("Run comprehensive test suite", "all"),
            ("Generate code coverage report", "all"),
            ("Check for TODO comments older than 30 days", "all"),
            ("Analyze code complexity metrics", "backend"),
            ("Update API documentation", "backend"),
        ]
        
        for task, project in tasks:
            print(f"🔧 Running: {task} on {project}")
            self.client.send_task(task, project=project)
            time.sleep(2)