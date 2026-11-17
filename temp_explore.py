import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def explore():
    url = "http://localhost:8001/mcp"
    print(f"Connecting to {url}")

    async with streamablehttp_client(url) as (
        read_stream,
        write_stream,
        get_session_id,
    ):
        print("Connected.")
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()

            print("TOOLS_START")
            for t in tools.tools:
                print(f"Name: {t.name}, Description: {t.description}")
            print("TOOLS_END")

if __name__ == "__main__":
    asyncio.run(explore())
