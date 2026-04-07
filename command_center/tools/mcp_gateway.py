"""
L4 — Central MCP Connection Manager

Maintains persistent SSE connections to remote MCP servers, handles
reconnection on failure, and provides a unified get_toolset() interface.
"""

from typing import Optional

try:
    from google.adk.tools import MCPToolset
    from google.adk.tools.mcp import SseServerParams
except ImportError:
    # Stubs for development
    class SseServerParams:
        def __init__(self, **kwargs):
            self.config = kwargs

    class MCPToolset:
        def __init__(self, **kwargs):
            self.config = kwargs
            self._tools = []

        async def connect(self):
            pass

        async def list_tools(self):
            return self._tools

        def is_alive(self):
            return False

        async def close(self):
            pass


# MCP server endpoint configurations
MCP_SERVER_CONFIGS: dict[str, dict] = {
    "google_calendar": {
        "url": "https://calendar.googleapis.com/mcp/v1/sse",
        "auth_scheme": "oauth",
    },
    "gmail": {
        "url": "https://gmail.googleapis.com/mcp/v1/sse",
        "auth_scheme": "oauth",
    },
}

# In-memory pool of active MCPToolset connections
_connection_pool: dict[str, MCPToolset] = {}


async def get_toolset(server_name: str, auth_token: str) -> MCPToolset:
    """
    Returns an active MCPToolset for the named MCP server.
    Checks pool for an existing alive connection; creates a new one if needed.
    """
    existing = _connection_pool.get(server_name)
    if existing and hasattr(existing, "is_alive") and existing.is_alive():
        return existing

    server_config = MCP_SERVER_CONFIGS.get(server_name)
    if not server_config:
        raise ConnectionError(f"Unknown MCP server: {server_name}")

    toolset = MCPToolset(
        connection_params=SseServerParams(
            url=server_config["url"],
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    )

    try:
        await toolset.connect()
    except Exception as e:
        raise ConnectionError(f"Failed to connect to MCP server '{server_name}': {e}")

    _connection_pool[server_name] = toolset
    return toolset


async def close_all() -> None:
    """Gracefully closes all active MCP connections. Called during shutdown."""
    for name, toolset in _connection_pool.items():
        try:
            await toolset.close()
        except Exception:
            pass  # Best-effort cleanup
    _connection_pool.clear()
