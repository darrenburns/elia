"""Unit tests for MCP configuration functionality."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from pydantic import ValidationError

from elia_chat.mcp.mcp_config import MCPConfig, MCPServerConfig
from elia_chat.mcp.exceptions import MCPConfigurationError


class TestMCPServerConfig:
    """Test MCPServerConfig model."""
    
    def test_default_values(self):
        """Test MCPServerConfig with default values."""
        config = MCPServerConfig(command="test-command")
        
        assert config.command == "test-command"
        assert config.args == []
        assert config.env == {}
        assert config.disabled is False
        assert config.auto_approve == []
        assert config.timeout == 30
    
    def test_custom_values(self):
        """Test MCPServerConfig with custom values."""
        config = MCPServerConfig(
            command="python",
            args=["script.py", "--verbose"],
            env={"DEBUG": "1", "PATH": "/usr/bin"},
            disabled=True,
            auto_approve=["tool1", "tool2"],
            timeout=60
        )
        
        assert config.command == "python"
        assert config.args == ["script.py", "--verbose"]
        assert config.env == {"DEBUG": "1", "PATH": "/usr/bin"}
        assert config.disabled is True
        assert config.auto_approve == ["tool1", "tool2"]
        assert config.timeout == 60
    
    def test_validation_error_missing_command(self):
        """Test validation error when command is missing."""
        with pytest.raises(ValidationError):
            MCPServerConfig()
    
    def test_validation_error_invalid_timeout(self):
        """Test validation error with invalid timeout type."""
        with pytest.raises(ValidationError):
            MCPServerConfig(command="test", timeout="invalid")


class TestMCPConfig:
    """Test MCPConfig model."""
    
    def test_empty_config(self):
        """Test empty MCPConfig."""
        config = MCPConfig()
        assert config.mcp_servers == {}
    
    def test_config_with_servers(self):
        """Test MCPConfig with servers."""
        server_config = MCPServerConfig(command="test-command")
        config = MCPConfig(mcp_servers={"test-server": server_config})
        
        assert "test-server" in config.mcp_servers
        assert config.mcp_servers["test-server"].command == "test-command"
    
    def test_get_enabled_servers_all_enabled(self):
        """Test get_enabled_servers with all servers enabled."""
        server1 = MCPServerConfig(command="cmd1", disabled=False)
        server2 = MCPServerConfig(command="cmd2", disabled=False)
        config = MCPConfig(mcp_servers={"server1": server1, "server2": server2})
        
        enabled = config.get_enabled_servers()
        assert len(enabled) == 2
        assert "server1" in enabled
        assert "server2" in enabled
    
    def test_get_enabled_servers_some_disabled(self):
        """Test get_enabled_servers with some servers disabled."""
        server1 = MCPServerConfig(command="cmd1", disabled=False)
        server2 = MCPServerConfig(command="cmd2", disabled=True)
        server3 = MCPServerConfig(command="cmd3", disabled=False)
        config = MCPConfig(mcp_servers={
            "server1": server1, 
            "server2": server2, 
            "server3": server3
        })
        
        enabled = config.get_enabled_servers()
        assert len(enabled) == 2
        assert "server1" in enabled
        assert "server3" in enabled
        assert "server2" not in enabled
    
    def test_add_server(self):
        """Test adding a server to configuration."""
        config = MCPConfig()
        server_config = MCPServerConfig(command="test-command")
        
        config.add_server("test-server", server_config)
        
        assert "test-server" in config.mcp_servers
        assert config.mcp_servers["test-server"].command == "test-command"
    
    def test_remove_server_exists(self):
        """Test removing an existing server."""
        server_config = MCPServerConfig(command="test-command")
        config = MCPConfig(mcp_servers={"test-server": server_config})
        
        result = config.remove_server("test-server")
        
        assert result is True
        assert "test-server" not in config.mcp_servers
    
    def test_remove_server_not_exists(self):
        """Test removing a non-existent server."""
        config = MCPConfig()
        
        result = config.remove_server("non-existent")
        
        assert result is False
    
    def test_get_server_exists(self):
        """Test getting an existing server configuration."""
        server_config = MCPServerConfig(command="test-command")
        config = MCPConfig(mcp_servers={"test-server": server_config})
        
        result = config.get_server("test-server")
        
        assert result is not None
        assert result.command == "test-command"
    
    def test_get_server_not_exists(self):
        """Test getting a non-existent server configuration."""
        config = MCPConfig()
        
        result = config.get_server("non-existent")
        
        assert result is None


class TestMCPConfigFileOperations:
    """Test MCPConfig file loading and saving operations."""
    
    def test_load_from_file_valid_json(self):
        """Test loading valid JSON configuration file."""
        config_data = {
            "mcp_servers": {
                "test-server": {
                    "command": "python",
                    "args": ["script.py"],
                    "env": {"DEBUG": "1"},
                    "disabled": False,
                    "auto_approve": ["tool1"],
                    "timeout": 45
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            config = MCPConfig.load_from_file(temp_path)
            
            assert len(config.mcp_servers) == 1
            server = config.mcp_servers["test-server"]
            assert server.command == "python"
            assert server.args == ["script.py"]
            assert server.env == {"DEBUG": "1"}
            assert server.disabled is False
            assert server.auto_approve == ["tool1"]
            assert server.timeout == 45
        finally:
            temp_path.unlink()
    
    def test_load_from_file_not_found(self):
        """Test loading from non-existent file."""
        non_existent_path = Path("/non/existent/file.json")
        
        with pytest.raises(MCPConfigurationError):
            MCPConfig.load_from_file(non_existent_path)
    
    def test_load_from_file_invalid_json(self):
        """Test loading invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(MCPConfigurationError):
                MCPConfig.load_from_file(temp_path)
        finally:
            temp_path.unlink()
    
    def test_load_from_file_invalid_config(self):
        """Test loading JSON with invalid configuration structure."""
        invalid_config = {
            "mcp_servers": {
                "test-server": {
                    # Missing required 'command' field
                    "args": ["script.py"]
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_config, f)
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(MCPConfigurationError):
                MCPConfig.load_from_file(temp_path)
        finally:
            temp_path.unlink()
    
    @patch('elia_chat.mcp.mcp_config.config_directory')
    def test_load_default_file_exists(self, mock_config_directory):
        """Test loading default configuration when file exists."""
        config_data = {
            "mcp_servers": {
                "default-server": {
                    "command": "default-command"
                }
            }
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_config_directory.return_value = temp_path
            
            config_file = temp_path / "mcp.json"
            with open(config_file, 'w') as f:
                json.dump(config_data, f)
            
            config = MCPConfig.load_default()
            
            assert len(config.mcp_servers) == 1
            assert "default-server" in config.mcp_servers
            assert config.mcp_servers["default-server"].command == "default-command"
    
    @patch('elia_chat.mcp.mcp_config.config_directory')
    def test_load_default_file_not_exists(self, mock_config_directory):
        """Test loading default configuration when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_config_directory.return_value = temp_path
            
            # File doesn't exist
            config = MCPConfig.load_default()
            
            assert len(config.mcp_servers) == 0
    
    @patch('elia_chat.mcp.mcp_config.config_directory')
    def test_load_default_invalid_file(self, mock_config_directory):
        """Test loading default configuration with invalid file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_config_directory.return_value = temp_path
            
            config_file = temp_path / "mcp.json"
            with open(config_file, 'w') as f:
                f.write("{ invalid json }")
            
            # Should return empty config instead of raising exception
            config = MCPConfig.load_default()
            
            assert len(config.mcp_servers) == 0
    
    def test_save_to_file_default_path(self):
        """Test saving configuration to default path."""
        server_config = MCPServerConfig(command="test-command")
        config = MCPConfig(mcp_servers={"test-server": server_config})
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "mcp.json"
            
            config.save_to_file(temp_path)
            
            assert temp_path.exists()
            
            # Verify saved content
            with open(temp_path, 'r') as f:
                saved_data = json.load(f)
            
            assert "mcp_servers" in saved_data
            assert "test-server" in saved_data["mcp_servers"]
            assert saved_data["mcp_servers"]["test-server"]["command"] == "test-command"
    
    @patch('elia_chat.mcp.mcp_config.config_directory')
    def test_save_to_file_no_path(self, mock_config_directory):
        """Test saving configuration without specifying path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_config_directory.return_value = temp_path
            
            server_config = MCPServerConfig(command="test-command")
            config = MCPConfig(mcp_servers={"test-server": server_config})
            
            config.save_to_file()
            
            config_file = temp_path / "mcp.json"
            assert config_file.exists()