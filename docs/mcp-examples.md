# MCP Configuration Examples

## Basic Examples

### Minimal Configuration
```json
{
  "mcp_servers": {}
}
```

### Single Server
```json
{
  "mcp_servers": {
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem@latest", "/home/user/documents"]
    }
  }
}
```

## Development Environment

### Full Development Stack
```json
{
  "mcp_servers": {
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem@latest", "/home/user/projects"],
      "auto_approve": ["read_file", "list_directory"],
      "timeout": 15
    },
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git@latest"],
      "auto_approve": ["git_status", "git_log", "git_diff"],
      "timeout": 20
    },
    "github": {
      "command": "uvx",
      "args": ["mcp-server-github@latest"],
      "env": {
        "GITHUB_TOKEN": "ghp_your_token_here"
      },
      "auto_approve": ["search_repositories", "get_repository"],
      "timeout": 30
    }
  }
}
```

## Data Analysis Environment

### Database and File Analysis
```json
{
  "mcp_servers": {
    "postgres": {
      "command": "uvx",
      "args": ["mcp-server-postgres@latest"],
      "env": {
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/analytics"
      },
      "auto_approve": ["list_tables", "describe_table"],
      "timeout": 45
    },
    "sqlite": {
      "command": "uvx",
      "args": ["mcp-server-sqlite@latest"],
      "auto_approve": ["list_tables", "describe_table", "query"],
      "timeout": 30
    },
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem@latest", "/data"],
      "auto_approve": ["read_file", "list_directory"],
      "timeout": 20
    }
  }
}
```

## Research Environment

### Documentation and Search
```json
{
  "mcp_servers": {
    "aws-docs": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "auto_approve": ["search_documentation", "get_documentation"],
      "timeout": 30
    },
    "brave-search": {
      "command": "uvx",
      "args": ["mcp-server-brave-search@latest"],
      "env": {
        "BRAVE_API_KEY": "BSA_your_api_key_here"
      },
      "timeout": 30
    },
    "wikipedia": {
      "command": "uvx",
      "args": ["mcp-server-wikipedia@latest"],
      "auto_approve": ["search", "get_page"],
      "timeout": 25
    }
  }
}
```

## System Administration

### Server Management Tools
```json
{
  "mcp_servers": {
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem@latest", "/"],
      "auto_approve": ["read_file", "list_directory"],
      "timeout": 15
    },
    "docker": {
      "command": "uvx",
      "args": ["mcp-server-docker@latest"],
      "auto_approve": ["list_containers", "container_status"],
      "timeout": 30
    },
    "kubernetes": {
      "command": "uvx",
      "args": ["mcp-server-kubernetes@latest"],
      "env": {
        "KUBECONFIG": "/home/user/.kube/config"
      },
      "auto_approve": ["get_pods", "get_services"],
      "timeout": 45
    }
  }
}
```

## Custom Server Examples

### Python Calculator Server
```json
{
  "mcp_servers": {
    "calculator": {
      "command": "python",
      "args": ["/usr/local/bin/calculator_server.py"],
      "auto_approve": ["add", "subtract", "multiply", "divide"],
      "timeout": 10
    }
  }
}
```

### Node.js Weather Server
```json
{
  "mcp_servers": {
    "weather": {
      "command": "node",
      "args": ["/opt/weather-server/index.js"],
      "env": {
        "WEATHER_API_KEY": "your_weather_api_key",
        "DEFAULT_LOCATION": "New York"
      },
      "auto_approve": ["get_current_weather"],
      "timeout": 20
    }
  }
}
```

## Security-Focused Examples

### Minimal Auto-Approval
```json
{
  "mcp_servers": {
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem@latest", "/home/user/safe-directory"],
      "auto_approve": ["read_file"],
      "timeout": 15
    },
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git@latest"],
      "auto_approve": ["git_status"],
      "timeout": 20
    }
  }
}
```

### No Auto-Approval (Maximum Security)
```json
{
  "mcp_servers": {
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem@latest", "/sensitive/data"],
      "auto_approve": [],
      "timeout": 15
    },
    "database": {
      "command": "uvx",
      "args": ["mcp-server-postgres@latest"],
      "env": {
        "DATABASE_URL": "postgresql://user:pass@prod-db:5432/production"
      },
      "auto_approve": [],
      "timeout": 30
    }
  }
}
```

## Environment-Specific Configurations

### Development Environment
```json
{
  "mcp_servers": {
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem@latest", "/home/user/dev"],
      "auto_approve": ["read_file", "list_directory", "write_file"],
      "timeout": 15
    },
    "database": {
      "command": "uvx",
      "args": ["mcp-server-postgres@latest"],
      "env": {
        "DATABASE_URL": "postgresql://dev:dev@localhost:5432/dev_db"
      },
      "auto_approve": ["list_tables", "describe_table", "query"],
      "timeout": 30
    }
  }
}
```

### Production Environment
```json
{
  "mcp_servers": {
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem@latest", "/var/log"],
      "auto_approve": ["read_file", "list_directory"],
      "timeout": 15
    },
    "database": {
      "command": "uvx",
      "args": ["mcp-server-postgres@latest"],
      "env": {
        "DATABASE_URL": "${PROD_DATABASE_URL}"
      },
      "auto_approve": ["list_tables", "describe_table"],
      "timeout": 45
    }
  }
}
```

## Testing Configurations

### Minimal Test Setup
```json
{
  "mcp_servers": {
    "test-calc": {
      "command": "python",
      "args": ["-c", "from mcp.server import FastMCP; mcp = FastMCP('test'); mcp.tool(lambda x, y: x + y, name='add'); mcp.run()"],
      "auto_approve": ["add"],
      "timeout": 5
    }
  }
}
```

### Multiple Test Servers
```json
{
  "mcp_servers": {
    "test-fs": {
      "command": "uvx",
      "args": ["mcp-server-filesystem@latest", "/tmp"],
      "auto_approve": ["read_file", "list_directory"],
      "timeout": 10
    },
    "test-calc": {
      "command": "python",
      "args": ["/path/to/test_calculator.py"],
      "auto_approve": ["add", "subtract"],
      "timeout": 5
    },
    "disabled-server": {
      "command": "uvx",
      "args": ["some-server@latest"],
      "disabled": true
    }
  }
}
```

## Advanced Patterns

### Conditional Server Loading
```json
{
  "mcp_servers": {
    "work-tools": {
      "command": "uvx",
      "args": ["work-mcp-server@latest"],
      "env": {
        "WORK_MODE": "true"
      },
      "disabled": false
    },
    "personal-tools": {
      "command": "uvx",
      "args": ["personal-mcp-server@latest"],
      "disabled": true
    }
  }
}
```

### Resource-Intensive Servers
```json
{
  "mcp_servers": {
    "ai-analysis": {
      "command": "uvx",
      "args": ["mcp-server-ai-analysis@latest"],
      "env": {
        "GPU_MEMORY_LIMIT": "8GB",
        "MAX_CONCURRENT_REQUESTS": "2"
      },
      "timeout": 120
    }
  }
}
```