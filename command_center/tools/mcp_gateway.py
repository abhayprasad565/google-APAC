# ============================================================================
# FILE: tools/mcp_gateway.py
# LAYER: L4 — Tool & MCP Gateway
# ============================================================================
#
# PURPOSE:
#   Central connection manager for all MCP server connections. Maintains
#   persistent SSE connections to remote MCP servers, handles reconnection
#   on failure, and provides a unified get_toolset() interface for agent
#   files to call.
#
# KEY RESPONSIBILITIES:
#   1. Manage a connection pool of MCP server connections
#   2. Establish new SSE connections with proper auth headers
#   3. Check connection liveness and reconnect on failure
#   4. Provide a clean shutdown for all connections
#
# ============================================================================
#
#
# ── CONSTANT: MCP_SERVER_CONFIGS ────────────────────────────────────────────
#
#   dict[str, dict]
#   Maps server names to their connection configuration.
#
#   Structure:
#     {
#       "google_calendar" : {
#         url          : "https://calendar.googleapis.com/mcp/v1/sse",
#         auth_scheme  : "oauth"
#       },
#       "gmail" : {
#         url          : "https://gmail.googleapis.com/mcp/v1/sse",
#         auth_scheme  : "oauth"
#       }
#     }
#
#
# ── MODULE-LEVEL STATE: connection_pool ─────────────────────────────────────
#
#   dict[str, MCPToolset]
#   In-memory cache of active MCPToolset instances keyed by server name.
#   Checked before creating new connections.
#
#
# ── FUNCTION: get_toolset ───────────────────────────────────────────────────
#
# async function get_toolset(server_name, auth_token) -> MCPToolset
#
#   TASK:
#     Returns an active MCPToolset for the named MCP server. First checks
#     the connection pool for an existing, alive connection. If not found
#     or if the existing connection is dead, creates a new SSE connection
#     using the server config and auth token, stores it in the pool, and
#     returns it.
#
#   INPUT:
#     server_name : str
#       — which MCP server to connect to
#       — e.g. "google_calendar", "gmail"
#
#     auth_token  : str
#       — valid OAuth2 bearer token for the server
#
#   OUTPUT:
#     MCPToolset
#       — an ADK MCPToolset instance with all tools from that server
#         ready to use. The toolset has been connected and its tools
#         have been loaded.
#
#   ERROR HANDLING:
#     - If connection fails, raises ConnectionError with server_name
#     - If auth_token is expired, the connection will fail and caller
#       should refresh via auth_manager and retry
#
#
# ── FUNCTION: close_all ─────────────────────────────────────────────────────
#
# async function close_all() -> None
#
#   TASK:
#     Gracefully closes all active MCP connections in the pool.
#     Called during server shutdown (lifespan event in main.py).
#
#   INPUT:
#     None
#
#   OUTPUT:
#     None
#
#   SIDE EFFECTS:
#     - Closes all SSE connections
#     - Clears the connection_pool dict
#
# ============================================================================
