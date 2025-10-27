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


@router.get("/servers/popular", response_class=JSONResponse)
async def get_popular_servers() -> JSONResponse:
    """Get popular MCP server templates for one-click setup."""
    try:
        store = get_mcp_server_store()
        popular_servers = store.get_popular_servers()
        
        return JSONResponse({
            "ok": True,
            "servers": popular_servers
        })
        
    except Exception as exc:
        logger.error("Failed to get popular servers", extra={"error": str(exc)})
        return error_response(f"Failed to get popular servers: {exc}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/servers/from-template", response_class=JSONResponse)
async def create_server_from_template(
    template_id: str,
    auth_config: dict
) -> JSONResponse:
    """Create an MCP server from a popular template."""
    try:
        store = get_mcp_server_store()
        
        # Create server from template
        config = store.create_from_template(template_id, auth_config)
        if not config:
            return error_response(f"Unknown template: {template_id}", status_code=status.HTTP_404_NOT_FOUND)
        
        # Add to store
        store.add_server(config)
        
        # Add to registry
        registry = get_mcp_registry()
        registry.add_server(config)
        
        # Initialize server tools
        await registry.refresh_server(config.name)
        
        logger.info(f"Created MCP server from template: {template_id} -> {config.name}")
        
        return JSONResponse({
            "ok": True,
            "message": f"Created {config.name} from {template_id} template",
            "server": {
                "name": config.name,
                "url": config.url,
                "auth_type": config.auth_type,
                "enabled": config.enabled,
            }
        })
        
    except Exception as exc:
        logger.error(f"Failed to create server from template: {template_id}", extra={"error": str(exc)})
        return error_response(f"Failed to create server from template: {exc}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/servers/validate", response_class=JSONResponse)
async def validate_server_connection(
    server_url: str,
    auth_type: str,
    auth_config: dict
) -> JSONResponse:
    """Validate MCP server connection before saving."""
    try:
        # Create temporary config for testing
        temp_config = MCPServerConfig(
            name="temp_validation",
            url=server_url,
            auth_type=auth_type,
            auth_config=auth_config,
            enabled=True
        )
        
        # Test connection via registry
        registry = get_mcp_registry()
        registry.add_server(temp_config)
        
        try:
            # Try to discover tools (this will test the connection)
            await registry.refresh_server("temp_validation")
            
            # Get discovered tools
            tools = registry.get_tools_for_server("temp_validation")
            
            # Clean up temporary server
            registry.remove_server("temp_validation")
            
            return JSONResponse({
                "ok": True,
                "message": "Server connection successful",
                "tools_discovered": len(tools),
                "tools": [{"name": tool.name, "description": tool.description} for tool in tools]
            })
            
        except Exception as conn_exc:
            # Clean up on failure
            try:
                registry.remove_server("temp_validation")
            except:
                pass
            
            return JSONResponse({
                "ok": False,
                "message": f"Connection failed: {str(conn_exc)}",
                "error": str(conn_exc)
            })
        
    except Exception as exc:
        logger.error("Failed to validate server connection", extra={"error": str(exc)})
        return error_response(f"Failed to validate server: {exc}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
