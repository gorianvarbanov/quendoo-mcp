"""
MCP Wrapper v2 - Forces correct server URL
"""
import os
import sys
import subprocess

# FORCE the correct URL
os.environ["MCP_SERVER_URL"] = "https://quendoo-mcp-server-880871219885.us-central1.run.app"

print(f"[MCP Wrapper v2] Forcing URL: {os.environ['MCP_SERVER_URL']}", file=sys.stderr, flush=True)

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
local_client_path = os.path.join(script_dir, "local_client.py")

# Run local_client.py with the correct environment
result = subprocess.run([sys.executable, local_client_path], env=os.environ)
sys.exit(result.returncode)
