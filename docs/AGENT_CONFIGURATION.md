# Agent Configuration System

## Overview

The agent system now includes a unified configuration system that allows centralized management of agent settings, including model selection, parameters, and capabilities.

## Default Configuration

All agents are configured to use **Gemini 2.5 Flash** by default, providing:
- Fast response times ($0.15/$0.60 per 1M tokens)
- Large context window (1M tokens)
- Multimodal capabilities
- Cost-effective operation

## Agent Types and Defaults

| Agent Type | Default Model | Temperature | Max Tokens | Purpose |
|------------|---------------|-------------|------------|---------|
| Architect | gemini-2.5-flash | 0.7 | 4000 | High-level system design |
| Request Planner | gemini-2.5-flash | 0.7 | 3000 | Convert requests to plans |
| Coding | gemini-2.5-flash | 0.2 | 4000 | Generate code patches |
| Analyzer | gemini-2.5-flash | 0.5 | 2000 | Analyze code architecture |
| Code Planner | gemini-2.5-flash | 0.7 | 3000 | Plan implementations |
| Test | gemini-2.5-flash | 0.3 | 3000 | Generate test cases |
| General | gemini-2.5-flash | 0.7 | 2000 | General purpose tasks |

## Configuration Methods

### 1. Environment Variables (Recommended)

Override default models for specific agents in your `.env` file:

```env
# Override specific agents
ARCHITECT_MODEL=gpt-4o
CODING_MODEL=claude-sonnet-4
ANALYZER_MODEL=gemini-2.0-flash

# Keep others as default (gemini-2.5-flash)
```

### 2. CLI Commands

View and manage configurations using the CLI:

```bash
# View current agent configurations
agent config show

# Temporarily change a model (session only)
agent config set-model coding claude-sonnet-4

# Set all agents to use the same model
agent config set-all-models gpt-4o

# Reset all to gemini-2.5-flash
agent config reset
```

### 3. Programmatic Access

```python
from src.core.agent_config import AgentConfigManager

# Get configuration for an agent
config = AgentConfigManager.get_config("architect")
print(f"Model: {config.get_model()}")
print(f"Temperature: {config.temperature}")

# Update default model (runtime only)
AgentConfigManager.update_default_model("coding", "claude-opus-4")
```

## Configuration Hierarchy

1. **Environment Variables** (highest priority)
   - `{AGENT_TYPE}_MODEL` in `.env` file
   - Persists across sessions

2. **Runtime Configuration**
   - CLI commands or programmatic updates
   - Session-specific changes

3. **Default Configuration**
   - Built-in defaults (all use gemini-2.5-flash)
   - Fallback when no overrides exist

## Agent Capabilities

Each agent has defined capabilities that help with:
- Task assignment
- Model selection
- Feature compatibility

### Capability List

- **planning**: High-level planning and orchestration
- **architecture**: System design and structure
- **task_creation**: Creating and managing tasks
- **coding**: Code generation and modification
- **patching**: Creating code patches
- **refactoring**: Code improvement
- **analysis**: Code and architecture analysis
- **pattern_detection**: Identifying code patterns
- **testing**: Test generation and validation
- **decomposition**: Breaking down complex tasks

## Model Selection Guidelines

### When to Override Defaults

1. **Complex Architecture Tasks**
   - Use `claude-opus-4` or `gpt-4o` for architect
   - Better reasoning for system design

2. **Critical Code Generation**
   - Use `claude-sonnet-4` for coding agent
   - Higher quality code output

3. **Budget Constraints**
   - Keep `gemini-2.5-flash` (default)
   - Most cost-effective option

4. **Large Context Requirements**
   - Use `gemini-2.5-pro` (2M context)
   - For analyzing large codebases

## Integration with Frontend

The configuration system is designed to support frontend integration:

1. **Initialization**: Frontend can set models during project init
2. **Runtime Changes**: Update models for new agent instances
3. **Compatibility Check**: Verify model supports required features
4. **Cost Display**: Show pricing for selected models

## Best Practices

1. **Use Environment Variables**
   - Persist configuration across sessions
   - Easy to manage and version control

2. **Monitor Costs**
   - Use `agent cost summary` regularly
   - Adjust models based on budget

3. **Match Model to Task**
   - Complex tasks: More powerful models
   - Simple tasks: Keep default (gemini-2.5-flash)
   - Analysis tasks: Fast models suffice

4. **Test Configuration**
   - Run `agent config show` after changes
   - Verify models are correctly set

## Troubleshooting

### Model Not Changing
- Check environment variable spelling
- Ensure `.env` file is loaded
- Verify model name is valid

### API Key Issues
- Set `GOOGLE_API_KEY` for Gemini models
- Set appropriate keys for other providers
- Check key permissions

### Performance Issues
- Review model selection
- Consider context window limits
- Check token usage with cost tracker

## Future Enhancements

- [ ] Model performance benchmarks
- [ ] Automatic model selection based on task
- [ ] Model fallback chains
- [ ] Per-project model configuration
- [ ] Model usage analytics