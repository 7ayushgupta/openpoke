# OpenPoke Documentation

This directory contains documentation for setting up, configuring, and deploying OpenPoke.

## 📚 Documentation Index

### Setup & Configuration

- **[ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)** - Complete reference for all environment variables
  - Required vs optional variables
  - Development vs production values
  - Security best practices
  - Example `.env` file structure

- **[LLM_PROVIDER_SETUP.md](./LLM_PROVIDER_SETUP.md)** - How to configure LLM providers
  - OpenRouter vs OpenAI
  - Model selection
  - Cost optimization tips
  - Switching between providers

### Deployment & Infrastructure

- **[HTTPS_SETUP.md](./HTTPS_SETUP.md)** - Complete HTTPS/TLS setup guide
  - Caddy setup (automatic HTTPS)
  - Nginx setup (manual configuration)
  - Cloud load balancer options
  - Let's Encrypt certificate setup
  - Security headers configuration

- **[LOCALHOST_TUNNELING.md](./LOCALHOST_TUNNELING.md)** - Make localhost accessible online
  - ngrok setup (recommended)
  - Cloudflare Tunnel
  - localtunnel
  - Testing OAuth flows
  - Sharing demos

### Security

- **[SECURITY_AUDIT.md](./SECURITY_AUDIT.md)** - Comprehensive security audit report
  - All identified security issues
  - Attack scenarios and impact assessments
  - Fix recommendations
  - Deployment checklist
  - Note: Many security fixes have already been implemented. See codebase for current status.

### Architecture & Design

- **[web_app_architecture.md](./web_app_architecture.md)** - System architecture documentation
  - Frontend and backend architecture
  - Component breakdown
  - Data flow diagrams
  - Technology stack

- **[shloks_blog.md](./shloks_blog.md)** - Original blog post about OpenPoke
  - Architecture explanation
  - Design decisions
  - Insights for builders
  - Note: This is historical documentation from the original implementation

## 🚀 Quick Start

1. Start with the main [README.md](../README.md) in the project root
2. Set up environment variables using [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)
3. Configure your LLM provider using [LLM_PROVIDER_SETUP.md](./LLM_PROVIDER_SETUP.md)
4. For production deployment, see [HTTPS_SETUP.md](./HTTPS_SETUP.md)

## 📝 Documentation Status

- ✅ **ENVIRONMENT_VARIABLES.md** - Up to date
- ✅ **LLM_PROVIDER_SETUP.md** - Up to date
- ✅ **HTTPS_SETUP.md** - Up to date
- ✅ **LOCALHOST_TUNNELING.md** - Up to date
- ✅ **web_app_architecture.md** - Up to date
- ⚠️ **SECURITY_AUDIT.md** - Historical reference (security fixes have been implemented)
- 📜 **shloks_blog.md** - Historical documentation

## 🔗 Related Resources

- [Main README](../README.md) - Project overview and quickstart
- [LICENSE](../LICENSE) - MIT License
- [GitHub Repository](https://github.com/shlokkhemani/OpenPoke) - Source code

