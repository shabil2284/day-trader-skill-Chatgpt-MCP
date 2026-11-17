from mcp.server.transport_security import TransportSecuritySettings

# Example implementation logic
# The previous attempt was:
# mcp.run(transport="streamable-http", allowed_hosts=[...])

# The correct implementation for FastMCP is:
# mcp.run(
#     transport="streamable-http",
#     transport_security=TransportSecuritySettings(allowed_hosts=[...])
# )
