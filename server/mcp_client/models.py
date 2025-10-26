"""Pydantic models for MCP protocol messages."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class MCPRequest(BaseModel):
    """MCP JSON-RPC request."""
    
    jsonrpc: str = Field(default="2.0")
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Union[str, int]


class MCPResponse(BaseModel):
    """MCP JSON-RPC response."""
    
    jsonrpc: str = Field(default="2.0")
    id: Union[str, int]
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class MCPTool(BaseModel):
    """MCP tool definition."""
    
    name: str
    description: str
    inputSchema: Dict[str, Any]


class MCPToolCall(BaseModel):
    """MCP tool call parameters."""
    
    name: str
    arguments: Dict[str, Any]


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server."""
    
    name: str
    url: str
    auth_type: Optional[str] = None  # "oauth", "api_key", None
    auth_config: Optional[Dict[str, Any]] = None
    enabled: bool = True


class MCPToolResult(BaseModel):
    """Result from MCP tool execution."""
    
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
