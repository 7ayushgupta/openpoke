# Environment Variables Configuration

This document explains all environment variables used by OpenPoke.

## 🔴 Critical (Required for Production)

### ENVIRONMENT
- **Default:** `development`
- **Production value:** `production`
- **Description:** Controls security features. Many security checks only activate when set to `production`.

```bash
export ENVIRONMENT=production
```

### JWT_SECRET_KEY
- **Default:** Auto-generated (development only)
- **Production:** REQUIRED - must be set manually
- **Description:** Secret key for signing JWT tokens. Must be consistent across server restarts and instances.

```bash
# Generate a secure key:
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# Set it:
export JWT_SECRET_KEY='your-generated-key-here'
```

### OPENPOKE_CORS_ALLOW_ORIGINS
- **Default:** `http://localhost:3000,http://localhost:8001`
- **Production value:** Your actual domain(s)
- **Description:** Comma-separated list of allowed CORS origins (no spaces!)

```bash
# Development:
export OPENPOKE_CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:8001

# Production:
export OPENPOKE_CORS_ALLOW_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

---

## 🟠 OAuth Configuration (Required for Login)

### OAUTH_GOOGLE_CLIENT_ID
- **Required:** Yes
- **Get from:** Google Cloud Console
- **Description:** Google OAuth client ID

### OAUTH_GOOGLE_CLIENT_SECRET
- **Required:** Yes
- **Get from:** Google Cloud Console
- **Description:** Google OAuth client secret

### OAUTH_REDIRECT_URI
- **Default:** `http://localhost:3000/api/v1/auth/callback`
- **Production value:** `https://yourdomain.com/api/v1/auth/callback`
- **Description:** OAuth callback URL (must match Google Console configuration)

---

## 🟡 LLM Provider Configuration

### LLM_PROVIDER
- **Default:** `openrouter`
- **Options:** `openrouter` or `openai`
- **Description:** Which LLM provider to use

