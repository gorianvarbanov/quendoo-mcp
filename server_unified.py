"""
Unified Quendoo MCP Server with OAuth 2.1 support.

This server combines:
1. MCP server with FastMCP for tool execution
2. OAuth 2.1 authorization server endpoints
3. SSE transport for MCP communication
"""

import os
import sys
from typing import Optional

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session
from flask_cors import CORS
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

from oauth_server import OAuthServer
from tools import (
    AutomationClient,
    EmailClient,
    QuendooClient,
    register_auth_tools,
    register_automation_tools,
    register_availability_tools,
    register_booking_tools,
    register_email_tools,
    register_property_tools,
)
from tools.database import DatabaseClient
from tools.jwt_auth import decode_jwt_token

load_dotenv()


class JWTTokenVerifier(TokenVerifier):
    """Verify JWT tokens for MCP authentication."""

    def __init__(self, db_client: DatabaseClient) -> None:
        self.db = db_client

    async def verify_token(self, token: str) -> AccessToken | None:
        # Decode JWT token
        payload = decode_jwt_token(token)
        if not payload:
            return None

        user_id = payload.get("user_id")
        email = payload.get("email")

        if not user_id or not email:
            return None

        # Load user from database to verify they still exist
        user = self.db.get_user_by_id(user_id)
        if not user:
            return None

        # Return access token with user_id as client_id
        return AccessToken(
            token=token, client_id=f"user:{user_id}", scopes=[]
        )


