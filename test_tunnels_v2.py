import httpx
import json
import asyncio

async def get_mcp_capabilities(url):
    try:
        async with httpx.AsyncClient() as client:
            # Initialize
            init_resp = await client.post(f"{url}/initialize", json={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }, timeout=10)

            if init_resp.status_code != 200:
                return f"Failed to initialize: {init_resp.text}"

            # List tools
            tools_resp = await client.post(f"{url}/tools/list", json={}, timeout=10)

            if tools_resp.status_code != 200:
                return f"Failed to list tools: {tools_resp.text}"

            return tools_resp.json()
    except Exception as e:
        return f"Error: {str(e)}"

async def main():
    execution_url = "http://localhost:8081"
    analysis_url = "http://localhost:8080"

    print("--- Execution Tunnel (8081) ---")
    print(await get_mcp_capabilities(execution_url))

    print("\n--- Analysis Tunnel (8080) ---")
    print(await get_mcp_capabilities(analysis_url))

if __name__ == "__main__":
    asyncio.run(main())
