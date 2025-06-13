# Discord Webhook Setup for Codeur

## Quick Start

### 1. Install and Configure Codeur

```bash
# Install codeur globally
pip install -e /path/to/codeur

# Initialize webhook config
agent-system webhook init
```

### 2. Configure Your Projects

Edit `.agent.yaml`:

```yaml
webhook:
  # Generate with: agent-system webhook generate-token
  auth_token: "your-secure-token-here"
  
  # Discord bot token from https://discord.com/developers/applications
  discord_bot_token: "your-discord-bot-token"
  
  # Map Discord channels to local directories
  project_mapping:
    - pattern: "frontend"
      path: "/home/riley/projects/my-frontend"
    - pattern: "backend|api"
      path: "/home/riley/projects/my-api"
    - pattern: ".*"  # Default fallback
      path: "/home/riley/projects/current"
```

### 3. Start the Webhook Server

```bash
# Start in background
agent-system webhook start --daemon

# Or run in foreground to see logs
agent-system webhook start
```

### 4. Set Up Discord Bot

1. Create a Discord Application at https://discord.com/developers/applications
2. Create a Bot and copy the token
3. Invite bot to your server with these permissions:
   - Read Messages
   - Send Messages
   - Read Message History
   - Add Reactions

### 5. Configure Discord Webhook

In your Discord server settings:
1. Go to Integrations → Webhooks
2. Create webhook pointing to: `http://your-server:8080/webhook/discord`
3. Add your auth token as a query parameter: `?token=your-secure-token`

## Usage Examples

### Basic Commands

```
!agent run "Add error handling to the API"
!agent analyze src/
!agent search "TODO"
!agent status
```

### Project-Specific Commands

```
# Works on frontend project
!agent run frontend "Convert components to TypeScript"

# Works on backend project  
!agent run api "Add rate limiting to endpoints"
```

### Advanced Usage

```
# Dry run mode
!agent run --dry-run "Refactor user authentication"

# Specific file operations
!agent run "Fix the bug in src/users/auth.py"

# Code review
!agent analyze --verbose src/core/
```

## Features

- **Async Execution**: Commands run in background, won't block Discord
- **Status Updates**: Bot reacts with ✅ on success, ❌ on failure
- **Security**: Token-based auth + path validation
- **Rate Limiting**: 100 requests/minute default
- **Timeout Protection**: 5-minute max execution time
- **Project Mapping**: Route commands to different codebases

## Monitoring

```bash
# View logs
tail -f ~/.agent/webhook.log

# Check status
agent-system webhook status

# Test webhook
agent-system webhook test discord
```

## Security Notes

1. **Never commit tokens** - Use environment variables
2. **Restrict bot permissions** - Only what's needed
3. **Use HTTPS in production** - Encrypt webhook traffic
4. **Whitelist IPs** - Restrict to Discord's IP ranges
5. **Monitor logs** - Watch for suspicious activity

## Troubleshooting

### Bot not responding?
- Check webhook server is running: `ps aux | grep agent-webhook`
- Verify bot has message permissions
- Check logs: `~/.agent/webhook.log`

### Authentication errors?
- Regenerate token: `agent-system webhook generate-token`
- Verify token in both `.agent.yaml` and webhook URL

### Wrong directory?
- Check project_mapping patterns
- Use more specific patterns for better matching
- Test with: `agent-system webhook test discord`

## Example Discord Workflow

1. **Developer in Discord**: "Hey bot, can you add input validation to the user registration?"
2. **Send command**: `!agent run backend "Add input validation to user registration endpoint"`
3. **Bot responds**: ✅ reaction + "Task started in backend project"
4. **Work happens**: Agent analyzes code, generates patches
5. **Completion**: Bot posts summary with file changes
6. **Review locally**: Developer pulls changes and reviews

## Advanced Configuration

### Multiple Environments

```yaml
environments:
  dev:
    webhook_url: "http://dev-server:8080"
    projects:
      - name: "dev-frontend"
        path: "/projects/dev/frontend"
  
  prod:
    webhook_url: "https://prod-server:8443"
    projects:
      - name: "prod-api"
        path: "/projects/prod/api"
```

### Custom Commands

Create `.agent-commands.yaml`:

```yaml
commands:
  review:
    description: "Code review with specific rules"
    template: "analyze {path} --check-style --check-security"
  
  quickfix:
    description: "Fast bug fixes"
    template: "run --fast --no-tests 'Fix: {message}'"
```

## Next Steps

1. Set up GitHub webhooks for PR automation
2. Add Slack integration for team channels
3. Create custom Discord commands for your workflow
4. Set up monitoring dashboards
5. Implement CD pipeline triggers

Happy remote coding! 🚀