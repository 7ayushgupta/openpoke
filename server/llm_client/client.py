"""Unified LLM client that routes to OpenAI or OpenRouter based on configuration."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import httpx

from ..config import get_settings
from ..logging_config import logger


class LLMError(RuntimeError):
    """Raised when an LLM API request fails."""


# Shared HTTP client with connection pooling
_http_client: Optional[httpx.AsyncClient] = None


def _get_http_client() -> httpx.AsyncClient:
    """Get or create the shared HTTP client with connection pooling."""
    global _http_client
    if _http_client is None:
        settings = get_settings()
        _http_client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(
                max_keepalive_connections=settings.http_client_max_keepalive,
                max_connections=settings.http_client_max_connections,
            ),
        )
    return _http_client


async def _close_http_client() -> None:
    """Close the shared HTTP client. Should be called on application shutdown."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


def _get_provider() -> str:
    """Get the configured LLM provider."""
    settings = get_settings()
    provider = settings.llm_provider.lower()
    if provider not in ["openai", "openrouter"]:
        logger.warning(f"Unknown LLM provider '{provider}', defaulting to 'openrouter'")
        return "openrouter"
    return provider


def _log_provider_initialization() -> None:
    """Log the LLM provider configuration at startup."""
    settings = get_settings()
    provider = _get_provider()
    
    # Check if API key is configured
    api_key_configured = False
    if provider == "openai":
        api_key_configured = bool(settings.openai_api_key)
        api_key_status = "✅ Configured" if api_key_configured else "❌ Missing"
        logger.info(f"🤖 LLM Provider: OpenAI | API Key: {api_key_status}")
        if api_key_configured:
            logger.info(f"🔗 OpenAI Base URL: {settings.openai_base_url}")
    else:  # openrouter
        api_key_configured = bool(settings.openrouter_api_key)
        api_key_status = "✅ Configured" if api_key_configured else "❌ Missing"
        logger.info(f"🤖 LLM Provider: OpenRouter | API Key: {api_key_status}")
    
    # Log model configuration
    logger.info(f"📝 Model Configuration:")
    logger.info(f"   • Interaction Agent: {settings.interaction_agent_model}")
    logger.info(f"   • Execution Agent: {settings.execution_agent_model}")
    logger.info(f"   • Email Search: {settings.execution_agent_search_model}")
    logger.info(f"   • Summarizer: {settings.summarizer_model}")
    logger.info(f"   • Email Classifier: {settings.email_classifier_model}")
    
    if not api_key_configured:
        if provider == "openai":
            logger.error("❌ OPENAI_API_KEY environment variable is required when using OpenAI provider")
            logger.error("💡 Add 'OPENAI_API_KEY=sk-your-key-here' to your .env file")
        else:
            logger.error("❌ OPENROUTER_API_KEY environment variable is required when using OpenRouter provider")
            logger.error("💡 Add 'OPENROUTER_API_KEY=your-key-here' to your .env file")
        logger.info("💡 Or switch providers by setting 'LLM_PROVIDER=openai' or 'LLM_PROVIDER=openrouter'")


def _normalize_model_name(model: str, provider: str) -> str:
    """Normalize model name based on provider."""
    if provider == "openai":
        # Strip provider prefixes for OpenAI (e.g., "anthropic/claude-sonnet-4" -> "claude-sonnet-4")
        # But keep OpenAI model names as-is
        if "/" in model and not model.startswith("gpt"):
            parts = model.split("/", 1)
            normalized = parts[1] if len(parts) > 1 else model
            logger.debug(f"Normalized model name from '{model}' to '{normalized}' for OpenAI")
            return normalized
    return model


def _build_messages(messages: List[Dict[str, str]], system: Optional[str]) -> List[Dict[str, str]]:
    """Build message list with optional system message."""
    if system:
        return [{"role": "system", "content": system}, *messages]
    return messages


def _handle_response_error(exc: httpx.HTTPStatusError, provider: str) -> None:
    """Handle HTTP error responses from LLM providers."""
    response = exc.response
    detail: str
    try:
        payload = response.json()
        detail = payload.get("error") or payload.get("message") or json.dumps(payload)
    except Exception:
        detail = response.text
    raise LLMError(f"{provider.title()} request failed ({response.status_code}): {detail}") from exc


