# Model Card System Documentation

## Overview

The agent system now includes a unified model card system that provides:
- Centralized model configuration
- Cost tracking and estimation
- Input/output limits enforcement
- Provider-agnostic interface
- Per-agent model selection

## Configuration

### Environment Variables

Models are configured through environment variables in your `.env` file:

```env
# Agent-specific model configuration
ARCHITECT_MODEL=gpt-4o           # Architect agent model
REQUEST_PLANNER_MODEL=gpt-4o     # Request planner model
CODING_MODEL=claude-sonnet-4     # Coding agent model
ANALYZER_MODEL=gemini-2.0-flash  # Analyzer agent model
GENERAL_MODEL=gpt-4o            # Default model for other uses
```

### Available Models

#### OpenAI Models
- **gpt-4o**: Balanced flagship model ($2.50/$10.00 per 1M tokens)
- **o3**: SOTA reasoning with vision ($2.00/$8.00 per 1M tokens)
- **o4-mini**: Fast and cost-efficient ($1.10/$4.40 per 1M tokens)
- **o1-pro**: Ultra-premium for complex tasks ($150/$600 per 1M tokens)

#### Google Models
- **gemini-2.0-flash**: Fast multimodal model ($0.10/$0.40 per 1M tokens)
- **gemini-2.5-flash**: Efficient with thinking mode ($0.15/$0.60-$3.50 per 1M tokens)
- **gemini-2.5-pro**: SOTA with 2M context ($2.50/$10.00 per 1M tokens)

#### Anthropic Models
- **claude-opus-4**: SOTA for coding ($15.00/$75.00 per 1M tokens)
- **claude-sonnet-4**: Balanced performance ($3.00/$15.00 per 1M tokens)

### Model Aliases

For convenience, you can use aliases:
- `fast` → gemini-2.0-flash
- `balanced` → gpt-4o
- `powerful` → claude-opus-4
- `budget` → gemini-2.5-flash
- `premium` → o1-pro
- `reasoning` → o3

## Usage

### In Code

The LLMClient automatically uses the model card system:

```python
from src.llm import LLMClient

# Create client for specific agent
client = LLMClient(agent_name="architect")

# Or specify a model directly
client = LLMClient(model="claude-sonnet-4", agent_name="coding")

# Generate text
response = client.generate(
    prompt="Your prompt here",
    system_prompt="Optional system prompt",
    max_tokens=2000,  # Automatically capped to model limits
    temperature=0.7   # Automatically adjusted to model range
)

# Get cost summary
summary = client.get_cost_summary()
print(f"Total cost for {summary['agent']}: ${summary['total_cost']:.4f}")
```

### Cost Tracking

View costs using the CLI:

```bash
# Show cost summary
agent cost summary

# Show available models and pricing
agent cost models

# Reset cost tracking
agent cost reset
```

## Model Selection Guidelines

### By Agent Type

1. **Architect Agent**: Use balanced models with good reasoning
   - Recommended: `gpt-4o`, `claude-sonnet-4`
   - For complex architecture: `claude-opus-4`, `o3`

2. **Coding Agent**: Use models optimized for code generation
   - Recommended: `claude-sonnet-4`, `claude-opus-4`
   - Budget option: `gemini-2.0-flash`

3. **Request Planner**: Use models with good task decomposition
   - Recommended: `gpt-4o`, `gemini-2.5-pro`
   - For complex planning: `o3`, `o1-pro`

4. **Analyzer Agent**: Use fast models for code analysis
   - Recommended: `gemini-2.0-flash`, `gemini-2.5-flash`
   - For detailed analysis: `gpt-4o`

### By Use Case

- **Large Context (>128k tokens)**: `gemini-2.5-pro` (2M), `gemini-2.0-flash` (1M)
- **Vision Support**: `gpt-4o`, `o3`, `gemini` models, `claude` models
- **Tool/Function Calling**: All models except some specialized ones
- **JSON Mode**: OpenAI and Google models (not Anthropic)
- **Budget Conscious**: `gemini-2.0-flash`, `gemini-2.5-flash`

## Implementation Details

### Model Cards

Each model has a card containing:
- Provider and model ID
- Display name
- Input/output pricing
- Context window size
- Maximum output tokens
- Supported features
- Temperature range
- Additional costs (tools, search, etc.)

### Cost Calculation

Costs are automatically tracked:
1. Input tokens counted before API call
2. Output tokens from API response or estimation
3. Additional costs for tool usage
4. Aggregated by agent and model

### Limits Enforcement

The system automatically:
- Caps max_tokens to model's limit
- Adjusts temperature to valid range
- Validates provider requirements
- Falls back to defaults when needed

## Adding New Models

To add a new model, update `src/core/model_cards.py`:

```python
MODEL_CARDS["new-model-id"] = ModelCard(
    provider=ModelProvider.OPENAI,
    model_id="new-model-id",
    display_name="New Model Name",
    input_price=1.00,  # USD per 1M tokens
    output_price=2.00,  # USD per 1M tokens
    context_window=100_000,
    max_output_tokens=4_096,
    features=["feature1", "feature2"],
    supports_vision=True,
    supports_tools=True,
    supports_json_mode=True,
    temperature_range=(0.0, 2.0)
)
```

## Troubleshooting

### Model Not Found
- Check model ID matches exactly
- Verify environment variable is set
- Try using full model ID instead of alias

### API Key Issues
- Ensure provider API key is set in `.env`
- Check key has access to the model
- Verify key permissions

### Cost Tracking Issues
- Cost tracking is automatic
- Use `agent cost summary` to view
- Reset with `agent cost reset` if needed

## Future Enhancements

- [ ] Add Groq, Cohere, and other providers
- [ ] Implement cost budgets and alerts
- [ ] Add model performance benchmarks
- [ ] Support for local models (Ollama, etc.)
- [ ] Export cost reports to CSV/JSON
- [ ] Real-time cost monitoring dashboard