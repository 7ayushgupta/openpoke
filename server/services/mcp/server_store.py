"""Persistent storage for MCP server configurations."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...logging_config import logger
from ...mcp_client.models import MCPServerConfig


# Popular MCP server templates for one-click setup
POPULAR_SERVERS = {
    "notion": {
        "name": "Notion",
        "url": "https://api.notion.com/mcp",
        "auth_type": "api_key",
        "description": "Access Notion pages and databases",
        "setup_guide": "Get your integration token from Notion Developer Portal",
        "icon": "📝",
        "category": "Productivity",
        "auth_fields": [
            {
                "name": "api_key",
                "label": "Integration Token",
                "type": "password",
                "placeholder": "ntn_****",
                "help": "Create an integration at https://www.notion.so/my-integrations"
            }
        ]
    },
    "github": {
        "name": "GitHub",
        "url": "https://api.github.com/mcp",
        "auth_type": "api_key",
        "description": "Manage GitHub repositories and issues",
        "setup_guide": "Create a Personal Access Token in GitHub Settings",
        "icon": "🐙",
        "category": "Development",
        "auth_fields": [
            {
                "name": "api_key",
                "label": "Personal Access Token",
                "type": "password",
                "placeholder": "ghp_****",
                "help": "Generate token at https://github.com/settings/tokens"
            }
        ]
    }
}


class MCPServerStore:
    """Persistent storage for MCP server configurations."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.data_dir / "mcp_servers.json"
        self._servers: Dict[str, MCPServerConfig] = {}
        self._load_servers()
    
    def _load_servers(self) -> None:
        """Load server configurations from disk."""
        if not self.config_file.exists():
            logger.info("No MCP server configuration file found, starting with empty config")
            return
        
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            servers_data = data.get("servers", [])
            for server_data in servers_data:
                try:
                    config = MCPServerConfig(**server_data)
                    self._servers[config.name] = config
                except Exception as exc:
                    logger.warning(
                        f"Failed to load MCP server config: {server_data}",
                        extra={"error": str(exc)}
                    )
                    continue
            
            logger.info(f"Loaded {len(self._servers)} MCP server configurations")
            
        except Exception as exc:
            logger.error(
                f"Failed to load MCP server configurations from {self.config_file}",
                extra={"error": str(exc)}
            )
    
    def _save_servers(self) -> None:
        """Save server configurations to disk."""
        try:
            data = {
                "servers": [
                    {
                        "name": config.name,
                        "url": config.url,
                        "auth_type": config.auth_type,
                        "auth_config": config.auth_config,
                        "enabled": config.enabled,
                    }
                    for config in self._servers.values()
                ]
            }
            
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved {len(self._servers)} MCP server configurations")
            
        except Exception as exc:
            logger.error(
                f"Failed to save MCP server configurations to {self.config_file}",
                extra={"error": str(exc)}
            )
            raise
    
    def add_server(self, config: MCPServerConfig) -> None:
        """Add a new MCP server configuration."""
        self._servers[config.name] = config
        self._save_servers()
        logger.info(f"Added MCP server: {config.name}")
    
    def remove_server(self, server_name: str) -> bool:
        """Remove an MCP server configuration."""
        if server_name in self._servers:
            del self._servers[server_name]
            self._save_servers()
            logger.info(f"Removed MCP server: {server_name}")
            return True
        return False
    
    def get_server(self, server_name: str) -> Optional[MCPServerConfig]:
        """Get server configuration by name."""
        return self._servers.get(server_name)
    
    def list_servers(self) -> List[MCPServerConfig]:
        """List all server configurations."""
        return list(self._servers.values())
    
    def update_server(self, server_name: str, **updates: Any) -> bool:
        """Update server configuration."""
        if server_name not in self._servers:
            return False
        
        config = self._servers[server_name]
        updated_config = config.model_copy(update=updates)
        self._servers[server_name] = updated_config
        self._save_servers()
        logger.info(f"Updated MCP server: {server_name}")
        return True
    
    def enable_server(self, server_name: str) -> bool:
        """Enable a server."""
        return self.update_server(server_name, enabled=True)
    
    def disable_server(self, server_name: str) -> bool:
        """Disable a server."""
        return self.update_server(server_name, enabled=False)
    
    def get_popular_servers(self) -> Dict[str, Dict[str, Any]]:
        """Get popular server templates."""
        return POPULAR_SERVERS.copy()
    
    def create_from_template(self, template_id: str, auth_config: Dict[str, Any]) -> Optional[MCPServerConfig]:
        """Create a server configuration from a popular template."""
        if template_id not in POPULAR_SERVERS:
            return None
        
        template = POPULAR_SERVERS[template_id]
        
        # Generate unique name if server already exists
        base_name = template["name"]
        server_name = base_name
        counter = 1
        while server_name in self._servers:
            server_name = f"{base_name} {counter}"
            counter += 1
        
        config = MCPServerConfig(
            name=server_name,
            url=template["url"],
            auth_type=template["auth_type"],
            auth_config=auth_config,
            enabled=True
        )
        
        return config


@lru_cache(maxsize=1)
def get_mcp_server_store() -> MCPServerStore:
    """Get cached MCP server store instance."""
    from ...config import get_settings
    
    settings = get_settings()
    data_dir = Path(__file__).parent.parent.parent / "data" / "mcp"
    return MCPServerStore(data_dir)