### OPENROUTER_API_KEY
- **Required:** If using OpenRouter
- **Get from:** [openrouter.ai](https://openrouter.ai)
- **Description:** OpenRouter API key

### OPENAI_API_KEY
- **Required:** If using OpenAI directly
- **Get from:** [platform.openai.com](https://platform.openai.com)
- **Description:** OpenAI API key

### OPENAI_BASE_URL
- **Default:** `https://api.openai.com/v1`
- **Optional:** Custom OpenAI-compatible endpoint
- **Description:** Base URL for OpenAI API. Use for Azure OpenAI, local LLM servers, or other OpenAI-compatible services

---

## 🤖 LLM Model Configuration

Configure which models to use for different tasks. These can be set per-provider.

### OPENPOKE_INTERACTION_MODEL
- **Default:** `anthropic/claude-sonnet-4` (OpenRouter) or `gpt-4-turbo` (OpenAI)
- **Description:** Model used by the Interaction Agent (main chat interface)
- **Examples:**
  - OpenRouter: `anthropic/claude-sonnet-4`, `openai/gpt-4-turbo`, `meta-llama/llama-3.3-70b-instruct`
  - OpenAI: `gpt-4-turbo`, `gpt-4o`, `gpt-3.5-turbo`

### OPENPOKE_EXECUTION_MODEL
- **Default:** `anthropic/claude-sonnet-4` (OpenRouter) or `gpt-4-turbo` (OpenAI)
- **Description:** Model used by Execution Agents for task execution
- **Examples:**
  - OpenRouter: `anthropic/claude-sonnet-4`, `anthropic/claude-3.5-sonnet`
  - OpenAI: `gpt-4-turbo`, `gpt-4o`

### OPENPOKE_EXECUTION_SEARCH_MODEL
- **Default:** `anthropic/claude-sonnet-4` (OpenRouter) or `gpt-3.5-turbo` (OpenAI)
- **Description:** Model used for email search and simple tasks (cost optimization)
- **Examples:**
  - OpenRouter: `anthropic/claude-haiku`, `openai/gpt-3.5-turbo`
  - OpenAI: `gpt-3.5-turbo`

### OPENPOKE_SUMMARIZER_MODEL
- **Default:** `anthropic/claude-sonnet-4` (OpenRouter) or `gpt-3.5-turbo` (OpenAI)
- **Description:** Model used for conversation summarization (cost optimization)
- **Examples:**
  - OpenRouter: `anthropic/claude-haiku`, `openai/gpt-3.5-turbo`
  - OpenAI: `gpt-3.5-turbo`

### OPENPOKE_EMAIL_CLASSIFIER_MODEL
- **Default:** `anthropic/claude-sonnet-4` (OpenRouter) or `gpt-3.5-turbo` (OpenAI)
- **Description:** Model used for email importance classification (cost optimization)
- **Examples:**
  - OpenRouter: `anthropic/claude-haiku`, `openai/gpt-3.5-turbo`
  - OpenAI: `gpt-3.5-turbo`

---

## 🟢 Composio Configuration (Gmail)

### COMPOSIO_API_KEY
- **Required:** For Gmail features
- **Get from:** [composio.dev](https://composio.dev)
- **Description:** Composio API key

### COMPOSIO_GMAIL_AUTH_CONFIG_ID
- **Required:** For Gmail features
- **Get from:** Composio dashboard
- **Description:** Gmail auth configuration ID

---

## ⚙️ Server Configuration (Optional)

### OPENPOKE_HOST
- **Default:** `0.0.0.0`
- **Description:** Host address to bind the server to
- **Note:** Use `0.0.0.0` to listen on all interfaces, or `127.0.0.1` for localhost only

### OPENPOKE_PORT
- **Default:** `8001`
- **Description:** Port number for the FastAPI server

### OPENPOKE_ENABLE_DOCS
- **Default:** `1` (enabled)
- **Values:** `1` (enabled) or `0` (disabled)
- **Description:** Enable/disable FastAPI interactive documentation (Swagger UI)
- **Production:** Recommended to set to `0` for security

### OPENPOKE_DOCS_URL
- **Default:** `/docs`
- **Description:** URL path for FastAPI documentation
- **Note:** Only applies if `OPENPOKE_ENABLE_DOCS=1`

---

## 🔧 Advanced Configuration (Optional)

### OPENPOKE_EXECUTION_TIMEOUT
- **Default:** `90`
- **Description:** Maximum timeout in seconds for execution agent batches
- **Unit:** Seconds

### OPENPOKE_MAX_TOOL_ITERATIONS
- **Default:** `8`
- **Description:** Maximum number of tool call iterations per execution agent
- **Note:** Prevents infinite loops from agents stuck in reasoning loops

### OPENPOKE_HTTP_MAX_KEEPALIVE
- **Default:** `10`
- **Description:** Maximum number of keepalive connections in HTTP client pool

### OPENPOKE_HTTP_MAX_CONNECTIONS
- **Default:** `20`
- **Description:** Maximum number of concurrent connections in HTTP client pool

### OPENPOKE_MCP_SERVERS
- **Default:** `[]` (empty)
- **Format:** JSON array
- **Description:** MCP (Model Context Protocol) server configurations
- **Example:**
  ```json
  [
    {
      "name": "notion",
      "url": "https://mcp-server.example.com",
      "auth_type": "api_key",
      "api_key": "your-api-key"
    }
  ]
  ```

### DEFAULT_USER_ID
- **Default:** `admin`
- **Description:** Default user ID for single-user deployments
- **Note:** In multi-user deployments, this is typically set per-session via OAuth

---

## Example .env File

Create a `.env` file in the project root:

```bash
# Critical Security Settings
ENVIRONMENT=development
JWT_SECRET_KEY=your-generated-secret-key-here

# CORS Configuration
OPENPOKE_CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:8001

# OAuth Configuration
OAUTH_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
OAUTH_GOOGLE_CLIENT_SECRET=your-client-secret
OAUTH_REDIRECT_URI=http://localhost:3000/api/v1/auth/callback

# LLM Provider
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-...

# Composio (Gmail)
COMPOSIO_API_KEY=your-composio-key
COMPOSIO_GMAIL_AUTH_CONFIG_ID=your-config-id

# Server Configuration (optional)
OPENPOKE_HOST=0.0.0.0
OPENPOKE_PORT=8001

# LLM Model Configuration (optional - uses defaults if not set)
# OPENPOKE_INTERACTION_MODEL=anthropic/claude-sonnet-4
# OPENPOKE_EXECUTION_MODEL=anthropic/claude-sonnet-4
# OPENPOKE_EXECUTION_SEARCH_MODEL=anthropic/claude-haiku
# OPENPOKE_SUMMARIZER_MODEL=anthropic/claude-haiku
# OPENPOKE_EMAIL_CLASSIFIER_MODEL=anthropic/claude-haiku
```

---

## Production Checklist

Before deploying to production:

- [ ] Set `ENVIRONMENT=production`
- [ ] Generate and set `JWT_SECRET_KEY`
- [ ] Update `OPENPOKE_CORS_ALLOW_ORIGINS` with your domain(s)
- [ ] Update `OAUTH_REDIRECT_URI` with your domain
- [ ] Store secrets in a secure secrets manager
- [ ] Never commit `.env` file to git

---

## Security Best Practices

1. **Never commit secrets to git**
   - Add `.env` to `.gitignore`
   - Use environment-specific files (.env.development, .env.production)

2. **Use a secrets manager in production**
   - AWS Secrets Manager
   - Google Cloud Secret Manager
   - Azure Key Vault
   - HashiCorp Vault

3. **Rotate secrets regularly**
   - JWT_SECRET_KEY: Every 90 days
   - API keys: Every 180 days or when compromised

4. **Use different secrets per environment**
   - Development, staging, and production should have different keys
   - Never use production secrets in development

