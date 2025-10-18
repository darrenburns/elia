# MCP Support in Elia Chat

Elia Chat supports the Model Context Protocol (MCP) for connecting to external tools and data sources.

## Quick Setup

1. **Install UV package manager:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Create MCP configuration file:**
   ```bash
   mkdir -p ~/.config/elia
   cat > ~/.config/elia/mcp.json << 'EOF'
   {
     "mcp_servers": {
       "filesystem": {
         "command": "uvx",
         "args": ["mcp-server-filesystem@latest", "/home/user"],
         "auto_approve": ["read_file", "list_directory"]
       }
     }
   }
   EOF
   ```

3. **Restart Elia Chat** - MCP tools will now be available to language models

## Popular Servers

- **AWS Docs**: `uvx awslabs.aws-documentation-mcp-server@latest`
- **File System**: `uvx mcp-server-filesystem@latest /path`
- **Git**: `uvx mcp-server-git@latest`
- **Web Search**: `uvx mcp-server-brave-search@latest`

## Documentation

See [docs/mcp-support.md](docs/mcp-support.md) for complete configuration guide, troubleshooting, and examples.

## Security Note

Only add tools to `auto_approve` that you trust completely. Other tools will require user confirmation before execution.