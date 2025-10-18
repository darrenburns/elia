"""Logging configuration and utilities for MCP operations."""

import logging
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from enum import Enum

from elia_chat.locations import config_directory


class MCPLogLevel(Enum):
    """MCP-specific log levels."""
    AUDIT = "AUDIT"
    PERFORMANCE = "PERFORMANCE" 
    SECURITY = "SECURITY"
    CONNECTION = "CONNECTION"
    TOOL_EXECUTION = "TOOL_EXECUTION"


@dataclass
class MCPLogEntry:
    """Structured log entry for MCP operations."""
    timestamp: str
    level: str
    category: str
    server_name: Optional[str]
    tool_name: Optional[str]
    operation: str
    message: str
    duration_ms: Optional[float] = None
    success: bool = True
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class MCPLogger:
    """Enhanced logger for MCP operations with structured logging."""
    
    def __init__(self, name: str = "mcp"):
        self.logger = logging.getLogger(name)
        self._audit_entries: List[MCPLogEntry] = []
        self._performance_metrics: Dict[str, List[float]] = {}
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Set up MCP-specific logging configuration."""
        # Create MCP log directory
        log_dir = config_directory() / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Set up file handlers for different log types
        self._setup_audit_logging(log_dir)
        self._setup_performance_logging(log_dir)
        
    def _setup_audit_logging(self, log_dir: Path) -> None:
        """Set up audit logging to file."""
        audit_file = log_dir / "mcp_audit.log"
        
        # Create audit handler
        audit_handler = logging.FileHandler(audit_file)
        audit_handler.setLevel(logging.INFO)
        
        # Create formatter for audit logs
        audit_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - AUDIT - %(message)s'
        )
        audit_handler.setFormatter(audit_formatter)
        
        # Add handler to logger
        audit_logger = logging.getLogger("mcp.audit")
        audit_logger.addHandler(audit_handler)
        audit_logger.setLevel(logging.INFO)
    
    def _setup_performance_logging(self, log_dir: Path) -> None:
        """Set up performance logging to file."""
        perf_file = log_dir / "mcp_performance.log"
        
        # Create performance handler
        perf_handler = logging.FileHandler(perf_file)
        perf_handler.setLevel(logging.DEBUG)
        
        # Create formatter for performance logs
        perf_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - PERF - %(message)s'
        )
        perf_handler.setFormatter(perf_formatter)
        
        # Add handler to logger
        perf_logger = logging.getLogger("mcp.performance")
        perf_logger.addHandler(perf_handler)
        perf_logger.setLevel(logging.DEBUG)    

    def log_connection_event(
        self, 
        server_name: str, 
        event: str, 
        success: bool = True,
        error: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log MCP connection events."""
        entry = MCPLogEntry(
            timestamp=datetime.now().isoformat(),
            level="INFO" if success else "ERROR",
            category=MCPLogLevel.CONNECTION.value,
            server_name=server_name,
            tool_name=None,
            operation=event,
            message=f"Connection {event} for server '{server_name}'",
            success=success,
            error_code=error,
            details=details
        )
        
        self._audit_entries.append(entry)
        
        # Log to appropriate logger
        if success:
            self.logger.info(f"MCP Connection: {entry.message}")
        else:
            self.logger.error(f"MCP Connection Error: {entry.message} - {error}")
        
        # Also log to audit logger
        audit_logger = logging.getLogger("mcp.audit")
        audit_logger.info(json.dumps(entry.to_dict()))
    
    def log_tool_execution(
        self,
        server_name: str,
        tool_name: str,
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        result_size: Optional[int] = None
    ) -> None:
        """Log tool execution events with performance metrics."""
        # Sanitize arguments for logging (remove sensitive data)
        safe_args = self._sanitize_arguments(arguments) if arguments else None
        
        details = {
            "arguments": safe_args,
            "result_size_bytes": result_size
        }
        
        entry = MCPLogEntry(
            timestamp=datetime.now().isoformat(),
            level="INFO" if success else "ERROR",
            category=MCPLogLevel.TOOL_EXECUTION.value,
            server_name=server_name,
            tool_name=tool_name,
            operation="tool_execution",
            message=f"Tool '{tool_name}' executed on server '{server_name}'",
            duration_ms=duration_ms,
            success=success,
            error_code=error,
            details=details
        )
        
        self._audit_entries.append(entry)
        
        # Record performance metrics
        metric_key = f"{server_name}.{tool_name}"
        if metric_key not in self._performance_metrics:
            self._performance_metrics[metric_key] = []
        self._performance_metrics[metric_key].append(duration_ms)
        
        # Log to appropriate loggers
        if success:
            self.logger.debug(f"Tool executed: {tool_name} ({duration_ms:.2f}ms)")
        else:
            self.logger.error(f"Tool execution failed: {tool_name} - {error}")
        
        # Log to performance logger
        perf_logger = logging.getLogger("mcp.performance")
        perf_logger.debug(json.dumps(entry.to_dict()))
        
        # Log to audit logger
        audit_logger = logging.getLogger("mcp.audit")
        audit_logger.info(json.dumps(entry.to_dict()))
    
    def log_security_event(
        self,
        event: str,
        server_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        severity: str = "INFO",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log security-related events."""
        entry = MCPLogEntry(
            timestamp=datetime.now().isoformat(),
            level=severity,
            category=MCPLogLevel.SECURITY.value,
            server_name=server_name,
            tool_name=tool_name,
            operation="security_event",
            message=f"Security event: {event}",
            success=severity != "ERROR",
            details=details
        )
        
        self._audit_entries.append(entry)
        
        # Log to main logger with appropriate level
        log_func = getattr(self.logger, severity.lower(), self.logger.info)
        log_func(f"MCP Security: {entry.message}")
        
        # Always log security events to audit
        audit_logger = logging.getLogger("mcp.audit")
        audit_logger.warning(json.dumps(entry.to_dict()))
    
    def _sanitize_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from arguments for logging."""
        sensitive_keys = {
            'password', 'token', 'key', 'secret', 'auth', 'credential',
            'api_key', 'access_token', 'refresh_token', 'private_key'
        }
        
        sanitized = {}
        for key, value in arguments.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 100:
                # Truncate very long strings
                sanitized[key] = value[:100] + "...[TRUNCATED]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    @contextmanager
    def time_operation(self, operation: str, server_name: Optional[str] = None):
        """Context manager to time operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.debug(f"Operation '{operation}' took {duration_ms:.2f}ms")
            
            # Log to performance logger
            perf_logger = logging.getLogger("mcp.performance")
            perf_entry = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "server_name": server_name,
                "duration_ms": duration_ms
            }
            perf_logger.debug(json.dumps(perf_entry))
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filter recent entries
        recent_entries = [
            entry for entry in self._audit_entries
            if datetime.fromisoformat(entry.timestamp) > cutoff_time
            and entry.category == MCPLogLevel.TOOL_EXECUTION.value
        ]
        
        if not recent_entries:
            return {"message": "No tool executions in the specified time period"}
        
        # Calculate statistics
        total_executions = len(recent_entries)
        successful_executions = sum(1 for entry in recent_entries if entry.success)
        failed_executions = total_executions - successful_executions
        
        # Calculate performance metrics
        durations = [entry.duration_ms for entry in recent_entries if entry.duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        
        # Group by server and tool
        server_stats = {}
        tool_stats = {}
        
        for entry in recent_entries:
            # Server statistics
            if entry.server_name:
                if entry.server_name not in server_stats:
                    server_stats[entry.server_name] = {"total": 0, "successful": 0, "failed": 0}
                server_stats[entry.server_name]["total"] += 1
                if entry.success:
                    server_stats[entry.server_name]["successful"] += 1
                else:
                    server_stats[entry.server_name]["failed"] += 1
            
            # Tool statistics
            if entry.tool_name:
                if entry.tool_name not in tool_stats:
                    tool_stats[entry.tool_name] = {"total": 0, "successful": 0, "failed": 0}
                tool_stats[entry.tool_name]["total"] += 1
                if entry.success:
                    tool_stats[entry.tool_name]["successful"] += 1
                else:
                    tool_stats[entry.tool_name]["failed"] += 1
        
        return {
            "time_period_hours": hours,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": (successful_executions / total_executions * 100) if total_executions > 0 else 0,
            "performance": {
                "average_duration_ms": avg_duration,
                "max_duration_ms": max_duration,
                "min_duration_ms": min_duration
            },
            "server_statistics": server_stats,
            "tool_statistics": tool_stats
        }
    
    def get_audit_trail(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get audit trail for the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_entries = [
            entry.to_dict() for entry in self._audit_entries
            if datetime.fromisoformat(entry.timestamp) > cutoff_time
        ]
        
        return sorted(recent_entries, key=lambda x: x["timestamp"], reverse=True)
    
    def clear_old_entries(self, days: int = 30) -> int:
        """Clear audit entries older than N days."""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        original_count = len(self._audit_entries)
        self._audit_entries = [
            entry for entry in self._audit_entries
            if datetime.fromisoformat(entry.timestamp) > cutoff_time
        ]
        
        cleared_count = original_count - len(self._audit_entries)
        if cleared_count > 0:
            self.logger.info(f"Cleared {cleared_count} old audit entries (older than {days} days)")
        
        return cleared_count


# Global MCP logger instance
mcp_logger = MCPLogger()


def get_mcp_logger() -> MCPLogger:
    """Get the global MCP logger instance."""
    return mcp_logger