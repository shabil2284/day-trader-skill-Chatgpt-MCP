import asyncio
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def call_tool(url, tool_name, arguments):
    async with streamablehttp_client(url) as (read_stream, write_stream, get_session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return result

async def main():
    print("\n--- 1. Checking Analysis MCP Status ---")
    analysis_status = await call_tool("http://localhost:8000/mcp", "server_status", {})
    print(analysis_status.content[0].text if analysis_status.content else analysis_status)

    print("\n--- 2. Checking Execution MCP Status ---")
    exec_status = await call_tool("http://localhost:8001/mcp", "get_execution_server_status", {})
    print(exec_status.content[0].text if exec_status.content else exec_status)

    print("\n--- 3. Calling get_positions (Analysis) ---")
    positions = await call_tool("http://localhost:8000/mcp", "get_positions", {"mode": "paper"})
    print("Raw positions output:", positions)

    print("\n--- 4. Listing Proposals (Execution) ---")
    proposals = await call_tool("http://localhost:8001/mcp", "list_order_proposals", {})
    print("Raw proposals output:", proposals)

    if proposals.structuredContent:
        proposal_list = proposals.structuredContent
    elif proposals.content and hasattr(proposals.content[0], "text"):
        proposal_list = json.loads(proposals.content[0].text)
    else:
        proposal_list = []

    print(f"Found {len(proposal_list)} proposals.")

    if proposal_list and isinstance(proposal_list, list) and len(proposal_list) > 0:
        p_id = proposal_list[0].get("id")
        print(f"\n--- 5. Calling get_execution_status for ID: {p_id} ---")
        status = await call_tool("http://localhost:8001/mcp", "get_execution_status", {"proposal_id": p_id})
        print(status.content[0].text if status.content else status)
    else:
        print("\n--- 5. Skipping get_execution_status (no valid proposal ID available) ---")

if __name__ == "__main__":
    asyncio.run(main())
