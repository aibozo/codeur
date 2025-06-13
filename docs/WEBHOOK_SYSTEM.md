# Agent Webhook System

The Agent Webhook System enables remote task execution through webhooks from various platforms like Discord, GitHub, and Slack. This allows teams to trigger agent operations without direct CLI access.

## Features

- **Multi-platform Support**: Discord, GitHub, Slack webhooks
- **Security**: Token authentication, signature verification, rate limiting
- **Project Mapping**: Map webhook sources to local project directories
- **Async Execution**: Non-blocking task execution with status tracking
- **Sandboxed Operations**: Safe execution with security boundaries

## Quick Start

### 1. Configuration

Create a `.agent.yaml` configuration file:

```yaml
webhook:
  enabled: true
  host: "0.0.0.0"
  port: 8080
  auth_enabled: true
  auth_tokens:
    - "your-secret-token-here"
  project_mappings:
    "my-project": "/path/to/my-project"
    "myorg/myrepo": "/path/to/myrepo"
```

Or use environment variables:

```bash
export AGENT_WEBHOOK_ENABLED=true
export AGENT_WEBHOOK_PORT=8080
export AGENT_WEBHOOK_AUTH_TOKENS='["your-secret-token"]'
export AGENT_WEBHOOK_PROJECT_MAPPINGS='{"my-project": "/path/to/project"}'
```

### 2. Generate Auth Token

```bash
# Generate a secure token
agent webhook generate-token

# Or hash an existing token
agent webhook generate-token "my-existing-token"
```

### 3. Start the Server

```bash
# Start with default settings
agent webhook start

# Or specify host/port
agent webhook start --host 0.0.0.0 --port 8080

# Use specific config file
agent webhook start --config .agent-webhook.yaml
```

## Platform Integration

### Discord

Set up a Discord bot or webhook that sends messages in this format:

```
!agent <action> <project> <args>
```

Examples:
- `!agent analyze my-project --complexity`
- `!agent fix backend-api --auto`
- `!agent test frontend --coverage`

### GitHub

The webhook system handles these GitHub events:

1. **Issues**: Opened issues with "agent" label
   ```markdown
   The performance is slow in the data module.
   
   /agent analyze --performance --suggest-fixes
   ```

2. **Pull Requests**: When agent-bot is requested as reviewer
3. **Comments**: On issues/PRs with @agent mentions
4. **Pushes**: Commits with `/agent fix` in message

### Slack

Use slash commands or app mentions:

```
/agent my-project analyze --security
@agent my-project fix "Update dependencies"
```

## Security

### Authentication

All webhook requests must include authentication:

```bash
curl -X POST http://localhost:8080/webhook \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"source": "discord", "event_type": "message", "payload": {...}}'
```

### Signature Verification

For GitHub webhooks, configure the webhook secret:

```yaml
webhook:
  secret_key: "github-webhook-secret"
```

### Rate Limiting

Default: 100 requests per 60 seconds per IP

```yaml
webhook:
  rate_limit_enabled: true
  rate_limit_requests: 100
  rate_limit_window_seconds: 60
```

## API Endpoints

### POST /webhook
Main webhook endpoint for receiving tasks.

Request:
```json
{
  "source": "github",
  "event_type": "issues",
  "payload": {...},
  "signature": "sha256=..."
}
```

Response:
```json
{
  "success": true,
  "message": "Task submitted successfully",
  "task_id": "uuid-here",
  "details": {
    "project": "/path/to/project",
    "command": "analyze",
    "source": "github"
  }
}
```

### GET /health
Health check endpoint.

### GET /status/{task_id}
Get task execution status.

## Task Execution

Tasks are executed asynchronously with:
- Sandboxed git operations (if enabled)
- Security validation for project paths
- Output capture and logging
- 5-minute timeout per task

## Project Mappings

Map webhook sources to project directories:

```yaml
project_mappings:
  # Direct mapping
  "project-name": "/absolute/path/to/project"
  
  # GitHub repositories
  "myorg/myrepo": "/path/to/myrepo"
  
  # Pattern matching (regex)
  "myorg/.*": "/path/to/org/repos"
  
  # Discord/Slack identifiers
  "backend-api": "/projects/backend-api"
```

## Examples

### Discord Webhook Payload

```json
{
  "source": "discord",
  "event_type": "message",
  "payload": {
    "content": "!agent analyze my-project --complexity",
    "author": {"username": "developer"},
    "channel": {"name": "dev-chat"}
  }
}
```

### GitHub Issue Webhook

```json
{
  "source": "github",
  "event_type": "issues",
  "payload": {
    "action": "opened",
    "issue": {
      "number": 42,
      "labels": [{"name": "agent"}],
      "body": "/agent fix --auto"
    },
    "repository": {
      "full_name": "myorg/myrepo"
    }
  }
}
```

## Testing

Test webhook handling locally:

```bash
# Generate example config
agent webhook init

# Test with example payload
agent webhook test --source discord \
  --payload examples/discord_payload.json \
  --project my-project
```

## Monitoring

Check active tasks and server status:

```bash
# View server health
curl http://localhost:8080/health

# Check specific task
curl http://localhost:8080/status/{task_id}
```

## Best Practices

1. **Security First**
   - Always use authentication in production
   - Rotate tokens regularly
   - Use HTTPS with proper certificates

2. **Project Isolation**
   - Enable git sandboxing for untrusted sources
   - Use specific project mappings, avoid wildcards
   - Set up .agent-security.yml in projects

3. **Resource Management**
   - Monitor task execution times
   - Set appropriate rate limits
   - Use task priorities for important operations

4. **Error Handling**
   - Check task status after submission
   - Monitor webhook server logs
   - Set up alerts for failed tasks

## Troubleshooting

### Webhook not processed
- Check authentication token
- Verify project mapping exists
- Review server logs for errors

### Task execution fails
- Ensure project path is valid
- Check agent command syntax
- Verify file permissions

### Rate limiting issues
- Increase rate limits if needed
- Use different tokens for services
- Implement request queuing on client side