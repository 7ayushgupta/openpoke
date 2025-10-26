"""MCP server registry for managing multiple MCP server connections."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from functools import lru_cache

from ..logging_config import logger
from .client import MCPClient
from .models import MCPServerConfig, MCPTool, MCPToolCall, MCPToolResult


class MCPRegistry:
    """Registry for managing multiple MCP server connections and tools."""
    
    def __init__(self):
        self._servers: Dict[str, MCPServerConfig] = {}
        self._tools: Dict[str, MCPTool] = {}  # tool_name -> MCPTool
        self._server_tools: Dict[str, List[str]] = {}  # server_name -> [tool_names]
        self._initialized = False
    
    def add_server(self, config: MCPServerConfig) -> None:
        """Add an MCP server configuration."""
        self._servers[config.name] = config
        logger.info(f"Added MCP server: {config.name}")
    
    def remove_server(self, server_name: str) -> None:
        """Remove an MCP server and its tools."""
        if server_name in self._servers:
            # Remove tools from this server
            if server_name in self._server_tools:
                for tool_name in self._server_tools[server_name]:
                    if tool_name in self._tools:
                        del self._tools[tool_name]
                del self._server_tools[server_name]
            
            del self._servers[server_name]
            logger.info(f"Removed MCP server: {server_name}")
    
    def get_server(self, server_name: str) -> Optional[MCPServerConfig]:
        """Get server configuration by name."""
        return self._servers.get(server_name)
    
    def list_servers(self) -> List[MCPServerConfig]:
        """List all configured servers."""
        return list(self._servers.values())
    
    def get_tools(self) -> List[MCPTool]:
        """Get all available MCP tools."""
        return list(self._tools.values())
    
    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Get a specific tool by name."""
        return self._tools.get(tool_name)
    
    def get_tools_for_server(self, server_name: str) -> List[MCPTool]:
        """Get tools for a specific server."""
        if server_name not in self._server_tools:
            return []
        
        tool_names = self._server_tools[server_name]
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    async def initialize(self) -> None:
        """Initialize all MCP servers and discover their tools."""
        if self._initialized:
            return
        
        logger.info("Initializing MCP registry...")
        
        # Discover tools from all enabled servers
        for server_name, config in self._servers.items():
            if not config.enabled:
                logger.info(f"Skipping disabled server: {server_name}")
                continue
            
            try:
                await self._discover_server_tools(server_name, config)
            except Exception as exc:
                logger.error(
                    f"Failed to initialize server {server_name}",
                    extra={"error": str(exc)}
                )
                continue
        
        self._initialized = True
        logger.info(
            f"MCP registry initialized with {len(self._tools)} tools from {len(self._servers)} servers"
        )
    
    async def _discover_server_tools(self, server_name: str, config: MCPServerConfig) -> None:
        """Discover tools from a specific MCP server."""
        try:
            async with MCPClient(config) as client:
                # Test connection
                if not await client.test_connection():
                    logger.warning(f"Server {server_name} connection test failed")
                    return
                
                # Discover tools
                tools = await client.list_tools()
                
                # Store tools with server prefix
                server_tool_names = []
                for tool in tools:
                    prefixed_name = f"mcp_{server_name}_{tool.name}"
                    
                    # Create a copy with prefixed name
                    prefixed_tool = MCPTool(
                        name=prefixed_name,
                        description=tool.description,
                        inputSchema=tool.inputSchema,
                    )
                    
                    self._tools[prefixed_name] = prefixed_tool
                    server_tool_names.append(prefixed_name)
                
                self._server_tools[server_name] = server_tool_names
                
                logger.info(
                    f"Discovered {len(tools)} tools from server {server_name}",
                    extra={
                        "server": server_name,
                        "tool_count": len(tools),
                        "tools": [tool.name for tool in tools],
                    }
                )
                
        except Exception as exc:
            logger.error(
                f"Failed to discover tools from server {server_name}",
                extra={"error": str(exc)}
            )
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Call a tool by its prefixed name."""
        if tool_name not in self._tools:
            return MCPToolResult(
                success=False,
                error=f"Tool {tool_name} not found"
            )
        
        # Extract server name and original tool name
        if not tool_name.startswith("mcp_"):
            return MCPToolResult(
                success=False,
                error=f"Invalid tool name format: {tool_name}"
            )
        
        parts = tool_name.split("_", 2)
        if len(parts) < 3:
            return MCPToolResult(
                success=False,
                error=f"Invalid tool name format: {tool_name}"
            )
        
        server_name = parts[1]
        original_tool_name = parts[2]
        
        if server_name not in self._servers:
            return MCPToolResult(
                success=False,
                error=f"Server {server_name} not found"
            )
        
        config = self._servers[server_name]
        if not config.enabled:
            return MCPToolResult(
                success=False,
                error=f"Server {server_name} is disabled"
            )
        
        try:
            async with MCPClient(config) as client:
                tool_call = MCPToolCall(
                    name=original_tool_name,
                    arguments=arguments,
                )
                return await client.call_tool(tool_call)
                
        except Exception as exc:
            logger.error(
                f"Failed to call tool {tool_name}",
                extra={
                    "tool": tool_name,
                    "server": server_name,
                    "error": str(exc),
                }
            )
            return MCPToolResult(
                success=False,
                error=f"Tool call failed: {exc}"
            )
    
    async def refresh_server(self, server_name: str) -> bool:
        """Refresh tools from a specific server."""
        if server_name not in self._servers:
            return False
        
        config = self._servers[server_name]
        
        # Remove existing tools from this server
        if server_name in self._server_tools:
            for tool_name in self._server_tools[server_name]:
                if tool_name in self._tools:
                    del self._tools[tool_name]
            del self._server_tools[server_name]
        
        try:
            await self._discover_server_tools(server_name, config)
            return True
        except Exception as exc:
            logger.error(
                f"Failed to refresh server {server_name}",
                extra={"error": str(exc)}
            )
            return False
    
    def is_initialized(self) -> bool:
        """Check if the registry has been initialized."""
        return self._initialized


@lru_cache(maxsize=1)
def get_mcp_registry() -> MCPRegistry:
    """Get cached MCP registry instance."""
    return MCPRegistry()
