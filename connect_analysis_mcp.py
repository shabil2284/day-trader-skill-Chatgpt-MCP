import asyncio
import sys
from mcp.client.streamable_http import streamable_http_client
from mcp.client.session import ClientSession

async def main():
    url = "http://localhost:8000/mcp"

    try:
        async with streamable_http_client(url) as (read_stream, write_stream, get_session_id):
            client = ClientSession(read_stream, write_stream)

            print("Successfully connected")

            # Initialize
            print("Calling initialize()...")
            init_result = await client.initialize()
            print("initialize() successful:", init_result)

            # List tools
            print("Calling list_tools()...")
            tools = await client.list_tools()
            print("Tools count:", len(tools.tools))

            # Server status
            print("Calling server_status()...")
            status = await client.call_tool("server_status", {})
            print("Server status:", status.structuredContent)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
