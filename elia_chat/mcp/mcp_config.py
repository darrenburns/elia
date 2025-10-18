"""MCP configuration models and loading functionality."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, ValidationError, ConfigDict

from elia_chat.locations import config_directory
from elia_chat.mcp.exceptions import MCPConfigurationError, MCPErrorCode

logger = logging.getLogger(__name__)


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""
    
    model_config = ConfigDict(extra="forbid")
    
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    disabled: bool = False
    auto_approve: List[str] = Field(default_factory=list)
    timeout: int = 30


class MCPConfig(BaseModel):
    """Complete MCP configuration."""
    
    model_config = ConfigDict(extra="forbid")
    
    mcp_servers: Dict[str, MCPServerConfig] = Field(default_factory=dict)
    
    @classmethod
    def load_from_file(cls, config_path: Path) -> "MCPConfig":
        """Load MCP configuration from JSON file.
        
        Args:
            config_path: Path to the MCP configuration file
            
        Returns:
            MCPConfig instance
            
        Raises:
            MCPConfigurationError: If the config file is invalid or cannot be loaded
        """
        try:
            if not config_path.exists():
                raise MCPConfigurationError(
                    message=f"MCP configuration file not found: {config_path}",
                    error_code=MCPErrorCode.MISSING_CONFIG,
                    details={"config_path": str(config_path)}
                )
            
            if not config_path.is_file():
                raise MCPConfigurationError(
                    message=f"MCP configuration path is not a file: {config_path}",
                    error_code=MCPErrorCode.INVALID_CONFIG,
                    details={"config_path": str(config_path)}
                )
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Validate that it's a dictionary
            if not isinstance(config_data, dict):
                raise MCPConfigurationError(
                    message=f"MCP configuration must be a JSON object, got {type(config_data).__name__}",
                    error_code=MCPErrorCode.CONFIG_VALIDATION_ERROR,
                    details={"config_path": str(config_path), "data_type": type(config_data).__name__}
                )
            
            return cls(**config_data)
            
        except json.JSONDecodeError as e:
            raise MCPConfigurationError(
                message=f"Invalid JSON in MCP configuration file: {e}",
                error_code=MCPErrorCode.CONFIG_VALIDATION_ERROR,
                details={"config_path": str(config_path), "json_error": str(e)},
                cause=e
            )
        except ValidationError as e:
            # Extract validation details
            validation_errors = []
            for error in e.errors():
                validation_errors.append({
                    "field": ".".join(str(x) for x in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"]
                })
            
            raise MCPConfigurationError(
                message=f"Invalid MCP configuration: {e}",
                error_code=MCPErrorCode.CONFIG_VALIDATION_ERROR,
                details={
                    "config_path": str(config_path),
                    "validation_errors": validation_errors
                },
                cause=e
            )
        except Exception as e:
            raise MCPConfigurationError(
                message=f"Failed to load MCP configuration: {e}",
                error_code=MCPErrorCode.INVALID_CONFIG,
                details={"config_path": str(config_path)},
                cause=e
            )
    
    @classmethod
    def load_default(cls) -> "MCPConfig":
        """Load MCP configuration from default location.
        
        Returns:
            MCPConfig instance. If the file doesn't exist or is invalid,
            returns an empty configuration with no servers.
        """
        config_path = config_directory() / "mcp.json"
        
        if not config_path.exists():
            logger.info(f"MCP configuration file not found at {config_path}, using empty configuration")
            return cls()
        
        try:
            return cls.load_from_file(config_path)
        except MCPConfigurationError as e:
            logger.warning(f"Failed to load MCP configuration: {e.user_message}")
            logger.debug(f"Configuration error details: {e.details}")
            logger.warning("Using empty MCP configuration for graceful degradation")
            return cls()
        except Exception as e:
            logger.error(f"Unexpected error loading MCP configuration from {config_path}: {e}")
            logger.warning("Using empty MCP configuration")
            return cls()
    
    def get_enabled_servers(self) -> Dict[str, MCPServerConfig]:
        """Return only enabled MCP servers.
        
        Returns:
            Dictionary of server names to their configurations, 
            excluding disabled servers.
        """
        return {
            name: config 
            for name, config in self.mcp_servers.items() 
            if not config.disabled
        }
    
    def save_to_file(self, config_path: Optional[Path] = None) -> None:
        """Save MCP configuration to JSON file.
        
        Args:
            config_path: Path to save the configuration. If None, uses default location.
            
        Raises:
            OSError: If the file cannot be written
        """
        if config_path is None:
            config_path = config_directory() / "mcp.json"
        
        # Ensure the parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.model_dump(), f, indent=2)
            logger.info(f"MCP configuration saved to {config_path}")
        except OSError as e:
            logger.error(f"Failed to save MCP configuration to {config_path}: {e}")
            raise
    
    def add_server(self, name: str, config: MCPServerConfig) -> None:
        """Add or update an MCP server configuration.
        
        Args:
            name: Server name
            config: Server configuration
        """
        self.mcp_servers[name] = config
    
    def remove_server(self, name: str) -> bool:
        """Remove an MCP server configuration.
        
        Args:
            name: Server name to remove
            
        Returns:
            True if the server was removed, False if it didn't exist
        """
        if name in self.mcp_servers:
            del self.mcp_servers[name]
            return True
        return False
    
    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        """Get configuration for a specific server.
        
        Args:
            name: Server name
            
        Returns:
            Server configuration or None if not found
        """
        return self.mcp_servers.get(name)