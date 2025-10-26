"""MCP server management routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from ..logging_config import logger
from ..mcp_client.models import MCPServerConfig
from ..mcp_client.registry import get_mcp_registry
from ..models.mcp import (
    MCPAuthPayload,
    MCPAuthResponse,
    MCPConnectPayload,
    MCPDisconnectPayload,
    MCPServerListResponse,
    MCPServerResponse,
    MCPToolCallPayload,
    MCPToolCallResponse,
    MCPToolListResponse,
)
from ..services.mcp import get_mcp_server_store
from ..utils import error_response

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.post("/servers", response_class=JSONResponse)
async def add_mcp_server(payload: MCPConnectPayload) -> JSONResponse:
    """Add a new MCP server."""
    try:
        # Create server configuration
        config = MCPServerConfig(
            name=payload.server_name,
            url=payload.url,
            auth_type=payload.auth_type,
            auth_config=payload.auth_config,
            enabled=True,
        )
        
        # Add to registry
        registry = get_mcp_registry()
        registry.add_server(config)
        
        # Save to storage
        store = get_mcp_server_store()
        store.add_server(config)
        
        # Initialize server tools
        await registry.refresh_server(payload.server_name)
        
        logger.info(f"Added MCP server: {payload.server_name}")
        
        return JSONResponse({
            "ok": True,
            "message": f"Added MCP server: {payload.server_name}",
            "server": {
                "name": config.name,
                "url": config.url,
                "auth_type": config.auth_type,
                "enabled": config.enabled,
            }
        })
        
    except Exception as exc:
        logger.error(f"Failed to add MCP server: {payload.server_name}", extra={"error": str(exc)})
        return error_response(f"Failed to add MCP server: {exc}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/servers", response_model=MCPServerListResponse)
async def list_mcp_servers() -> MCPServerListResponse:
    """List all configured MCP servers."""
    try:
        registry = get_mcp_registry()
        servers = registry.list_servers()
        
        server_responses = []
        for server in servers:
            tool_count = len(registry.get_tools_for_server(server.name))
            server_responses.append(MCPServerResponse(
                name=server.name,
                url=server.url,
                auth_type=server.auth_type,
                enabled=server.enabled,
                tool_count=tool_count,
            ))
        
        return MCPServerListResponse(servers=server_responses)
        
    except Exception as exc:
        logger.error("Failed to list MCP servers", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete("/servers/{server_name}", response_class=JSONResponse)
async def remove_mcp_server(server_name: str) -> JSONResponse:
    """Remove an MCP server."""
    try:
        # Remove from registry
        registry = get_mcp_registry()
        registry.remove_server(server_name)
        
        # Remove from storage
        store = get_mcp_server_store()
        success = store.remove_server(server_name)
        
        if not success:
            return error_response(f"Server {server_name} not found", status_code=status.HTTP_404_NOT_FOUND)
        
        logger.info(f"Removed MCP server: {server_name}")
        
        return JSONResponse({
            "ok": True,
            "message": f"Removed MCP server: {server_name}",
        })
        
    except Exception as exc:
        logger.error(f"Failed to remove MCP server: {server_name}", extra={"error": str(exc)})
        return error_response(f"Failed to remove MCP server: {exc}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/tools", response_model=MCPToolListResponse)
async def list_mcp_tools() -> MCPToolListResponse:
    """List all available MCP tools."""
    try:
        registry = get_mcp_registry()
        tools = registry.get_tools()
        
        from ..models.mcp import MCPToolResponse
        tool_responses = []
        
        for tool in tools:
            # Extract server name from prefixed tool name
            if tool.name.startswith("mcp_"):
                parts = tool.name.split("_", 2)
                if len(parts) >= 3:
                    server_name = parts[1]
                else:
                    server_name = "unknown"
            else:
                server_name = "unknown"
            
            tool_responses.append(MCPToolResponse(
                name=tool.name,
                description=tool.description,
                server_name=server_name,
                input_schema=tool.inputSchema,
            ))
        
        return MCPToolListResponse(tools=tool_responses)
        
    except Exception as exc:
        logger.error("Failed to list MCP tools", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/auth/{server_name}", response_model=MCPAuthResponse)
async def handle_mcp_auth(server_name: str, payload: MCPAuthPayload) -> MCPAuthResponse:
    """Handle MCP server authentication."""
    try:
        # For now, just store the auth config
        store = get_mcp_server_store()
        server = store.get_server(server_name)
        
        if not server:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Server {server_name} not found")
        
        # Update auth config
        store.update_server(server_name, auth_config=payload.auth_config)
        
        # Refresh the server in registry
        registry = get_mcp_registry()
        await registry.refresh_server(server_name)
        
        logger.info(f"Updated auth for MCP server: {server_name}")
        
        return MCPAuthResponse(
            success=True,
            message=f"Authentication configured for {server_name}",
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to handle MCP auth for {server_name}", extra={"error": str(exc)})
        return MCPAuthResponse(
            success=False,
            message=f"Authentication failed: {exc}",
        )


@router.post("/tools/call", response_model=MCPToolCallResponse)
async def call_mcp_tool(payload: MCPToolCallPayload) -> MCPToolCallResponse:
    """Call an MCP tool."""
    try:
        registry = get_mcp_registry()
        
        if not registry.is_initialized():
            return MCPToolCallResponse(
                success=False,
                error="MCP registry not initialized"
            )
        
        result = await registry.call_tool(payload.tool_name, payload.arguments)
        
        return MCPToolCallResponse(
            success=result.success,
            data=result.data,
            error=result.error,
        )
        
    except Exception as exc:
        logger.error(f"Failed to call MCP tool: {payload.tool_name}", extra={"error": str(exc)})
        return MCPToolCallResponse(
            success=False,
            error=f"Tool call failed: {exc}",
        )


@router.post("/servers/{server_name}/refresh", response_class=JSONResponse)
async def refresh_mcp_server(server_name: str) -> JSONResponse:
    """Refresh tools from a specific MCP server."""
    try:
        registry = get_mcp_registry()
        success = await registry.refresh_server(server_name)
        
        if not success:
            return error_response(f"Failed to refresh server {server_name}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        logger.info(f"Refreshed MCP server: {server_name}")
        
        return JSONResponse({
            "ok": True,
            "message": f"Refreshed MCP server: {server_name}",
        })
        
    except Exception as exc:
        logger.error(f"Failed to refresh MCP server: {server_name}", extra={"error": str(exc)})
        return error_response(f"Failed to refresh server: {exc}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
