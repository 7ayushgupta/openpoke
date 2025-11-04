# LLM Provider Configuration Guide

OpenPoke now supports multiple LLM providers! You can choose between **OpenAI** (direct, often cheaper) or **OpenRouter** (multi-provider access) by setting environment variables.

## Quick Start

### Option 1: Use OpenAI (Direct, Cost-Effective)

```bash
# Set provider to OpenAI
export LLM_PROVIDER=openai

# Add your OpenAI API key
export OPENAI_API_KEY=sk-your-openai-key-here

# Use OpenAI model names
export OPENPOKE_INTERACTION_MODEL=gpt-4-turbo
export OPENPOKE_EXECUTION_MODEL=gpt-4-turbo
export OPENPOKE_EXECUTION_SEARCH_MODEL=gpt-3.5-turbo
export OPENPOKE_SUMMARIZER_MODEL=gpt-3.5-turbo
export OPENPOKE_EMAIL_CLASSIFIER_MODEL=gpt-3.5-turbo
```

### Option 2: Use OpenRouter (Multi-Provider Access - Default)

```bash
# Set provider to OpenRouter (default)
export LLM_PROVIDER=openrouter

# Add your OpenRouter API key
export OPENROUTER_API_KEY=your-openrouter-key-here

# Model configuration (optional - these are the defaults)
export OPENPOKE_INTERACTION_MODEL=anthropic/claude-sonnet-4
export OPENPOKE_EXECUTION_MODEL=anthropic/claude-sonnet-4
export OPENPOKE_EXECUTION_SEARCH_MODEL=anthropic/claude-sonnet-4
export OPENPOKE_SUMMARIZER_MODEL=anthropic/claude-sonnet-4
export OPENPOKE_EMAIL_CLASSIFIER_MODEL=anthropic/claude-sonnet-4

# For cost optimization, use cheaper models for simpler tasks:
# export OPENPOKE_EXECUTION_SEARCH_MODEL=anthropic/claude-haiku
# export OPENPOKE_SUMMARIZER_MODEL=anthropic/claude-haiku
# export OPENPOKE_EMAIL_CLASSIFIER_MODEL=anthropic/claude-haiku
```

## Environment Variables Reference

### LLM Provider Selection

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `LLM_PROVIDER` | `openai` or `openrouter` | `openrouter` | Choose which LLM provider to use |

### API Keys

| Variable | Required When | Description |
|----------|---------------|-------------|
| `OPENAI_API_KEY` | `LLM_PROVIDER=openai` | Your OpenAI API key from https://platform.openai.com/api-keys |
| `OPENROUTER_API_KEY` | `LLM_PROVIDER=openrouter` | Your OpenRouter API key from https://openrouter.ai/keys |
| `OPENAI_BASE_URL` | Optional | Custom OpenAI-compatible endpoint (default: `https://api.openai.com/v1`) |

### Model Configuration

| Variable | Description | Default | Example (OpenAI) | Example (OpenRouter) |
|----------|-------------|---------|------------------|----------------------|
| `OPENPOKE_INTERACTION_MODEL` | Main conversation handler | `anthropic/claude-sonnet-4` | `gpt-4-turbo` | `anthropic/claude-sonnet-4` |
| `OPENPOKE_EXECUTION_MODEL` | Background task processor | `anthropic/claude-sonnet-4` | `gpt-4-turbo` | `anthropic/claude-sonnet-4` |
| `OPENPOKE_EXECUTION_SEARCH_MODEL` | Email search tasks | `anthropic/claude-sonnet-4` | `gpt-3.5-turbo` | `anthropic/claude-haiku` |
| `OPENPOKE_SUMMARIZER_MODEL` | Conversation summarization | `anthropic/claude-sonnet-4` | `gpt-3.5-turbo` | `anthropic/claude-haiku` |
| `OPENPOKE_EMAIL_CLASSIFIER_MODEL` | Email importance | `anthropic/claude-sonnet-4` | `gpt-3.5-turbo` | `anthropic/claude-haiku` |

**Note:** Defaults shown are for OpenRouter. When using OpenAI, you should set these explicitly as OpenAI model names differ.

## Cost Optimization Tips

### Using OpenAI Direct

1. **Use GPT-4 Turbo for main tasks**: Better quality for interaction and execution
2. **Use GPT-3.5 Turbo for simple tasks**: Cheaper for summarization and classification
3. **Typical savings**: 40-60% cheaper than OpenRouter for OpenAI models

Example cost-optimized configuration:
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your-key
export OPENPOKE_INTERACTION_MODEL=gpt-4-turbo
export OPENPOKE_EXECUTION_MODEL=gpt-4-turbo
export OPENPOKE_EXECUTION_SEARCH_MODEL=gpt-3.5-turbo
export OPENPOKE_SUMMARIZER_MODEL=gpt-3.5-turbo
export OPENPOKE_EMAIL_CLASSIFIER_MODEL=gpt-3.5-turbo
```

### Using OpenRouter

1. **Mix providers**: Use Claude for quality, GPT-3.5 for cost
2. **Use cheaper models**: `anthropic/claude-haiku` for simple tasks
3. **Benefit**: Access to multiple providers with one API key

Example mixed configuration:
```bash
export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY=your-key
export OPENPOKE_INTERACTION_MODEL=anthropic/claude-sonnet-4
export OPENPOKE_EXECUTION_MODEL=anthropic/claude-sonnet-4
export OPENPOKE_EXECUTION_SEARCH_MODEL=anthropic/claude-haiku
export OPENPOKE_SUMMARIZER_MODEL=openai/gpt-3.5-turbo
export OPENPOKE_EMAIL_CLASSIFIER_MODEL=anthropic/claude-haiku
```

## Switching Between Providers

You can switch providers anytime by changing the `LLM_PROVIDER` variable and updating your API keys. No code changes needed!

```bash
# Switch to OpenAI
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your-openai-key

# Switch back to OpenRouter
export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY=your-openrouter-key
```

## Using .env File

Create a `.env` file in the project root:

```bash
# .env file
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENPOKE_INTERACTION_MODEL=gpt-4-turbo
OPENPOKE_EXECUTION_MODEL=gpt-4-turbo
OPENPOKE_EXECUTION_SEARCH_MODEL=gpt-3.5-turbo
OPENPOKE_SUMMARIZER_MODEL=gpt-3.5-turbo
OPENPOKE_EMAIL_CLASSIFIER_MODEL=gpt-3.5-turbo
```

The server will automatically load these variables on startup.

## Troubleshooting

### "Missing OpenAI API key" error
- Ensure `OPENAI_API_KEY` is set when using `LLM_PROVIDER=openai`
- Check that the key starts with `sk-`

### "Missing OpenRouter API key" error
- Ensure `OPENROUTER_API_KEY` is set when using `LLM_PROVIDER=openrouter`
- Verify your key at https://openrouter.ai/keys

### Model not found
- For OpenAI: Use model names like `gpt-4-turbo`, `gpt-3.5-turbo`
- For OpenRouter: Use format `provider/model` like `anthropic/claude-sonnet-4`
- Check available models at https://openrouter.ai/models (OpenRouter) or https://platform.openai.com/docs/models (OpenAI)

## Advanced: OpenAI-Compatible APIs

You can use any OpenAI-compatible API by setting `OPENAI_BASE_URL`:

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your-key
export OPENAI_BASE_URL=https://your-custom-endpoint.com/v1
export OPENPOKE_INTERACTION_MODEL=your-model-name
```

This works with:
- Azure OpenAI
- Local LLM servers (Ollama, LM Studio, vLLM)
- Other OpenAI-compatible services
