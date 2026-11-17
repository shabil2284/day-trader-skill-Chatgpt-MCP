import requests
import json

def get_mcp_capabilities(url):
    try:
        # Initialize
        init_resp = requests.post(f"{url}/initialize", json={
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }, timeout=5)

        if init_resp.status_code != 200:
            return f"Failed to initialize: {init_resp.text}"

        # List tools
        tools_resp = requests.post(f"{url}/tools/list", json={}, timeout=5)

        if tools_resp.status_code != 200:
            return f"Failed to list tools: {tools_resp.text}"

        return tools_resp.json()
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    execution_url = "http://localhost:8081/mcp"
    analysis_url = "http://localhost:8080/mcp"

    print("--- Execution Tunnel (8081) ---")
    print(json.dumps(get_mcp_capabilities(execution_url), indent=2))

    print("\n--- Analysis Tunnel (8080) ---")
    print(json.dumps(get_mcp_capabilities(analysis_url), indent=2))
