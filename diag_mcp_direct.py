#!/usr/bin/env python3
"""Direct MCP test script"""
import json
import subprocess
import sys
import time
import urllib.request
import urllib.error

def start_server(port, script_path):
    """Start an MCP server"""
    proc = subprocess.Popen(
        [sys.executable, script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)
    return proc

def test_mcp_tools(port):
    """Test MCP tools/list endpoint"""
    url = f"http://localhost:{port}/mcp"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    data = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode()}
    except Exception as e:
        return {"error": str(e)}

# Start analysis server
print("Starting Analysis server on port 8000...")
analysis_proc = start_server(8000, "/Users/shabil/Downloads/day-trader-skill/chatgpt-mcp/server.py")

# Start execution server
print("Starting Execution server on port 8001...")
exec_proc = start_server(8001, "/Users/shabil/Downloads/day-trader-skill/chatgpt-mcp/execution_server.py")

time.sleep(3)

print("\n=== Testing Analysis Server (port 8000) ===")
result = test_mcp_tools(8000)
print(json.dumps(result, indent=2))

print("\n=== Testing Execution Server (port 8001) ===")
result = test_mcp_tools(8001)
print(json.dumps(result, indent=2))

# Cleanup
analysis_proc.terminate()
exec_proc.terminate()
analysis_proc.wait()
exec_proc.wait()
print("\nDone")