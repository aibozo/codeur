# Webhook Architecture

## System Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│     Discord     │     │     GitHub      │     │      Slack      │
│                 │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ Webhook               │ Webhook               │ Webhook
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    Codeur Webhook Server                        │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐     │
│  │   Security  │  │   Handlers   │  │   Task Executor   │     │
│  │  - Auth     │  │  - Discord   │  │  - Async Queue    │     │
│  │  - HMAC     │  │  - GitHub    │  │  - Worker Pool    │     │
│  │  - Rate Lim │  │  - Slack     │  │  - Timeout Mgmt   │     │
│  └─────────────┘  └──────────────┘  └───────────────────┘     │
│                                                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Execute Commands
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Codeur Agent System                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│  │   Request    │  │    Code      │  │     Coding       │     │
│  │   Planner    │  │   Planner    │  │     Agent        │     │
│  └──────────────┘  └──────────────┘  └──────────────────┘     │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│  │     RAG      │  │   Security   │  │   Git Sandbox    │     │
│  │   Service    │  │   Manager    │  │                  │     │
│  └──────────────┘  └──────────────┘  └──────────────────┘     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Operate on
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Local Codebases                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│  │   Frontend   │  │   Backend    │  │   Mobile App     │     │
│  │   Project    │  │   Project    │  │    Project       │     │
│  └──────────────┘  └──────────────┘  └──────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## Request Flow

```
1. External Event
   └─> Discord: "!agent run 'Add auth to API'"
   
2. Webhook Receipt
   └─> Validate token/signature
   └─> Parse platform-specific payload
   └─> Extract task and context
   
3. Security Check
   └─> Verify authentication
   └─> Check rate limits
   └─> Validate paths/projects
   
4. Task Routing
   └─> Map to project directory
   └─> Create execution context
   └─> Queue for processing
   
5. Async Execution
   └─> Worker picks up task
   └─> Change to project directory
   └─> Run agent command
   └─> Capture output/errors
   
6. Response Handling
   └─> Format platform-specific response
   └─> Send success/failure notification
   └─> Log for audit trail
```

## Security Layers

```
┌─────────────────────────────────────────┐
│          Network Security               │
│  - HTTPS/TLS in production              │
│  - IP whitelisting (optional)           │
└────────────────┬────────────────────────┘
                 │
┌─────────────────────────────────────────┐
│       Authentication Layer              │
│  - Bearer token validation              │
│  - HMAC signature (GitHub/Slack)        │
│  - Rate limiting per token              │
└────────────────┬────────────────────────┘
                 │
┌─────────────────────────────────────────┐
│        Path Security Layer              │
│  - Project directory isolation          │
│  - Symlink traversal protection         │
│  - Forbidden pattern matching           │
└────────────────┬────────────────────────┘
                 │
┌─────────────────────────────────────────┐
│       Execution Security                │
│  - Subprocess isolation                 │
│  - Resource limits (CPU/memory)         │
│  - Timeout enforcement (5 min)          │
└─────────────────────────────────────────┘
```

## Configuration Example

```yaml
# .agent.yaml
webhook:
  # Server configuration
  host: "0.0.0.0"
  port: 8080
  workers: 4
  
  # Security
  auth_token: "${AGENT_WEBHOOK_TOKEN}"
  rate_limit: 100  # per minute
  timeout: 300     # seconds
  
  # Platform tokens
  discord_bot_token: "${DISCORD_BOT_TOKEN}"
  github_webhook_secret: "${GITHUB_WEBHOOK_SECRET}"
  slack_signing_secret: "${SLACK_SIGNING_SECRET}"
  
  # Project mapping
  project_mapping:
    # Specific project patterns
    - pattern: "frontend|ui|web"
      path: "/home/user/projects/frontend"
      
    - pattern: "backend|api|server"
      path: "/home/user/projects/backend"
      
    - pattern: "mobile|app"
      path: "/home/user/projects/mobile"
      
    # GitHub repo mapping
    - pattern: "org/repo-name"
      path: "/home/user/projects/repo-name"
      
    # Default fallback
    - pattern: ".*"
      path: "/home/user/projects/current"
  
  # Allowed commands (optional whitelist)
  allowed_commands:
    - "run"
    - "analyze"
    - "search"
    - "status"
  
  # Security restrictions
  forbidden_paths:
    - "/etc"
    - "/var"
    - "/root"
    - "~/.ssh"
```

## Deployment Options

### 1. Systemd Service (Linux)

```ini
# /etc/systemd/system/codeur-webhook.service
[Unit]
Description=Codeur Webhook Server
After=network.target

[Service]
Type=simple
User=codeur
WorkingDirectory=/opt/codeur
ExecStart=/usr/local/bin/agent-system webhook start
Restart=always
Environment="AGENT_CONFIG=/etc/codeur/agent.yaml"

[Install]
WantedBy=multi-user.target
```

### 2. Docker Container

```dockerfile
FROM python:3.10-slim
RUN pip install codeur
EXPOSE 8080
CMD ["agent-system", "webhook", "start"]
```

### 3. Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: codeur-webhook
spec:
  replicas: 3
  selector:
    matchLabels:
      app: codeur-webhook
  template:
    metadata:
      labels:
        app: codeur-webhook
    spec:
      containers:
      - name: webhook
        image: codeur/webhook:latest
        ports:
        - containerPort: 8080
        env:
        - name: AGENT_WEBHOOK_TOKEN
          valueFrom:
            secretKeyRef:
              name: codeur-secrets
              key: webhook-token
```

## Monitoring & Observability

### Metrics Exposed

- `webhook_requests_total` - Total requests by platform
- `webhook_errors_total` - Failed requests by type
- `task_execution_duration` - Task completion times
- `task_queue_length` - Current queue size
- `worker_pool_utilization` - Active workers

### Health Endpoints

- `GET /health` - Basic health check
- `GET /metrics` - Prometheus metrics
- `GET /status` - Detailed system status

### Logging

All events are logged with structured JSON:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "info",
  "event": "webhook_received",
  "platform": "discord",
  "user": "developer",
  "task": "run 'Add error handling'",
  "project": "backend",
  "task_id": "abc123",
  "duration_ms": 1234
}
```

## Scaling Considerations

1. **Horizontal Scaling**: Run multiple webhook servers behind a load balancer
2. **Queue Backend**: Use Redis/RabbitMQ for distributed task queue
3. **Result Storage**: Use S3/GCS for large task outputs
4. **Rate Limiting**: Use Redis for distributed rate limiting
5. **Caching**: Cache project mappings and auth tokens

## Integration Examples

### CI/CD Pipeline

```yaml
# .github/workflows/code-review.yml
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Request AI Code Review
        run: |
          curl -X POST https://webhook.mycompany.com/webhook/github \
            -H "Authorization: Bearer ${{ secrets.CODEUR_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{
              "action": "opened",
              "pull_request": {
                "number": ${{ github.event.pull_request.number }},
                "title": "${{ github.event.pull_request.title }}"
              }
            }'
```

### Slack Workflow

```javascript
// Slack app command handler
app.command('/codeur', async ({ command, ack, say }) => {
  await ack();
  
  const response = await fetch('https://webhook.internal/webhook/slack', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.CODEUR_TOKEN}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      text: command.text,
      user_id: command.user_id,
      channel_id: command.channel_id
    })
  });
  
  await say(`Task queued: ${response.task_id}`);
});
```