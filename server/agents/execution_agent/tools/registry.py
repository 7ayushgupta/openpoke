"""Aggregate execution agent tool schemas and registries."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from . import gmail, triggers, mcp
from ..tasks import get_task_registry, get_task_schemas


# Return OpenAI/OpenRouter-compatible tool schemas
def get_tool_schemas() -> List[Dict[str, Any]]:
    """Return OpenAI/OpenRouter-compatible tool schemas."""
    schemas = [
        *gmail.get_schemas(),
        *get_task_schemas(),
        *triggers.get_schemas(),
    ]
    
    # Add MCP tools dynamically
    try:
        from ...mcp_client.registry import get_mcp_registry
        registry = get_mcp_registry()
        if registry.is_initialized():
            mcp_tools = registry.get_tools()
            for tool in mcp_tools:
                schema = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    },
                }
                schemas.append(schema)
    except Exception:
        pass  # MCP tools are optional
    
    return schemas


# Return Python callables for executing tools by name
def get_tool_registry(agent_name: str, user_id: str = "") -> Dict[str, Callable[..., Any]]:
    """Return Python callables for executing tools by name."""

    registry: Dict[str, Callable[..., Any]] = {}
    registry.update(gmail.build_registry(agent_name, user_id))
    registry.update(get_task_registry(agent_name))
    registry.update(triggers.build_registry(agent_name, user_id))
    registry.update(mcp.build_registry(agent_name))  # Add MCP tools
    return registry


__all__ = [
    "get_tool_registry",
    "get_tool_schemas",
]
