"""
L4 — Gmail MCP Wrapper

Wraps the Gmail MCP server connection and exposes
load_gmail_tools() for the email_agent.
"""

from command_center.tools import auth_manager, mcp_gateway


async def load_gmail_tools() -> list:
    """
    Fetches a fresh OAuth2 access token for Gmail,
    connects to the Gmail MCP server, and returns the tool list.

    Tools typically returned by the Gmail MCP server:
      - gmail.messages.send      → send an email message
      - gmail.messages.list      → list/search messages
      - gmail.threads.get        → get full conversation thread
      - gmail.drafts.create      → create an email draft
      - gmail.drafts.send        → send an existing draft
      - gmail.users.labels.list  → list email labels
    """
    token = await auth_manager.get_token("gmail")
    toolset = await mcp_gateway.get_toolset("gmail", token)
    tools = await toolset.list_tools()
    return tools