def _get_auth_settings() -> AuthSettings | None:
    """Get OAuth authentication settings."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        base_url = os.getenv(
            "OAUTH_BASE_URL",
            "https://quendoo-mcp-server-880871219885.us-central1.run.app"
        )
        return AuthSettings(
            issuer_url=base_url, resource_server_url=f"{base_url}/sse"
        )
    return None


def _get_token_verifier(auth: AuthSettings | None) -> Optional[TokenVerifier]:
    """Get token verifier for MCP authentication."""
    database_url = os.getenv("DATABASE_URL")
    if database_url and auth:
        try:
            db_client = DatabaseClient(database_url)
            return JWTTokenVerifier(db_client)
        except Exception as e:
            print(
                f"Warning: Failed to initialize JWT auth: {e}.",
                file=sys.stderr
            )
    return None


# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "CHANGE_THIS_IN_PRODUCTION")
CORS(app)

# Initialize OAuth server
oauth = OAuthServer()
db = DatabaseClient()

# Initialize MCP server
client = QuendooClient(api_key=None)
automation_bearer = os.getenv("QUENDOO_AUTOMATION_BEARER")
automation_client = AutomationClient(bearer_token=automation_bearer)
email_client = EmailClient()
auth_settings = _get_auth_settings()
token_verifier = _get_token_verifier(auth_settings)

mcp = FastMCP(
    name="quendoo-pms-mcp",
    instructions=(
        "Quendoo PMS & Communication MCP Server with OAuth 2.1 Authentication\n\n"
        "AUTHENTICATION OPTIONS:\n\n"
        "Option 1 - OAuth 2.1 (Recommended for Claude Desktop):\n"
        "  - Claude Desktop will automatically handle OAuth flow\n"
        "  - You'll be redirected to authorize the application\n"
        "  - Your Quendoo API key will be loaded from your registered account\n\n"
        "Option 2 - Manual Authentication (Fallback):\n"
        "  - Use authenticate_with_token(jwt_token='your-jwt-token')\n"
        "  - Or use set_quendoo_api_key(api_key='your-key')\n\n"
        "AVAILABLE TOOLS:\n"
        "- Property Management: List properties, get booking modules, check availability\n"
        "- Bookings: Create, update, retrieve bookings\n"
        "- Email: Send HTML emails via send_quendoo_email\n"
        "- Voice Calls: Make automated calls via make_call"
    ),
    token_verifier=token_verifier,
    auth=auth_settings,
)

# Register MCP tools
register_property_tools(mcp, client)
register_availability_tools(mcp, client)
register_booking_tools(mcp, client)
register_auth_tools(mcp)
register_automation_tools(mcp, automation_client)
register_email_tools(mcp, email_client)

# Global MCP transport
mcp_transport: Optional[SseServerTransport] = None


# ============================================================================
# OAuth 2.1 Endpoints
# ============================================================================


@app.route("/.well-known/openid-configuration", methods=["GET"])
def metadata_discovery():
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    return jsonify(oauth.get_metadata())


@app.route("/oauth/register", methods=["POST"])
def register_client():
    """Dynamic Client Registration (RFC 7591)."""
    try:
        data = request.json

        # Required fields
        client_name = data.get("client_name")
        redirect_uris = data.get("redirect_uris", [])

        if not client_name:
            return (
                jsonify({
                    "error": "invalid_client_metadata",
                    "error_description": "client_name is required"
                }),
                400,
            )

        if not redirect_uris:
            return (
                jsonify({
                    "error": "invalid_redirect_uri",
                    "error_description": "redirect_uris is required"
                }),
                400,
            )

        # Optional fields
        grant_types = data.get("grant_types", ["authorization_code", "refresh_token"])
        response_types = data.get("response_types", ["code"])
        token_endpoint_auth_method = data.get(
            "token_endpoint_auth_method", "client_secret_basic"
        )
        scope = data.get("scope", "openid profile email quendoo:pms")

        # Register client
        client_info = oauth.register_client(
            client_name=client_name,
            redirect_uris=redirect_uris,
            grant_types=grant_types,
            response_types=response_types,
            token_endpoint_auth_method=token_endpoint_auth_method,
            scope=scope,
        )

        return jsonify(client_info), 201

    except Exception as e:
        return jsonify({"error": "server_error", "error_description": str(e)}), 500


@app.route("/oauth/authorize", methods=["GET", "POST"])
def authorize():
    """Authorization endpoint with user consent."""
    if request.method == "GET":
        # Extract OAuth parameters
        client_id = request.args.get("client_id")
        redirect_uri = request.args.get("redirect_uri")
        response_type = request.args.get("response_type", "code")
        scope = request.args.get("scope", "openid profile email quendoo:pms")
        state = request.args.get("state")
        code_challenge = request.args.get("code_challenge")
        code_challenge_method = request.args.get("code_challenge_method", "S256")

        # Validate required parameters
        if not client_id or not redirect_uri or not code_challenge:
            return (
                jsonify({
                    "error": "invalid_request",
                    "error_description": "Missing required parameters: client_id, redirect_uri, code_challenge",
                }),
                400,
            )

        # Verify client exists
        client = oauth.get_client(client_id)
        if not client:
            return (
                jsonify({
                    "error": "invalid_client",
                    "error_description": "Unknown client_id",
                }),
                400,
            )

        # Verify redirect_uri is registered
        if redirect_uri not in client["redirect_uris"]:
            return (
                jsonify({
                    "error": "invalid_request",
                    "error_description": "redirect_uri not registered for this client",
                }),
                400,
            )

        # Store OAuth params in session
        session["oauth_request"] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": response_type,
            "scope": scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "client_name": client["client_name"],
        }

        # Show authorization/login page
        return render_template(
            "authorize.html", client_name=client["client_name"], scope=scope
        )

    elif request.method == "POST":
        from urllib.parse import urlencode

        # Get OAuth request from session
        oauth_request = session.get("oauth_request")
        if not oauth_request:
            return (
                jsonify({
                    "error": "invalid_request",
                    "error_description": "No active authorization request",
                }),
                400,
            )

        # Get login credentials or existing JWT token
        email = request.form.get("email")
        password = request.form.get("password")
        jwt_token = request.form.get("jwt_token")
        action = request.form.get("action")

        # Check if user denied authorization
        if action == "deny":
            error_params = {
                "error": "access_denied",
                "error_description": "User denied authorization",
            }
            if oauth_request["state"]:
                error_params["state"] = oauth_request["state"]

            redirect_url = f"{oauth_request['redirect_uri']}?{urlencode(error_params)}"
            return redirect(redirect_url)

        # Authenticate user
        user = None

        # Option 1: JWT token from web registration
        if jwt_token:
            payload = decode_jwt_token(jwt_token)
            if payload:
                user_id = payload.get("user_id")
                if user_id:
                    user = db.get_user_by_id(user_id)

        # Option 2: Email/password login
        elif email and password:
            user = db.authenticate_user(email, password)

        if not user:
            return render_template(
                "authorize.html",
                client_name=oauth_request["client_name"],
                scope=oauth_request["scope"],
                error="Invalid credentials or token",
            )

        # Create authorization code
        code = oauth.create_authorization_code(
            client_id=oauth_request["client_id"],
            user_id=user["id"],
            redirect_uri=oauth_request["redirect_uri"],
            scope=oauth_request["scope"],
            code_challenge=oauth_request["code_challenge"],
            code_challenge_method=oauth_request["code_challenge_method"],
        )

        # Build redirect URL with authorization code
        redirect_params = {"code": code}
        if oauth_request["state"]:
            redirect_params["state"] = oauth_request["state"]

        redirect_url = f"{oauth_request['redirect_uri']}?{urlencode(redirect_params)}"

        # Clear session
        session.pop("oauth_request", None)

        return redirect(redirect_url)


@app.route("/oauth/token", methods=["POST"])
def token_endpoint():
    """Token endpoint for code exchange."""
    try:
        # Get parameters from form data or JSON
        if request.is_json:
            data = request.json
        else:
            data = request.form.to_dict()

        grant_type = data.get("grant_type")
        code = data.get("code")
        redirect_uri = data.get("redirect_uri")
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
        code_verifier = data.get("code_verifier")

        # Validate grant type
        if grant_type != "authorization_code":
            return (
                jsonify({
                    "error": "unsupported_grant_type",
                    "error_description": "Only authorization_code grant type is supported",
                }),
                400,
            )

        # Validate required parameters
        if not all([code, redirect_uri, client_id, code_verifier]):
            return (
                jsonify({
                    "error": "invalid_request",
                    "error_description": "Missing required parameters",
                }),
                400,
            )

        # Check for client credentials in Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Basic "):
            import base64

            try:
                decoded = base64.b64decode(auth_header[6:]).decode()
                header_client_id, header_client_secret = decoded.split(":", 1)
                client_id = header_client_id
                client_secret = header_client_secret
            except Exception:
                pass

        # Exchange code for token
        token_response = oauth.exchange_code_for_token(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )

        if not token_response:
            return (
                jsonify({
                    "error": "invalid_grant",
                    "error_description": "Invalid authorization code or verification failed",
                }),
                400,
            )

        return jsonify(token_response)

    except Exception as e:
        return jsonify({"error": "server_error", "error_description": str(e)}), 500


@app.route("/oauth/userinfo", methods=["GET"])
def userinfo():
    """User info endpoint."""
    # Get access token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return (
            jsonify({
                "error": "invalid_token",
                "error_description": "Missing or invalid Authorization header",
            }),
            401,
        )

    access_token = auth_header[7:]  # Remove "Bearer " prefix

    # Get user info
    user_info = oauth.get_user_info(access_token)
    if not user_info:
        return (
            jsonify({
                "error": "invalid_token",
                "error_description": "Invalid or expired access token",
            }),
            401,
        )

    return jsonify(user_info)


# ============================================================================
# MCP SSE Endpoints
# ============================================================================


@app.route("/sse", methods=["GET"])
def sse_endpoint():
    """SSE endpoint for MCP communication."""
    global mcp_transport

    # Create SSE transport
    mcp_transport = SseServerTransport("/messages")

    # Connect MCP server to transport
    async def connect():
        async with mcp_transport.connect_sse(
            request.environ, []
        ) as (read_stream, write_stream):
            await mcp.run(read_stream, write_stream, mcp.create_initialization_options())

    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(connect())
    finally:
        loop.close()

    return mcp_transport.get_response()


@app.route("/messages", methods=["POST"])
def messages_endpoint():
    """Handle POST messages for MCP."""
    global mcp_transport

    if not mcp_transport:
        return jsonify({"error": "SSE connection not established"}), 400

    # Handle the message
    mcp_transport.handle_post_message(request.get_data(), request.headers)

    return "", 204


# ============================================================================
# Health Check
# ============================================================================


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "oauth_enabled": bool(os.getenv("DATABASE_URL")),
        "mcp_version": "1.0.0"
    })


if __name__ == "__main__":
    print("Quendoo MCP Server with OAuth 2.1 starting...", file=sys.stderr)
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
