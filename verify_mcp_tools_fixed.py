
import asyncio
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def list_tools(url):
    async with streamablehttp_client(url) as (read_stream, write_stream, get_session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            return [t.name for t in tools]

async def call_tool(url, tool_name, arguments):
    async with streamablehttp_client(url) as (read_stream, write_stream, get_session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return {
                "tool": tool_name,
                "content": result.content,
                "structured_content": result.structuredContent,
                "is_error": result.isError
            }

async def main():
    execution_url = "http://localhost:8081/mcp"

    print("--- Tool Inventory (Execution 8081) ---")
    tools = await list_tools(execution_url)
    print(tools)

    print("\n--- Testing get_positions ---")
    pos = await call_tool(execution_url, "get_positions", {"mode": "paper"})
    print(pos)

    print("\n--- Testing list_order_proposals ---")
    props = await call_tool(execution_url, "list_order_proposals", {})
    print(props)

    print("\n--- Testing get_order_proposal ---")
    # Need a valid id or just test one that returns nothing
    try:
        p = await call_tool(execution_url, "get_order_proposal", {"proposal_id": "test"})
        print(p)
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Testing get_execution_status ---")
    s = await call_tool(execution_url, "get_execution_status", {})
    print(s)

if __name__ == "__main__":
    asyncio.run(main())
