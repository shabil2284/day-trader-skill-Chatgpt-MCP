import asyncio
import traceback

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def explore_mcp(name, url):
    print("\n" + "=" * 70)
    print(f"Exploring MCP server: {name} ({url})")
    print("=" * 70)

    try:
        async with streamablehttp_client(url) as (
            read_stream,
            write_stream,
            get_session_id,
        ):
            print("HTTP connection established.")

            async with ClientSession(
                read_stream,
                write_stream
            ) as session:
                print("Sending MCP initialize request...")
                init = await session.initialize()
                print("Initialized:", init.serverInfo)

                print("Listing tools...")
                tools = await session.list_tools()
                print("Tools:", [t.name for t in tools.tools])

                print("Checking server status...")
                if name == "Analysis MCP":
                    status = await session.call_tool("server_status", arguments={})
                    print("Status Result:", status)
                elif name == "Execution MCP":
                    try:
                        status = await session.call_tool("get_execution_server_status", arguments={})
                        print("Status Result:", status)
                    except Exception as e:
                        print("get_execution_server_status call failed (expected if not registered/available):", e)

                return True

    except BaseException as error:
        print(f"\nFAILED exploring {name}.")
        traceback.print_exception(type(error), error, error.__traceback__)
        return False


async def main():
    servers = [
        ("Analysis MCP", "http://localhost:8000/mcp"),
        ("Execution MCP", "http://localhost:8001/mcp"),
    ]

    for name, url in servers:
        await explore_mcp(name, url)


if __name__ == "__main__":
    asyncio.run(main())
