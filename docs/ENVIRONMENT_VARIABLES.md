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
OAUTH_REDIRECT_URI=http://localhost:3000/auth/callback

# LLM Provider
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-...

# Composio (Gmail)
COMPOSIO_API_KEY=your-composio-key
COMPOSIO_GMAIL_AUTH_CONFIG_ID=your-config-id

# Server Configuration (optional)
OPENPOKE_HOST=0.0.0.0
OPENPOKE_PORT=8001
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

