"""
Simple SSE client that reads cached OAuth token and prints it for Claude Desktop.

Claude Desktop will use this to get the Bearer token for SSE connection.
"""
import json
import os
import sys

TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".quendoo_mcp_token.json")

# Check if we have a cached token
if os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, 'r') as f:
        token_data = json.load(f)
        access_token = token_data.get("access_token")

        if access_token:
            print(f"QUENDOO_ACCESS_TOKEN={access_token}", file=sys.stderr)
            # Set environment variable for SSE client
            os.environ["QUENDOO_ACCESS_TOKEN"] = access_token
        else:
            print("[WARNING] No access token found in cache", file=sys.stderr)
else:
    print("[WARNING] No token cache file found - OAuth required", file=sys.stderr)
    print(f"[INFO] Please run local_client.py first to authenticate", file=sys.stderr)
