"""MCP tool integration for execution agents."""

import asyncio
from typing import Any, Callable, Dict

from ....logging_config import logger
from ....mcp_client.registry import get_mcp_registry


async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Call an MCP tool asynchronously."""
    registry = get_mcp_registry()
    
    if not registry.is_initialized():
        return {"error": "MCP registry not initialized"}
    
    result = await registry.call_tool(tool_name, arguments)
    
    if result.success:
        return result.data
    else:
        return {"error": result.error}


def build_registry(agent_name: str) -> Dict[str, Callable[..., Any]]:
    """Build callable registry for MCP tools."""
    registry_obj = get_mcp_registry()
    
    if not registry_obj.is_initialized():
        return {}
    
    mcp_registry = {}
    tools = registry_obj.get_tools()
    
    for tool in tools:
        # Create async wrapper for each MCP tool
        async def mcp_tool_wrapper(**kwargs):
            return await call_mcp_tool(tool.name, kwargs)
        
        mcp_registry[tool.name] = mcp_tool_wrapper
    
    return mcp_registry
