"""Simplified configuration management."""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _load_env_file() -> None:
    """Load .env from root directory if present."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.is_file():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key, value = stripped.split("=", 1)
                key, value = key.strip(), value.strip().strip("'\"")
                if key and value and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        pass


_load_env_file()


DEFAULT_APP_NAME = "OpenPoke Server"
DEFAULT_APP_VERSION = "0.3.0"


def _env_int(name: str, fallback: int) -> int:
    try:
        return int(os.getenv(name, str(fallback)))
    except (TypeError, ValueError):
        return fallback


def _env_json_list(name: str, fallback: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse JSON list from environment variable."""
    value = os.getenv(name)
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return fallback


class Settings(BaseModel):
    """Application settings with lightweight env fallbacks."""

    # App metadata
    app_name: str = Field(default=DEFAULT_APP_NAME)
    app_version: str = Field(default=DEFAULT_APP_VERSION)

    # Server runtime
    server_host: str = Field(default=os.getenv("OPENPOKE_HOST", "0.0.0.0"))
    server_port: int = Field(default=_env_int("OPENPOKE_PORT", 8001))

    # LLM model selection
    interaction_agent_model: str = Field(default=os.getenv("OPENPOKE_INTERACTION_MODEL", "anthropic/claude-sonnet-4"))
    execution_agent_model: str = Field(default=os.getenv("OPENPOKE_EXECUTION_MODEL", "anthropic/claude-sonnet-4"))
    execution_agent_search_model: str = Field(default=os.getenv("OPENPOKE_EXECUTION_SEARCH_MODEL", "anthropic/claude-sonnet-4"))
    summarizer_model: str = Field(default=os.getenv("OPENPOKE_SUMMARIZER_MODEL", "anthropic/claude-sonnet-4"))
    email_classifier_model: str = Field(default=os.getenv("OPENPOKE_EMAIL_CLASSIFIER_MODEL", "anthropic/claude-sonnet-4"))

    # LLM Provider Configuration
    llm_provider: str = Field(default=os.getenv("LLM_PROVIDER", "openrouter"))
    
    # Credentials / integrations
    openrouter_api_key: Optional[str] = Field(default=os.getenv("OPENROUTER_API_KEY"))
    openai_api_key: Optional[str] = Field(default=os.getenv("OPENAI_API_KEY"))
    openai_base_url: str = Field(default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    composio_gmail_auth_config_id: Optional[str] = Field(default=os.getenv("COMPOSIO_GMAIL_AUTH_CONFIG_ID"))
    composio_api_key: Optional[str] = Field(default=os.getenv("COMPOSIO_API_KEY"))

    # HTTP behaviour
    cors_allow_origins_raw: str = Field(default=os.getenv("OPENPOKE_CORS_ALLOW_ORIGINS", "http://localhost:3000,http://localhost:8001"))
    enable_docs: bool = Field(default=os.getenv("OPENPOKE_ENABLE_DOCS", "1") != "0")
    docs_url: Optional[str] = Field(default=os.getenv("OPENPOKE_DOCS_URL", "/docs"))

    # Summarisation controls
    conversation_summary_threshold: int = Field(default=100)
    conversation_summary_tail_size: int = Field(default=10)

    # Execution and interaction agent settings
    execution_batch_timeout_seconds: int = Field(default=_env_int("OPENPOKE_EXECUTION_TIMEOUT", 90))
    max_tool_iterations: int = Field(default=_env_int("OPENPOKE_MAX_TOOL_ITERATIONS", 8))
    
    # HTTP client settings
    http_client_max_keepalive: int = Field(default=_env_int("OPENPOKE_HTTP_MAX_KEEPALIVE", 10))
    http_client_max_connections: int = Field(default=_env_int("OPENPOKE_HTTP_MAX_CONNECTIONS", 20))

    # MCP server configuration
    mcp_servers: List[Dict[str, Any]] = Field(
        default_factory=lambda: _env_json_list("OPENPOKE_MCP_SERVERS", [])
    )

    # Multi-user settings
    default_user_id: str = Field(default=os.getenv("DEFAULT_USER_ID", "admin"))

    # OAuth configuration
    oauth_google_client_id: Optional[str] = Field(default=os.getenv("OAUTH_GOOGLE_CLIENT_ID"))
    oauth_google_client_secret: Optional[str] = Field(default=os.getenv("OAUTH_GOOGLE_CLIENT_SECRET"))
    oauth_redirect_uri: str = Field(default=os.getenv("OAUTH_REDIRECT_URI", "http://localhost:3000/api/v1/auth/callback"))
    jwt_secret_key: Optional[str] = Field(default=os.getenv("JWT_SECRET_KEY"))

    @property
    def cors_allow_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_allow_origins_raw.strip() in {"", "*"}:
            return ["*"]
        return [origin.strip() for origin in self.cors_allow_origins_raw.split(",") if origin.strip()]

    @property
    def resolved_docs_url(self) -> Optional[str]:
        """Return documentation URL when docs are enabled."""
        return (self.docs_url or "/docs") if self.enable_docs else None

    @property
    def summarization_enabled(self) -> bool:
        """Flag indicating conversation summarisation is active."""
        return self.conversation_summary_threshold > 0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
