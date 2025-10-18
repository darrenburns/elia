# MCP Troubleshooting Guide

## Quick Diagnostics

### Check MCP Status
1. Open Elia Chat
2. Look for MCP status in the UI (usually in home screen or options)
3. Check which servers are connected/disconnected

### Validate Configuration
```bash
# Check if config file exists
ls -la ~/.config/elia/mcp.json

# Validate JSON syntax
python -m json.tool ~/.config/elia/mcp.json
```

## Common Error Messages

### "Command not found: uvx"
**Cause**: UV package manager not installed
**Solution**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or restart terminal
```

### "MCP server failed to start"
**Cause**: Server command or arguments incorrect
**Solution**:
1. Test command manually: `uvx mcp-server-name@latest`
2. Check server exists in registry
3. Verify arguments are correct

### "Connection timeout"
**Cause**: Server taking too long to start or respond
**Solution**:
```json
{
  "mcp_servers": {
    "slow-server": {
      "timeout": 60,
      "command": "..."
    }
  }
}
```

### "Permission denied"
**Cause**: Insufficient file/directory permissions
**Solution**:
```bash
# Check permissions
ls -la /path/to/directory

# Fix if needed
chmod 755 /path/to/directory
```

### "API authentication failed"
**Cause**: Missing or invalid API keys
**Solution**:
```json
{
  "mcp_servers": {
    "api-server": {
      "env": {
        "API_KEY": "your-actual-key-here"
      }
    }
  }
}
```

## Step-by-Step Debugging

### 1. Basic Connectivity Test
```bash
# Test UV installation
uv --version

# Test server manually
uvx mcp-server-filesystem@latest /tmp
```

### 2. Configuration Validation
```bash
# Check JSON syntax
python -c "import json; print('Valid JSON' if json.load(open('~/.config/elia/mcp.json'.replace('~', '$HOME'))) else 'Invalid JSON')"

# Check file permissions
ls -la ~/.config/elia/mcp.json
```

### 3. Server-Specific Tests

#### File System Server
```bash
# Test with temporary directory
uvx mcp-server-filesystem@latest /tmp

# Check directory permissions
ls -la /path/to/configured/directory
```

#### Git Server
```bash
# Test in a git repository
cd /path/to/git/repo
uvx mcp-server-git@latest
```

#### API-based Servers
```bash
# Test environment variables
echo $API_KEY

# Test network connectivity
curl -I https://api.example.com
```

## Recovery Procedures

### Reset MCP Configuration
```bash
# Backup current config
cp ~/.config/elia/mcp.json ~/.config/elia/mcp.json.backup

# Create minimal config
cat > ~/.config/elia/mcp.json << 'EOF'
{
  "mcp_servers": {}
}
EOF
```

### Clean Server Cache
```bash
# Clear UV cache
uv cache clean

# Reinstall problematic server
uvx --force mcp-server-name@latest
```

### Restart with Clean State
1. Close Elia Chat completely
2. Clear any temporary files
3. Restart Elia Chat
4. Check MCP status

## Performance Issues

### Slow Tool Execution
- Increase timeout values
- Check network connectivity
- Monitor system resources

### High Memory Usage
- Limit number of concurrent servers
- Disable unused servers
- Monitor server processes

### Connection Drops
- Check network stability
- Verify server health
- Review server logs

## Getting Additional Help

### Log Collection
1. Enable debug logging in Elia Chat
2. Reproduce the issue
3. Collect relevant log entries
4. Include configuration (remove sensitive data)

### Information to Include
- Operating system and version
- UV version (`uv --version`)
- Python version (`python --version`)
- Elia Chat version
- MCP server versions
- Complete error messages
- Configuration file (sanitized)

### Support Channels
- Elia Chat GitHub Issues
- MCP Community Forums
- Server-specific repositories