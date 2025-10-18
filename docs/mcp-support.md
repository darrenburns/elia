# MCP (Model Context Protocol) Support in Elia Chat

## Overview

Elia Chat supports the Model Context Protocol (MCP), which allows language models to connect to external tools and data sources during conversations. This enables enhanced capabilities like accessing documentation, performing calculations, interacting with APIs, and much more.

## Quick Start

1. Create an MCP configuration file at `~/.config/elia/mcp.json`
2. Add your MCP server configurations
3. Restart Elia Chat
4. MCP tools will be available to language models in your conversations

## Configuration

### Configuration File Location

MCP servers are configured in a separate JSON file located at:
- **Linux/macOS**: `~/.config/elia/mcp.json`
- **Windows**: `%APPDATA%\elia\mcp.json`

### Basic Configuration Structure

```json
{
  "mcp_servers": {
    "server-name": {
      "command": "command-to-run",
      "args": ["arg1", "arg2"],
      "env": {
        "ENV_VAR": "value"
      },
      "disabled": false,
      "auto_approve": [],
      "timeout": 30
    }
  }
}
```

### Configuration Fields

- **command**: The executable command to start the MCP server
- **args**: Array of command-line arguments
- **env**: Environment variables for the server process
- **disabled**: Set to `true` to disable this server without removing configuration
- **auto_approve**: List of tool names that can execute without user confirmation (use carefully)
- **timeout**: Maximum seconds to wait for tool execution (default: 30)

## Popular MCP Server Examples

### AWS Documentation Server

Access AWS documentation and services:

```json
{
  "mcp_servers": {
    "aws-docs": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "auto_approve": [],
      "timeout": 30
    }
  }
}
```

### File System Server

Access and manipulate local files:

```json
{
  "mcp_servers": {
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem@latest", "/path/to/allowed/directory"],
      "env": {},
      "disabled": false,
      "auto_approve": ["read_file", "list_directory"],
      "timeout": 15
    }
  }
}
```

### Git Repository Server

Interact with Git repositories:

```json
{
  "mcp_servers": {
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git@latest"],
      "env": {},
      "disabled": false,
      "auto_approve": ["git_status", "git_log"],
      "timeout": 20
    }
  }
}
```

### Web Search Server

Perform web searches:

```json
{
  "mcp_servers": {
    "brave-search": {
      "command": "uvx",
      "args": ["mcp-server-brave-search@latest"],
      "env": {
        "BRAVE_API_KEY": "your-api-key-here"
      },
      "disabled": false,
      "auto_approve": [],
      "timeout": 30
    }
  }
}
```

### Database Server

Connect to databases:

```json
{
  "mcp_servers": {
    "postgres": {
      "command": "uvx",
      "args": ["mcp-server-postgres@latest"],
      "env": {
        "DATABASE_URL": "postgresql://user:pass@localhost/dbname"
      },
      "disabled": false,
      "auto_approve": ["list_tables", "describe_table"],
      "timeout": 45
    }
  }
}
```

### Calculator Server

Simple mathematical operations:

```json
{
  "mcp_servers": {
    "calculator": {
      "command": "python",
      "args": ["/path/to/calculator_server.py"],
      "env": {},
      "disabled": false,
      "auto_approve": ["add", "subtract", "multiply", "divide"],
      "timeout": 10
    }
  }
}
```

## Installation Requirements

### UV Package Manager

Most MCP servers use `uvx` (part of the UV package manager). Install UV first:

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative methods:**
- Homebrew: `brew install uv`
- pip: `pip install uv`

### Python Environment

Some MCP servers require Python. Ensure you have Python 3.8+ installed.

## Using MCP Tools

### Tool Approval Workflow

1. **Auto-approved tools**: Execute immediately without confirmation
2. **Non-approved tools**: Show confirmation dialog before execution
3. **User decision**: Approve or deny tool execution

### Example Conversation

```
User: What's the current status of my Git repository?Assistan
t: I'll check the Git status for you.

[Tool Approval Dialog appears]
Tool: git_status
Server: git
Description: Get the current status of the Git repository
Arguments: {"path": "."}

[User clicks "Approve"]A
ssistant: Your repository has 3 modified files and 1 untracked file. The modified files are src/main.py, README.md, and config.json. The untracked file is temp.log.
```

### Security Considerations

- **Auto-approval**: Only add tools to `auto_approve` that you trust completely
- **Environment variables**: Store sensitive data like API keys in environment variables
- **Tool permissions**: Review what each tool can do before approving
- **Network access**: Some tools may make external network requests

## Troubleshooting

### Common Issues

#### 1. MCP Server Won't Start

**Symptoms:**
- Server shows as "disconnected" in status
- Error messages about command not found
- Connection timeouts

**Solutions:**
```bash
# Check if UV is installed
uv --version

# Install UV if missing
curl -LsSf https://astral.sh/uv/install.sh | sh

# Test server command manually
uvx mcp-server-name@latest

# Check server logs in Elia Chat for specific errors
```

#### 2. Configuration File Not Found

**Symptoms:**
- MCP features not available
- No MCP status shown in UI

