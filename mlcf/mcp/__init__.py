"""
Model Context Protocol server implementation.
"""

try:
    from mlcf.mcp.server import MCPContextServer
except ImportError:
    MCPContextServer = None

__all__ = ["MCPContextServer"]