"""Comprehensive exception hierarchy for MCP operations."""

from typing import Optional, Dict, Any
from enum import Enum


class MCPErrorCode(Enum):
    """Standard error codes for MCP operations."""
    
    # Connection errors
    CONNECTION_FAILED = "connection_failed"
    CONNECTION_TIMEOUT = "connection_timeout"
    CONNECTION_LOST = "connection_lost"
    SERVER_UNAVAILABLE = "server_unavailable"
    
    # Configuration errors
    INVALID_CONFIG = "invalid_config"
    MISSING_CONFIG = "missing_config"
    CONFIG_VALIDATION_ERROR = "config_validation_error"
    
    # Tool execution errors
    TOOL_NOT_FOUND = "tool_not_found"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    TOOL_TIMEOUT = "tool_timeout"
    INVALID_ARGUMENTS = "invalid_arguments"
    TOOL_PERMISSION_DENIED = "tool_permission_denied"
    
    # Server management errors
    SERVER_NOT_FOUND = "server_not_found"
    SERVER_ALREADY_EXISTS = "server_already_exists"
    MULTIPLE_SERVERS_ERROR = "multiple_servers_error"
    
    # Protocol errors
    PROTOCOL_ERROR = "protocol_error"
    INVALID_RESPONSE = "invalid_response"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    
    # Resource errors
    RESOURCE_EXHAUSTED = "resource_exhausted"
    RATE_LIMITED = "rate_limited"
    
    # Security errors
    AUTHENTICATION_FAILED = "authentication_failed"
    AUTHORIZATION_FAILED = "authorization_failed"
    SECURITY_VIOLATION = "security_violation"


class MCPError(Exception):
    """Base exception for all MCP-related errors.
    
    Provides structured error information including error codes,
    user-friendly messages, and additional context.
    """
    
    def __init__(
        self,
        message: str,
        error_code: MCPErrorCode,
        user_message: Optional[str] = None,
        server_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize MCP error.
        
        Args:
            message: Technical error message for logging
            error_code: Standardized error code
            user_message: User-friendly error message (optional)
            server_name: Name of the MCP server involved (optional)
            tool_name: Name of the tool involved (optional)
            details: Additional error context (optional)
            cause: Original exception that caused this error (optional)
        """
        super().__init__(message)
        self.error_code = error_code
        self.server_name = server_name
        self.tool_name = tool_name
        self.details = details or {}
        self.cause = cause
        self.user_message = user_message or self._generate_user_message()
    
    def _generate_user_message(self) -> str:
        """Generate a user-friendly error message based on the error code."""
        messages = {
            MCPErrorCode.CONNECTION_FAILED: "Unable to connect to the MCP server. Please check your configuration.",
            MCPErrorCode.CONNECTION_TIMEOUT: "Connection to the MCP server timed out. The server may be slow to respond.",
            MCPErrorCode.CONNECTION_LOST: "Lost connection to the MCP server. Attempting to reconnect...",
            MCPErrorCode.SERVER_UNAVAILABLE: "The MCP server is currently unavailable.",
            MCPErrorCode.INVALID_CONFIG: "The MCP configuration is invalid. Please check your settings.",
            MCPErrorCode.MISSING_CONFIG: "MCP configuration not found. Please set up your MCP servers.",
            MCPErrorCode.TOOL_NOT_FOUND: "The requested tool is not available.",
            MCPErrorCode.TOOL_EXECUTION_FAILED: "The tool failed to execute properly.",
            MCPErrorCode.TOOL_TIMEOUT: "The tool execution timed out.",
            MCPErrorCode.INVALID_ARGUMENTS: "Invalid arguments provided to the tool.",
            MCPErrorCode.TOOL_PERMISSION_DENIED: "Permission denied for tool execution.",
            MCPErrorCode.SERVER_NOT_FOUND: "The specified MCP server was not found.",
            MCPErrorCode.PROTOCOL_ERROR: "A protocol error occurred while communicating with the MCP server.",
            MCPErrorCode.RATE_LIMITED: "Too many requests. Please wait before trying again.",
            MCPErrorCode.AUTHENTICATION_FAILED: "Authentication with the MCP server failed.",
            MCPErrorCode.AUTHORIZATION_FAILED: "You don't have permission to perform this action.",
        }
        
        base_message = messages.get(self.error_code, "An MCP error occurred.")
        
        # Add context if available
        if self.server_name and self.tool_name:
            return f"{base_message} (Server: {self.server_name}, Tool: {self.tool_name})"
        elif self.server_name:
            return f"{base_message} (Server: {self.server_name})"
        elif self.tool_name:
            return f"{base_message} (Tool: {self.tool_name})"
        
        return base_message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "error_code": self.error_code.value,
            "message": str(self),
            "user_message": self.user_message,
            "server_name": self.server_name,
            "tool_name": self.tool_name,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None
        }
    
    def __str__(self) -> str:
        """String representation of the error."""
        parts = [super().__str__()]
        
        if self.server_name:
            parts.append(f"server={self.server_name}")
        if self.tool_name:
            parts.append(f"tool={self.tool_name}")
        if self.error_code:
            parts.append(f"code={self.error_code.value}")
        
        return f"{parts[0]} ({', '.join(parts[1:])})" if len(parts) > 1 else parts[0]


class MCPConnectionError(MCPError):
    """Exception for MCP connection-related errors."""
    
    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        error_code: MCPErrorCode = MCPErrorCode.CONNECTION_FAILED,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            server_name=server_name,
            **kwargs
        )


class MCPConfigurationError(MCPError):
    """Exception for MCP configuration-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: MCPErrorCode = MCPErrorCode.INVALID_CONFIG,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            **kwargs
        )


