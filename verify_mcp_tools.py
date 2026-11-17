"""
End-to-end verification script for Day Trader AI MCP servers.
Tests both Analysis and Execution servers via local endpoints.
"""
import asyncio
import json
import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client

async def verify_server(s):
    print(f"\n--- {s['name']} SERVER ({s['url']}) ---")
    try:
        async with sse_client(s['url']) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                # 1. Tools inventory
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"\n[Inventory] Registered {len(tools)} tools:")
                for t in tools:
                    print(f"  - {t.name}")

                # 2. Server status
                tool_to_call = None
                for t in tools:
                    if t.name in ["server_status", "get_execution_server_status"]:
                        tool_to_call = t.name
                        break

                if tool_to_call:
                    res = await session.call_tool(tool_to_call, {})
                    print(f"\n[Status] {res.content}")

                # 3. Paper Positions
                if any(t.name == "get_positions" for t in tools):
                    res = await session.call_tool("get_positions", {"mode": "paper"})
                    print(f"\n[Positions] {res.content}")

                # 4. Proposals (Execution only)
                if s['name'] == "EXECUTION" and any(t.name == "list_order_proposals" for t in tools):
                    res = await session.call_tool("list_order_proposals", {"mode": "paper"})
                    print(f"\n[Proposals] {res.content}")
    except Exception as e:
        print(f"\n[Error] Failed to verify {s['name']}: {e}")

async def main():
    print("=" * 80)
    print("DAY TRADER AI MCP VERIFICATION (SSE)")
    print("=" * 80)

    servers = [
        {"name": "ANALYSIS", "url": "http://localhost:8000/mcp"},
        {"name": "EXECUTION", "url": "http://localhost:8001/mcp"}
    ]

    for s in servers:
        await verify_server(s)

    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