**Solutions:**
```bash
# Create config directory if it doesn't exist
mkdir -p ~/.config/elia

# Create basic MCP configuration
cat > ~/.config/elia/mcp.json << 'EOF'
{
  "mcp_servers": {}
}
EOF
```

#### 3. Tool Execution Timeouts

**Symptoms:**
- Tools fail with timeout errors
- Long-running operations get cancelled

**Solutions:**
- Increase timeout value in server configuration
- Check network connectivity for remote tools
- Verify server is responding correctly

```json
{
  "mcp_servers": {
    "slow-server": {
      "timeout": 60,
      "..."
    }
  }
}
```

#### 4. Permission Denied Errors

**Symptoms:**
- Tools fail with permission errors
- File access denied messages

**Solutions:**
- Check file/directory permissions
- Ensure Elia Chat has necessary access rights
- Verify environment variables are set correctly

```bash
# Check file permissions
ls -la /path/to/file

# Fix permissions if needed
chmod 644 /path/to/file
```

#### 5. Environment Variable Issues

**Symptoms:**
- API-based tools fail with authentication errors
- Missing configuration errors

**Solutions:**
```json
{
  "mcp_servers": {
    "api-server": {
      "env": {
        "API_KEY": "your-key-here",
        "API_URL": "https://api.example.com"
      }
    }
  }
}
```

#### 6. Multiple Server Conflicts

**Symptoms:**
- Tools with same names from different servers
- Unexpected tool behavior

**Solutions:**
- Use descriptive server names
- Check tool names don't conflict
- Disable conflicting servers if needed

### Debugging Steps

1. **Check Configuration Syntax**
   ```bash
   # Validate JSON syntax
   python -m json.tool ~/.config/elia/mcp.json
   ```

2. **Test Server Manually**
   ```bash
   # Run server command directly
   uvx mcp-server-name@latest
   ```

3. **Check Logs**
   - Look for MCP-related error messages in Elia Chat
   - Check server output for connection issues

4. **Verify Dependencies**
   ```bash
   # Check UV installation
   uv --version
   
   # Check Python version
   python --version
   ```

5. **Test Minimal Configuration**
   Start with a simple server configuration and add complexity gradually.

### Getting Help

- **MCP Documentation**: https://modelcontextprotocol.io/
- **Server Registry**: https://github.com/modelcontextprotocol/servers
- **Elia Chat Issues**: Report bugs in the Elia Chat repository
- **Community**: Join MCP community discussions

## Advanced Configuration

### Multiple Servers

You can configure multiple MCP servers simultaneously:

```json
{
  "mcp_servers": {
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem@latest", "/home/user/projects"]
    },
    "git": {
      "command": "uvx", 
      "args": ["mcp-server-git@latest"]
    },
    "calculator": {
      "command": "python",
      "args": ["/usr/local/bin/calc_server.py"]
    }
  }
}
```

### Environment-Specific Configuration

Use environment variables for different setups:

```json
{
  "mcp_servers": {
    "database": {
      "command": "uvx",
      "args": ["mcp-server-postgres@latest"],
      "env": {
        "DATABASE_URL": "${DATABASE_URL}",
        "DB_POOL_SIZE": "10"
      }
    }
  }
}
```

### Custom Server Development

Create your own MCP server using the FastMCP library:

```python
# my_server.py
from mcp.server import FastMCP

mcp = FastMCP("My Custom Server")

@mcp.tool(description="Get system information")
def get_system_info() -> str:
    import platform
    return f"OS: {platform.system()} {platform.release()}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

Then configure it in Elia:

```json
{
  "mcp_servers": {
    "custom": {
      "command": "python",
      "args": ["/path/to/my_server.py"]
    }
  }
}
```

## Best Practices

### Security

1. **Minimal Auto-Approval**: Only auto-approve read-only or safe operations
2. **Environment Variables**: Use env vars for sensitive data, never hardcode secrets
3. **Least Privilege**: Configure servers with minimal necessary permissions
4. **Regular Updates**: Keep MCP servers updated to latest versions

### Performance

1. **Appropriate Timeouts**: Set realistic timeouts based on tool complexity
2. **Resource Limits**: Monitor resource usage of MCP server processes
3. **Selective Enabling**: Disable unused servers to reduce overhead
4. **Connection Management**: Let Elia handle connection lifecycle

### Maintenance

1. **Configuration Backup**: Keep backups of your MCP configuration
2. **Version Pinning**: Consider pinning server versions for stability
3. **Regular Testing**: Periodically test your MCP tools
4. **Documentation**: Document custom server configurations

## Supported MCP Servers

Popular servers available through UV:

- **awslabs.aws-documentation-mcp-server**: AWS documentation and services
- **mcp-server-filesystem**: Local file system access
- **mcp-server-git**: Git repository operations
- **mcp-server-brave-search**: Web search via Brave API
- **mcp-server-postgres**: PostgreSQL database access
- **mcp-server-sqlite**: SQLite database operations
- **mcp-server-github**: GitHub API integration
- **mcp-server-slack**: Slack workspace integration

Check the [MCP Server Registry](https://github.com/modelcontextprotocol/servers) for the complete list.