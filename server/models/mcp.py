"""Pydantic models for MCP requests and responses."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MCPConnectPayload(BaseModel):
    """Payload for connecting to an MCP server."""
    
    server_name: str = Field(..., description="Name of the MCP server")
    url: str = Field(..., description="URL of the MCP server")
    auth_type: Optional[str] = Field(default=None, description="Authentication type: 'oauth', 'api_key', or None")
    auth_config: Optional[Dict[str, Any]] = Field(default=None, description="Authentication configuration")


class MCPDisconnectPayload(BaseModel):
    """Payload for disconnecting from an MCP server."""
    
    server_name: str = Field(..., description="Name of the MCP server to disconnect")


class MCPServerResponse(BaseModel):
    """Response containing MCP server information."""
    
    name: str
    url: str
    auth_type: Optional[str] = None
    enabled: bool = True
    tool_count: int = 0


class MCPServerListResponse(BaseModel):
    """Response containing list of MCP servers."""
    
    servers: List[MCPServerResponse] = Field(default_factory=list)


class MCPToolResponse(BaseModel):
    """Response containing MCP tool information."""
    
    name: str
    description: str
    server_name: str
    input_schema: Dict[str, Any]


class MCPToolListResponse(BaseModel):
    """Response containing list of MCP tools."""
    
    tools: List[MCPToolResponse] = Field(default_factory=list)


class MCPAuthPayload(BaseModel):
    """Payload for MCP authentication."""
    
    server_name: str = Field(..., description="Name of the MCP server")
    auth_config: Dict[str, Any] = Field(..., description="Authentication configuration")


class MCPAuthResponse(BaseModel):
    """Response for MCP authentication."""
    
    success: bool
    redirect_url: Optional[str] = None
    message: Optional[str] = None


class MCPToolCallPayload(BaseModel):
    """Payload for calling an MCP tool."""
    
    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class MCPToolCallResponse(BaseModel):
    """Response from MCP tool call."""
    
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
