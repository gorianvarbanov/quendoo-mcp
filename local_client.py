"""
Local MCP Client Wrapper with OAuth Authentication.

This script runs locally on the user's machine and handles OAuth authentication
before proxying requests to the remote MCP server.
"""
import asyncio
import hashlib
import json
import os
import secrets
import sys
import webbrowser
from base64 import urlsafe_b64encode
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


# Configuration
# HARDCODED to force correct URL (ignore environment variable for now)
MCP_SERVER_URL = "https://quendoo-mcp-server-880871219885.us-central1.run.app"
print(f"[Quendoo MCP] Using HARDCODED server URL: {MCP_SERVER_URL}", file=sys.stderr, flush=True)
OAUTH_AUTHORIZE_URL = f"{MCP_SERVER_URL}/oauth/authorize"
OAUTH_TOKEN_URL = f"{MCP_SERVER_URL}/oauth/token"
OAUTH_CALLBACK_PORT = 3000
OAUTH_CLIENT_ID = "claude-desktop-public"

# Token storage
TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".quendoo_mcp_token.json")


def generate_pkce_pair():
    """Generate PKCE code_verifier and code_challenge."""
    code_verifier = urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback redirect."""

    authorization_code = None

    def do_GET(self):
        """Handle GET request with authorization code."""
        query = urlparse(self.path).query
        params = parse_qs(query)

        if 'code' in params:
            OAuthCallbackHandler.authorization_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
                <html>
                <body>
                    <h1>Authentication Successful!</h1>
                    <p>You can close this window and return to Claude Desktop.</p>
                    <script>window.close();</script>
                </body>
                </html>
            ''')
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Error: No authorization code received</h1></body></html>')

    def log_message(self, format, *args):
        """Suppress access log messages."""
        pass


def start_oauth_callback_server():
    """Start local HTTP server to receive OAuth callback."""
    server = HTTPServer(('127.0.0.1', OAUTH_CALLBACK_PORT), OAuthCallbackHandler)
    thread = Thread(target=server.handle_request, daemon=True)
    thread.start()
    return server


def load_token():
    """Load OAuth token from file."""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_token(token_data):
    """Save OAuth token to file."""
    try:
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f)
        print(f"[OAuth] Token saved to {TOKEN_FILE}", file=sys.stderr)
    except Exception as e:
        print(f"[OAuth] Failed to save token: {e}", file=sys.stderr)


async def perform_oauth_flow():
    """Perform OAuth 2.1 authorization code flow with PKCE."""
    print("[OAuth] Starting OAuth authentication flow...", file=sys.stderr)

    # Generate PKCE pair
    code_verifier, code_challenge = generate_pkce_pair()

    # Start local callback server
    server = start_oauth_callback_server()

    # Build authorization URL
    redirect_uri = f"http://127.0.0.1:{OAUTH_CALLBACK_PORT}"
    auth_params = {
        'response_type': 'code',
        'client_id': OAUTH_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'scope': 'openid profile email quendoo:pms',
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    }
    auth_url = f"{OAUTH_AUTHORIZE_URL}?{urlencode(auth_params)}"

    # Open browser for user authentication
    print(f"[OAuth] Opening browser for authentication...", file=sys.stderr)
    print(f"[OAuth] If browser doesn't open, visit: {auth_url}", file=sys.stderr)
    webbrowser.open(auth_url)

    # Wait for callback (with timeout)
    print("[OAuth] Waiting for authorization callback...", file=sys.stderr)
    for _ in range(60):  # Wait up to 60 seconds
        await asyncio.sleep(1)
        if OAuthCallbackHandler.authorization_code:
            break

    if not OAuthCallbackHandler.authorization_code:
        raise TimeoutError("OAuth callback timeout - no authorization code received")

    authorization_code = OAuthCallbackHandler.authorization_code
    print(f"[OAuth] Authorization code received", file=sys.stderr)

    # Exchange code for token
    print("[OAuth] Exchanging authorization code for access token...", file=sys.stderr)
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            OAUTH_TOKEN_URL,
            data={
                'grant_type': 'authorization_code',
                'code': authorization_code,
                'redirect_uri': redirect_uri,
                'client_id': OAUTH_CLIENT_ID,
                'code_verifier': code_verifier,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        if token_response.status_code != 200:
            raise Exception(f"Token exchange failed: {token_response.text}")

        token_data = token_response.json()
        print(f"[OAuth] Access token obtained successfully", file=sys.stderr)

        # Save token
        save_token(token_data)

        return token_data['access_token']


async def get_access_token():
    """Get valid access token (from cache or perform OAuth flow)."""
    # Try to load cached token
    token_data = load_token()
    if token_data and 'access_token' in token_data:
        print("[OAuth] Using cached access token", file=sys.stderr)
        return token_data['access_token']

    # Perform OAuth flow
    return await perform_oauth_flow()


async def main():
    """Main entry point for local MCP client."""
    print("[Quendoo MCP] Starting local client (lazy OAuth - auth on first tool use)...", file=sys.stderr)

    # FORCE: Do NOT use cached token - always start fresh for lazy OAuth
    # This ensures we don't use old JWT tokens with wrong RSA keys
    access_token = None
    print("[OAuth] Starting without token - will authenticate on first tool use", file=sys.stderr)

    try:
        # Connect to MCP server
        sse_url = f"{MCP_SERVER_URL}/sse"
        print(f"[Quendoo MCP] Connecting to {sse_url}", file=sys.stderr)

        # Try to connect (will retry with OAuth if needed)
        retry_connection = True
        max_auth_attempts = 2
        auth_attempt = 0

        while retry_connection and auth_attempt < max_auth_attempts:
            retry_connection = False

            headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
            print(f"[DEBUG] access_token={access_token}", file=sys.stderr)
            print(f"[DEBUG] headers={headers}", file=sys.stderr)

            try:
                async with sse_client(sse_url, headers=headers) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        print("[Quendoo MCP] Connected successfully!", file=sys.stderr)

                        # Proxy stdin/stdout
                        async def read_stdin():
                            """Read from stdin and send to remote server."""
                            while True:
                                line = await asyncio.get_event_loop().run_in_executor(
                                    None, sys.stdin.readline
                                )
                                if not line:
                                    break
                                await write.send(json.loads(line))

                        async def write_stdout():
                            """Read from remote server and write to stdout."""
                            async for message in read:
                                print(json.dumps(message), flush=True)

                        # Run both tasks concurrently
                        await asyncio.gather(read_stdin(), write_stdout())

            except (Exception, BaseExceptionGroup) as e:
                # Handle both regular exceptions and ExceptionGroups (Python 3.11+)
                error_str = str(e).lower()

                # For ExceptionGroups, check nested exceptions
                is_auth_error = False
                if isinstance(e, BaseExceptionGroup):
                    # Check if any sub-exception is an auth error
                    for exc in e.exceptions:
                        exc_str = str(exc).lower()
                        if ('unauthorized' in exc_str or '401' in exc_str or
                            'authentication' in exc_str or 'forbidden' in exc_str):
                            is_auth_error = True
                            break
                else:
                    # Regular exception
                    if ('unauthorized' in error_str or '401' in error_str or
                        'authentication' in error_str or 'forbidden' in error_str):
                        is_auth_error = True

                if is_auth_error:
                    auth_attempt += 1
                    if auth_attempt < max_auth_attempts:
                        print(f"[OAuth] Authentication required - starting OAuth flow (attempt {auth_attempt})...", file=sys.stderr)
                        try:
                            access_token = await perform_oauth_flow()
                            print("[OAuth] Authentication successful! Reconnecting...", file=sys.stderr)
                            retry_connection = True
                        except Exception as oauth_error:
                            print(f"[OAuth] Authentication failed: {oauth_error}", file=sys.stderr)
                            raise
                    else:
                        print(f"[OAuth] Max authentication attempts reached", file=sys.stderr)
                        raise
                else:
                    # Not an auth error, re-raise
                    raise

    except Exception as e:
        print(f"[Quendoo MCP] Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
