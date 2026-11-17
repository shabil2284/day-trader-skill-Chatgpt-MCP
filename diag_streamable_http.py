#!/usr/bin/env python3

import asyncio
import json
from mcp.client.session import ClientSession

async def test_mcp_connection():
    # Test connection to analysis-mcp
    try:
        client = ClientSession("http://analysis-mcp:8000/mcp", transport="streamable-http")
        await client.initialize()
        print("✅ Analysis MCP Streamable HTTP handshake successful!")

        # Test a simple tool call
        status = await client.server_status()
        print("Analysis MCP Status:", status)
    except Exception as e:
        print("❌ Analysis MCP Streamable HTTP handshake failed:", str(e))

    # Test connection to execution-mcp
    try:
        client = ClientSession("http://execution-mcp:8001/mcp", transport="streamable-http")
        await client.initialize()
        print("✅ Execution MCP Streamable HTTP handshake successful!")

        # Test a simple tool call
        status = await client.get_execution_server_status()
        print("Execution MCP Status:", status)
    except Exception as e:
        print("❌ Execution MCP Streamable HTTP handshake failed:", str(e))

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())