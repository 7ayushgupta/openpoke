"""Core MCP HTTP client implementation."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from ..logging_config import logger
from .models import MCPRequest, MCPResponse, MCPTool, MCPToolCall, MCPToolResult, MCPServerConfig


class MCPClientError(Exception):
    """Raised when MCP client operations fail."""


class MCPClient:
    """HTTP-based MCP client for communicating with MCP servers."""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for MCP requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        # Add auth headers if configured
        if self.config.auth_type == "api_key" and self.config.auth_config:
            api_key = self.config.auth_config.get("api_key")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        
        return headers
    
    async def _make_request(self, request: MCPRequest) -> MCPResponse:
        """Make a JSON-RPC request to the MCP server."""
        if not self._client:
            raise MCPClientError("Client not initialized. Use async context manager.")
        
        if not self.config.enabled:
            raise MCPClientError(f"Server {self.config.name} is disabled")
        
        try:
            logger.debug(
                "Making MCP request",
                extra={
                    "server": self.config.name,
                    "method": request.method,
                    "url": self.config.url,
                }
            )
            
            response = await self._client.post(
                self.config.url,
                headers=self._get_headers(),
                json=request.model_dump(),
            )
            
            logger.debug(
                "MCP response received",
                extra={
                    "server": self.config.name,
                    "status_code": response.status_code,
                    "method": request.method,
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            return MCPResponse(**data)
            
        except httpx.HTTPStatusError as exc:
            logger.error(
                "MCP server returned error status",
                extra={
                    "server": self.config.name,
                    "status_code": exc.response.status_code,
                    "response_text": exc.response.text[:500],
                }
            )
            raise MCPClientError(f"MCP server error ({exc.response.status_code}): {exc.response.text}") from exc
            
        except httpx.HTTPError as exc:
            logger.error(
                "MCP HTTP error",
                extra={
                    "server": self.config.name,
                    "error": str(exc),
                    "url": self.config.url,
                }
            )
            raise MCPClientError(f"MCP request failed: {exc}") from exc
            
        except json.JSONDecodeError as exc:
            logger.error(
                "MCP response JSON decode error",
                extra={
                    "server": self.config.name,
                    "error": str(exc),
                }
            )
            raise MCPClientError(f"Invalid JSON response: {exc}") from exc
    
    async def list_tools(self) -> List[MCPTool]:
        """Discover available tools from the MCP server."""
        request = MCPRequest(
            method="tools/list",
            id=1,
        )
        
        try:
            response = await self._make_request(request)
            
            if response.error:
                raise MCPClientError(f"MCP tools/list error: {response.error}")
            
            if not response.result:
                logger.warning(
                    "MCP server returned empty tools list",
                    extra={"server": self.config.name}
                )
                return []
            
            tools_data = response.result.get("tools", [])
            tools = []
            
            for tool_data in tools_data:
                try:
                    tool = MCPTool(**tool_data)
                    tools.append(tool)
                except Exception as exc:
                    logger.warning(
                        "Failed to parse MCP tool",
                        extra={
                            "server": self.config.name,
                            "tool_data": tool_data,
                            "error": str(exc),
                        }
                    )
                    continue
            
            logger.info(
                "Discovered MCP tools",
                extra={
                    "server": self.config.name,
                    "tool_count": len(tools),
                }
            )
            
            return tools
            
        except Exception as exc:
            logger.error(
                "Failed to list MCP tools",
                extra={
                    "server": self.config.name,
                    "error": str(exc),
                }
            )
            raise MCPClientError(f"Failed to list tools from {self.config.name}: {exc}") from exc
    
    async def call_tool(self, tool_call: MCPToolCall) -> MCPToolResult:
        """Execute a tool call on the MCP server."""
        request = MCPRequest(
            method="tools/call",
            params={
                "name": tool_call.name,
                "arguments": tool_call.arguments,
            },
            id=2,
        )
        
        try:
            logger.debug(
                "Calling MCP tool",
                extra={
                    "server": self.config.name,
                    "tool": tool_call.name,
                    "arguments": tool_call.arguments,
                }
            )
            
            response = await self._make_request(request)
            
            if response.error:
                error_msg = response.error.get("message", "Unknown error")
                logger.error(
                    "MCP tool call error",
                    extra={
                        "server": self.config.name,
                        "tool": tool_call.name,
                        "error": error_msg,
                    }
                )
                return MCPToolResult(
                    success=False,
                    error=f"MCP tool error: {error_msg}"
                )
            
            result_data = response.result or {}
            
            logger.debug(
                "MCP tool call successful",
                extra={
                    "server": self.config.name,
                    "tool": tool_call.name,
                }
            )
            
            return MCPToolResult(
                success=True,
                data=result_data,
            )
            
        except Exception as exc:
            logger.error(
                "MCP tool call failed",
                extra={
                    "server": self.config.name,
                    "tool": tool_call.name,
                    "error": str(exc),
                }
            )
            return MCPToolResult(
                success=False,
                error=f"Tool call failed: {exc}"
            )
    
    async def test_connection(self) -> bool:
        """Test connection to the MCP server."""
        try:
            # Try to list tools as a connection test
            await self.list_tools()
            return True
        except Exception as exc:
            logger.warning(
                "MCP connection test failed",
                extra={
                    "server": self.config.name,
                    "error": str(exc),
                }
            )
            return False