class MCPToolError(MCPError):
    """Exception for MCP tool execution errors."""
    
    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        server_name: Optional[str] = None,
        error_code: MCPErrorCode = MCPErrorCode.TOOL_EXECUTION_FAILED,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            tool_name=tool_name,
            server_name=server_name,
            **kwargs
        )


class MCPTimeoutError(MCPError):
    """Exception for MCP timeout errors."""
    
    def __init__(
        self,
        message: str,
        timeout_duration: Optional[float] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if timeout_duration is not None:
            details['timeout_duration'] = timeout_duration
        if operation is not None:
            details['operation'] = operation
        
        kwargs['details'] = details
        
        super().__init__(
            message=message,
            error_code=MCPErrorCode.TOOL_TIMEOUT,
            **kwargs
        )


class MCPProtocolError(MCPError):
    """Exception for MCP protocol-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: MCPErrorCode = MCPErrorCode.PROTOCOL_ERROR,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            **kwargs
        )


class MCPSecurityError(MCPError):
    """Exception for MCP security-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: MCPErrorCode = MCPErrorCode.SECURITY_VIOLATION,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            **kwargs
        )


class MCPServerError(MCPError):
    """Exception for MCP server management errors."""
    
    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        error_code: MCPErrorCode = MCPErrorCode.SERVER_NOT_FOUND,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            server_name=server_name,
            **kwargs
        )


def handle_mcp_error(
    error: Exception,
    operation: str,
    server_name: Optional[str] = None,
    tool_name: Optional[str] = None,
    default_error_code: MCPErrorCode = MCPErrorCode.PROTOCOL_ERROR
) -> MCPError:
    """Convert a generic exception to an appropriate MCP error.
    
    Args:
        error: The original exception
        operation: Description of the operation that failed
        server_name: Name of the MCP server (optional)
        tool_name: Name of the tool (optional)
        default_error_code: Default error code to use
        
    Returns:
        Appropriate MCPError subclass
    """
    # If it's already an MCP error, return as-is
    if isinstance(error, MCPError):
        return error
    
    # Map common exception types to MCP errors
    if isinstance(error, ConnectionError):
        return MCPConnectionError(
            message=f"{operation} failed: {error}",
            server_name=server_name,
            error_code=MCPErrorCode.CONNECTION_FAILED,
            cause=error
        )
    
    if isinstance(error, TimeoutError):
        return MCPTimeoutError(
            message=f"{operation} timed out: {error}",
            server_name=server_name,
            tool_name=tool_name,
            operation=operation,
            cause=error
        )
    
    if isinstance(error, PermissionError):
        return MCPSecurityError(
            message=f"{operation} permission denied: {error}",
            server_name=server_name,
            tool_name=tool_name,
            error_code=MCPErrorCode.AUTHORIZATION_FAILED,
            cause=error
        )
    
    if isinstance(error, ValueError):
        return MCPToolError(
            message=f"{operation} invalid arguments: {error}",
            server_name=server_name,
            tool_name=tool_name,
            error_code=MCPErrorCode.INVALID_ARGUMENTS,
            cause=error
        )
    
    # Default case - wrap as generic MCP error
    return MCPError(
        message=f"{operation} failed: {error}",
        error_code=default_error_code,
        server_name=server_name,
        tool_name=tool_name,
        cause=error
    )


def create_graceful_degradation_error(
    operation: str,
    affected_servers: Optional[list] = None,
    available_alternatives: Optional[list] = None
) -> MCPError:
    """Create an error for graceful degradation scenarios.
    
    Args:
        operation: The operation that couldn't be completed
        affected_servers: List of servers that are unavailable
        available_alternatives: List of alternative options
        
    Returns:
        MCPError with graceful degradation information
    """
    details = {}
    if affected_servers:
        details['affected_servers'] = affected_servers
    if available_alternatives:
        details['available_alternatives'] = available_alternatives
    
    message = f"Operation '{operation}' partially failed"
    if affected_servers:
        message += f" (affected servers: {', '.join(affected_servers)})"
    
    user_message = f"Some MCP servers are unavailable, but the operation can continue"
    if available_alternatives:
        user_message += f" using: {', '.join(available_alternatives)}"
    
    return MCPError(
        message=message,
        error_code=MCPErrorCode.SERVER_UNAVAILABLE,
        user_message=user_message,
        details=details
    )