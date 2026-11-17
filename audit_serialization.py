import asyncio
import json
import traceback
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def audit_tool(url, tool_name, arguments):
    print(f"\n--- Auditing {tool_name} on {url} ---")
    try:
        async with streamablehttp_client(url) as (read_stream, write_stream, get_session_id):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                # We want to see the raw CallToolResult
                # session.call_tool returns a CallToolResult object
                result = await session.call_tool(tool_name, arguments)

                print(f"Tool: {tool_name}")
                print(f"isError: {result.isError}")
                print(f"content: {result.content}")
                print(f"structuredContent: {result.structuredContent}")

                # If content exists, print the first item's text if it's text
                if result.content:
                    for i, item in enumerate(result.content):
                        if hasattr(item, 'text'):
                            print(f"content[{i}].text: {repr(item.text)}")
                        else:
                            print(f"content[{i}]: {item}")

                return result
    except Exception as e:
        print(f"Error auditing {tool_name}: {e}")
        traceback.print_exc()

async def main():
    analysis_url = "http://localhost:8000/mcp"
    execution_url = "http://localhost:8001/mcp"

    print("\n=== ANALYSIS SERVER ===")
    # Audit get_positions
    await audit_tool(analysis_url, "get_positions", {"mode": "paper"})

    print("\n=== EXECUTION SERVER ===")
    # Audit get_positions
    await audit_tool(execution_url, "get_positions", {"mode": "paper"})

    # Audit list_order_proposals
    await audit_tool(execution_url, "list_order_proposals", {})

    # Audit get_execution_server_status
    await audit_tool(execution_url, "get_execution_server_status", {})

if __name__ == "__main__":
    asyncio.run(main())
