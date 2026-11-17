#!/usr/bin/env python3

import asyncio
import json
import httpx

async def test_streamable_http():
    # Test connection to analysis-mcp
    async with httpx.AsyncClient() as client:
        try:
            # Attempt to send an SSE-like request
            headers = {
                'Content-Type': 'text/event-stream',
                'Accept': 'text/event-stream'
            }

            # Send a JSON-RPC initialize request
            response = await client.post(
                "http://analysis-mcp:8000/mcp",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "test",
                            "version": "1.0"
                        }
                    },
                    "id": 1
                }
            )

            print("Analysis MCP Response Status:", response.status_code)
            print("Analysis MCP Response:", response.text)
        except Exception as e:
            print("Analysis MCP Streamable HTTP test failed:", str(e))

    # Test connection to execution-mcp
    async with httpx.AsyncClient() as client:
        try:
            # Attempt to send an SSE-like request
            headers = {
                'Content-Type': 'text/event-stream',
                'Accept': 'text/event-stream'
            }

            # Send a JSON-RPC initialize request
            response = await client.post(
                "http://execution-mcp:8001/mcp",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "test",
                            "version": "1.0"
                        }
                    },
                    "id": 2
                }
            )

            print("Execution MCP Response Status:", response.status_code)
            print("Execution MCP Response:", response.text)
        except Exception as e:
            print("Execution MCP Streamable HTTP test failed:", str(e))

if __name__ == "__main__":
    asyncio.run(test_streamable_http())