async def _openai_request(
    *,
    model: str,
    messages: List[Dict[str, str]],
    system: Optional[str] = None,
    api_key: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    base_url: str,
) -> Dict[str, Any]:
    """Make a request to OpenAI API."""
    settings = get_settings()
    key = (api_key or settings.openai_api_key or "").strip()
    if not key:
        raise LLMError("Missing OpenAI API key. Set OPENAI_API_KEY environment variable.")

    normalized_model = _normalize_model_name(model, "openai")
    
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload: Dict[str, object] = {
        "model": normalized_model,
        "messages": _build_messages(messages, system),
        "stream": False,
    }
    
    if tools:
        payload["tools"] = tools

    url = f"{base_url.rstrip('/')}/chat/completions"
    
    logger.debug(
        "Making OpenAI API request",
        extra={
            "model": normalized_model,
            "original_model": model,
            "message_count": len(messages),
            "has_system": bool(system),
            "tool_count": len(tools) if tools else 0,
        }
    )

    client = _get_http_client()
    try:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )
        logger.debug(
            "OpenAI API response received",
            extra={
                "status_code": response.status_code,
                "response_size": len(response.content),
                "model": normalized_model
            }
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "OpenAI API returned error status",
            extra={
                "status_code": exc.response.status_code,
                "model": normalized_model,
                "response_text": exc.response.text[:500]
            }
        )
        _handle_response_error(exc, "openai")
    except httpx.HTTPError as exc:
        logger.error(
            "OpenAI HTTP error",
            extra={
                "error": str(exc),
                "model": normalized_model,
                "url": url
            }
        )
        raise LLMError(f"OpenAI request failed: {exc}") from exc


async def _openrouter_request(
    *,
    model: str,
    messages: List[Dict[str, str]],
    system: Optional[str] = None,
    api_key: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Make a request to OpenRouter API."""
    settings = get_settings()
    key = (api_key or settings.openrouter_api_key or "").strip()
    if not key:
        raise LLMError("Missing OpenRouter API key. Set OPENROUTER_API_KEY environment variable.")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload: Dict[str, object] = {
        "model": model,
        "messages": _build_messages(messages, system),
        "stream": False,
    }
    
    if tools:
        payload["tools"] = tools

    url = "https://openrouter.ai/api/v1/chat/completions"
    
    logger.debug(
        "Making OpenRouter API request",
        extra={
            "model": model,
            "message_count": len(messages),
            "has_system": bool(system),
            "tool_count": len(tools) if tools else 0,
        }
    )

    client = _get_http_client()
    try:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )
        logger.debug(
            "OpenRouter API response received",
            extra={
                "status_code": response.status_code,
                "response_size": len(response.content),
                "model": model
            }
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "OpenRouter API returned error status",
            extra={
                "status_code": exc.response.status_code,
                "model": model,
                "response_text": exc.response.text[:500]
            }
        )
        _handle_response_error(exc, "openrouter")
    except httpx.HTTPError as exc:
        logger.error(
            "OpenRouter HTTP error",
            extra={
                "error": str(exc),
                "model": model,
                "url": url
            }
        )
        raise LLMError(f"OpenRouter request failed: {exc}") from exc


async def request_chat_completion(
    *,
    model: str,
    messages: List[Dict[str, str]],
    system: Optional[str] = None,
    api_key: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Request a chat completion from the configured LLM provider.
    
    Routes to OpenAI or OpenRouter based on LLM_PROVIDER environment variable.
    
    Args:
        model: Model name (e.g., "gpt-4-turbo" or "anthropic/claude-sonnet-4")
        messages: List of message dictionaries with "role" and "content"
        system: Optional system message
        api_key: Optional API key override
        tools: Optional list of tool definitions
        base_url: Optional base URL override (for OpenAI-compatible APIs)
    
    Returns:
        Raw JSON response from the LLM provider
    
    Raises:
        LLMError: If the request fails
    """
    provider = _get_provider()
    settings = get_settings()
    
    logger.info(
        f"Routing LLM request to {provider}",
        extra={
            "provider": provider,
            "model": model,
            "message_count": len(messages),
            "has_tools": bool(tools)
        }
    )
    
    if provider == "openai":
        effective_base_url = base_url or settings.openai_base_url
        return await _openai_request(
            model=model,
            messages=messages,
            system=system,
            api_key=api_key,
            tools=tools,
            base_url=effective_base_url,
        )
    else:  # openrouter
        return await _openrouter_request(
            model=model,
            messages=messages,
            system=system,
            api_key=api_key,
            tools=tools,
        )


__all__ = ["request_chat_completion", "LLMError", "_close_http_client"]
