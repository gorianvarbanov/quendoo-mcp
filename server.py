"""Quendoo MCP Server v2.0 - OAuth Edition - FIXED"""
import os
import sys
from typing import Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings

from tools import (
    AutomationClient,
    EmailClient,
    register_automation_tools,
    register_email_tools,
)
from tools.jwt_auth import decode_jwt_token
from tools.database import DatabaseClient
from stytch_auth import StytchAuthenticator


load_dotenv()


class JWTTokenVerifier(TokenVerifier):
    """Verify JWT tokens and load user API keys from database."""

    def __init__(self, db_client: DatabaseClient) -> None:
        self.db = db_client

    async def verify_token(self, token: str) -> AccessToken | None:
        print(f"[DEBUG JWT_VERIFIER] ===== Verifying JWT token =====", file=sys.stderr, flush=True)
        print(f"[DEBUG JWT_VERIFIER] Token (first 30 chars): {token[:30]}...", file=sys.stderr, flush=True)

        # Decode JWT token
        payload = decode_jwt_token(token)
        print(f"[DEBUG JWT_VERIFIER] Decoded payload: {payload is not None}", file=sys.stderr, flush=True)

        if not payload:
            print(f"[DEBUG JWT_VERIFIER] JWT decode failed!", file=sys.stderr, flush=True)
            return None

        user_id = payload.get("user_id")
        email = payload.get("email")
        print(f"[DEBUG JWT_VERIFIER] Extracted user_id={user_id}, email={email}", file=sys.stderr, flush=True)

        if not user_id or not email:
            print(f"[DEBUG JWT_VERIFIER] Missing user_id or email in payload!", file=sys.stderr, flush=True)
            return None

        # Load user from database to verify they still exist
        user = self.db.get_user_by_id(user_id)
        print(f"[DEBUG JWT_VERIFIER] User found in DB: {user is not None}", file=sys.stderr, flush=True)

        if not user:
            print(f"[DEBUG JWT_VERIFIER] User not found in database!", file=sys.stderr, flush=True)
            return None

        # Return access token with user_id as client_id
        # This allows us to use ctx.client_id in the tools
        client_id = f"user:{user_id}"
        print(f"[DEBUG JWT_VERIFIER] Returning AccessToken with client_id={client_id}", file=sys.stderr, flush=True)
        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=[]
        )


class StaticTokenVerifier(TokenVerifier):
    """Verify a single bearer token provided via environment variable (fallback)."""

    def __init__(self, token: str) -> None:
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        if token != self._token:
            return None
        return AccessToken(token=token, client_id="static-token", scopes=[])


class StytchTokenVerifier(TokenVerifier):
    """Verify Stytch OAuth tokens and load user API keys from database."""

    def __init__(self, stytch_auth: StytchAuthenticator, db_client: DatabaseClient) -> None:
        self.stytch = stytch_auth
        self.db = db_client

    async def verify_token(self, token: str) -> AccessToken | None:
        # Validate Stytch token
        token_data = self.stytch.validate_token(token)
        if not token_data:
            return None

        stytch_user_id = token_data.get("user_id")
        email = token_data.get("email")

        if not stytch_user_id or not email:
            return None

        # Load or create user in database
        user = self.db.get_user_by_stytch_id(stytch_user_id)
        if not user:
            # Create new user from Stytch authentication
            user_id = self.db.create_or_update_stytch_user(
                stytch_user_id=stytch_user_id,
                email=email
            )
        else:
            user_id = user["id"]

        # Return access token with user_id as client_id
        return AccessToken(
            token=token,
            client_id=f"stytch:{user_id}",
            scopes=["quendoo:pms"]
        )


def _get_auth_settings() -> AuthSettings | None:
    # Use custom OAuth server (issuer is our MCP server)
    mcp_server_url = os.getenv("MCP_SERVER_URL", "https://quendoo-mcp-server-880871219885.us-central1.run.app")
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # Our MCP server is both issuer and resource server
        return AuthSettings(issuer_url=mcp_server_url, resource_server_url=mcp_server_url)

    # Fallback: static bearer token
    token = os.getenv("BEARER_TOKEN")
    if token:
        return AuthSettings(issuer_url=mcp_server_url, resource_server_url=mcp_server_url)

    return None


def _get_token_verifier(auth: AuthSettings | None) -> Optional[TokenVerifier]:
    database_url = os.getenv("DATABASE_URL")

    # Priority 1: JWT auth with database (for our OAuth tokens)
    if database_url and auth:
        try:
            db_client = DatabaseClient(database_url)
            print("JWT authentication enabled", file=sys.stderr)
            return JWTTokenVerifier(db_client)
        except Exception as e:
            print(f"Warning: Failed to initialize JWT auth: {e}.", file=sys.stderr)

    # Priority 2: Stytch OAuth (fallback for direct Stytch tokens)
    stytch_project_id = os.getenv("STYTCH_PROJECT_ID")
    stytch_secret = os.getenv("STYTCH_SECRET")
    stytch_domain = os.getenv("STYTCH_PROJECT_DOMAIN")

    if all([stytch_project_id, stytch_secret, stytch_domain, database_url]) and auth:
        try:
            stytch_auth = StytchAuthenticator()
            db_client = DatabaseClient(database_url)
            print("Stytch OAuth authentication enabled as fallback", file=sys.stderr)
            return StytchTokenVerifier(stytch_auth, db_client)
        except ValueError as e:
            print(f"Stytch not configured: {e}.", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Failed to initialize Stytch auth: {e}.", file=sys.stderr)

    # Priority 3: static bearer token
    token = os.getenv("BEARER_TOKEN")
    if token and auth:
        print("Static token authentication enabled", file=sys.stderr)
        return StaticTokenVerifier(token)

    return None

# Configure automation and email clients
automation_bearer = os.getenv("QUENDOO_AUTOMATION_BEARER")
automation_client = AutomationClient(bearer_token=automation_bearer)
email_client = EmailClient()
auth_settings = _get_auth_settings()
token_verifier = _get_token_verifier(auth_settings)

server = FastMCP(
    name="quendoo-pms-mcp",
    instructions=(
        "Quendoo Property Management System - Fully Authenticated MCP Server\n\n"
        "✅ You are authenticated and ready to use all tools immediately.\n"
        "✅ API credentials are automatically loaded from your account.\n"
        "✅ No additional setup required - just use the tools!\n\n"
        "📋 AVAILABLE TOOLS:\n"
        "- Property Management: Properties, booking modules, availability\n"
        "- Bookings: Create, update, retrieve bookings\n"
        "- Email: Send HTML emails\n"
        "- Voice Calls: Automated calls with Bulgarian support\n\n"
        "All tools work immediately - authentication is automatic!"
    ),
    token_verifier=token_verifier,
    auth=auth_settings,
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8080")),
)

# ========================================
# REGISTER TOOLS WITH LAZY API KEY LOADING
# ========================================

from mcp.server.fastmcp import Context
from tools.client import QuendooClient


def extract_user_id(client_id: str) -> str:
    """Extract numeric user_id from client_id like 'user:123' or 'stytch:456'."""
    if ":" in client_id:
        return client_id.split(":", 1)[1]
    return client_id


def get_user_quendoo_client(ctx: Context) -> QuendooClient:
    """
    Load user's Quendoo API key from database and create authenticated client.

    This is called INSIDE each tool, not during registration.
    """
    print(f"[DEBUG] get_user_quendoo_client: client_id={ctx.client_id}", file=sys.stderr, flush=True)

    # Extract user_id from context
    user_id = extract_user_id(ctx.client_id)
    print(f"[DEBUG] Extracted user_id={user_id}", file=sys.stderr, flush=True)

    # Load user from database
    database_url = os.getenv("DATABASE_URL")
    db = DatabaseClient(database_url)
    user = db.get_user_by_id(user_id)
    
    if not user:
        raise ValueError(f"User {user_id} not found in database")
    
    quendoo_api_key = user.get("quendoo_api_key")
    print(f"[DEBUG] User quendoo_api_key present: {bool(quendoo_api_key)}", file=sys.stderr, flush=True)
    
    if not quendoo_api_key:
        raise ValueError(
            "Quendoo API key not configured. Please set it up using the set_quendoo_api_key tool first."
        )
    
    # Create client with user's API key
    print(f"[DEBUG] Creating QuendooClient with user's API key", file=sys.stderr, flush=True)
    return QuendooClient(api_key=quendoo_api_key)


# ========================================
# PROPERTY TOOLS
# ========================================

@server.tool()
def get_property_settings(
    ctx: Context,
    api_lng: str | None = None,
    names: str | None = None
) -> dict:
    """
    Get property settings including rooms, rates, services, meals, beds, booking modules, payment methods, and channel codes.

    Args:
        api_lng: Language code (e.g., 'en', 'bg'). Optional.
        names: Comma-separated list of setting names to retrieve. Optional.
    """
    print(f"[DEBUG TOOL] get_property_settings called", file=sys.stderr, flush=True)
    client = get_user_quendoo_client(ctx)
    params = {"api_lng": api_lng, "names": names}
    return client.get("/Property/getPropertySettings", params=params)


@server.tool()
def get_rooms_details(
    ctx: Context,
    api_lng: str | None = None,
    room_id: int | None = None
) -> dict:
    """
    Get detailed information for rooms. Optionally filter by room_id and language.

    Args:
        api_lng: Language code for room details. Optional.
        room_id: Specific room ID to get details for. Optional (returns all rooms if omitted).
    """
    print(f"[DEBUG TOOL] get_rooms_details called", file=sys.stderr, flush=True)
    client = get_user_quendoo_client(ctx)
    params = {"api_lng": api_lng, "room_id": room_id}
    return client.get("/Property/getRoomsDetails", params=params)


# ========================================
# AVAILABILITY TOOLS
# ========================================

@server.tool(name="get_availability")
def quendoo_get_availability(
    ctx: Context,
    date_from: str,
    date_to: str,
    sysres: str
) -> dict:
    """
    Get availability for a date range and system (qdo or ext).

    Args:
        date_from: Start date in YYYY-MM-DD format
        date_to: End date in YYYY-MM-DD format
        sysres: System reservation type ('qdo' for Quendoo or 'ext' for external)
    """
    print(f"[DEBUG TOOL] NEW get_availability called: {date_from} to {date_to}, sysres={sysres}", file=sys.stderr, flush=True)
    client = get_user_quendoo_client(ctx)
    print(f"[DEBUG AVAILABILITY] Got client, calling API...", file=sys.stderr, flush=True)
    params = {"date_from": date_from, "date_to": date_to, "sysres": sysres}
    result = client.get("/Availability/getAvailability", params=params)
    print(f"[DEBUG AVAILABILITY] API returned: {result is not None}", file=sys.stderr, flush=True)
    return result


@server.tool()
def update_availability(
    ctx: Context,
    values: list[dict]
) -> dict:
    """
    Update availability values for rooms or external rooms.

    Args:
        values: List of availability updates, each containing:
            - date: Date in YYYY-MM-DD format
            - room_id or ext_room_id: Room identifier
            - avail: Availability count (integer)
    """
    print(f"[DEBUG TOOL] update_availability called", file=sys.stderr, flush=True)
    client = get_user_quendoo_client(ctx)
    payload = {"values": values}
    return client.post("/Availability/updateAvailability", json=payload)


# ========================================
# BOOKING TOOLS
# ========================================

@server.tool()
def get_bookings(ctx: Context) -> dict:
    """
    List all bookings for the property.
    """
    print(f"[DEBUG TOOL] get_bookings called", file=sys.stderr, flush=True)
    client = get_user_quendoo_client(ctx)
    return client.get("/Booking/getBookings")


@server.tool()
def get_booking_offers(
    ctx: Context,
    bm_code: str,
    date_from: str,
    nights: int,
    api_lng: str | None = None,
    guests: list[dict] | None = None,
    currency: str | None = None
) -> dict:
    """
    Fetch booking offers for a booking module code and stay dates.

    Args:
        bm_code: Booking module code (e.g., 'BM001')
        date_from: Check-in date in YYYY-MM-DD format
        nights: Number of nights
        api_lng: Language code. Optional.
        guests: List of guest objects. Optional.
        currency: Currency code (e.g., 'EUR', 'USD'). Optional.
    """
    print(f"[DEBUG TOOL] get_booking_offers called", file=sys.stderr, flush=True)
    client = get_user_quendoo_client(ctx)
    params = {
        "bm_code": bm_code,
        "date_from": date_from,
        "nights": nights,
        "api_lng": api_lng,
        "currency": currency
    }
    payload = {"guests": guests} if guests else {}
    return client.post("/Booking/getBookingOffers", params=params, json=payload)


@server.tool()
def ack_booking(
    ctx: Context,
    booking_id: int,
    revision_id: str
) -> dict:
    """
    Acknowledge a booking using booking_id and revision_id.

    Args:
        booking_id: Booking ID
        revision_id: Revision ID
    """
    print(f"[DEBUG TOOL] ack_booking called", file=sys.stderr, flush=True)
    client = get_user_quendoo_client(ctx)
    payload = {"booking_id": booking_id, "revision_id": revision_id}
    return client.post("/Booking/ackBooking", json=payload)


@server.tool()
def post_room_assignment(
    ctx: Context,
    booking_id: int,
    revision_id: str
) -> dict:
    """
    Send room assignment for a booking.

    Args:
        booking_id: Booking ID
        revision_id: Revision ID
    """
    print(f"[DEBUG TOOL] post_room_assignment called", file=sys.stderr, flush=True)
    client = get_user_quendoo_client(ctx)
    payload = {"booking_id": booking_id, "revision_id": revision_id}
    return client.post("/Booking/postRoomAssignment", json=payload)


@server.tool()
def post_external_property_data(
    ctx: Context,
    data: dict
) -> dict:
    """
    Send external property mapping data to Quendoo.

    Args:
        data: External property data object
    """
    print(f"[DEBUG TOOL] post_external_property_data called", file=sys.stderr, flush=True)
    client = get_user_quendoo_client(ctx)
    return client.post("/Booking/postExternalPropertyData", json=data)


# Register automation and email tools (these don't need per-user API keys)
register_automation_tools(server, automation_client)
register_email_tools(server, email_client)

# Add OAuth endpoints using custom OAuth server (uses Stytch for auth only)
try:
    from starlette.responses import JSONResponse, RedirectResponse, HTMLResponse
    from starlette.requests import Request
    from oauth_server import OAuthServer

    mcp_server_url = os.getenv("MCP_SERVER_URL", "https://quendoo-mcp-server-880871219885.us-central1.run.app")

    # Initialize OAuth server
    oauth_server = OAuthServer()

    @server.custom_route(path="/.well-known/oauth-authorization-server", methods=["GET"])
    async def oauth_authorization_server_metadata(request: Request):
        """OAuth Authorization Server Metadata (RFC 8414)."""
        return JSONResponse(oauth_server.get_metadata())

    @server.custom_route(path="/.well-known/oauth-protected-resource", methods=["GET"])
    async def protected_resource_metadata_new(request: Request):
        """Protected Resource Metadata endpoint (RFC 9728)."""
        # Ensure URLs end with /
        resource = f"{mcp_server_url}/" if not mcp_server_url.endswith("/") else mcp_server_url
        auth_server = f"{mcp_server_url}/" if not mcp_server_url.endswith("/") else mcp_server_url

        return JSONResponse({
            "resource": resource,
            "authorization_servers": [auth_server],
            "bearer_methods_supported": ["header"],
            "scopes_supported": ["openid", "email", "profile", "quendoo:pms"]
        })

    @server.custom_route(path="/.well-known/jwks.json", methods=["GET"])
    async def jwks_endpoint(request: Request):
        """JWKS endpoint for JWT public key distribution."""
        from tools.jwt_auth import get_jwks
        return JSONResponse(get_jwks())

    @server.custom_route(path="/oauth/authorize", methods=["GET"])
    async def oauth_authorize_endpoint(request: Request):
        """
        OAuth authorization endpoint.

        Shows login page powered by Stytch.
        """
        # Extract OAuth parameters
        client_id = request.query_params.get("client_id")
        redirect_uri = request.query_params.get("redirect_uri")
        state = request.query_params.get("state", "")
        code_challenge = request.query_params.get("code_challenge")
        code_challenge_method = request.query_params.get("code_challenge_method", "S256")
        scope = request.query_params.get("scope", "openid email profile quendoo:pms")

        print(f"[DEBUG] /oauth/authorize: client_id={client_id}, redirect_uri={redirect_uri}", file=sys.stderr, flush=True)

        # Validate required parameters
        if not client_id or not redirect_uri or not code_challenge:
            return JSONResponse(
                {"error": "invalid_request", "error_description": "Missing required parameters"},
                status_code=400
            )

        # Get web app URL for Stytch login
        web_app_url = os.getenv("WEB_APP_URL", "https://quendoo-web-app-880871219885.us-central1.run.app")

        # Build OAuth callback URL (back to this server after Stytch login)
        oauth_callback_params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "scope": scope
        }

        from urllib.parse import urlencode, quote
        oauth_callback_url = f"{mcp_server_url}/oauth/callback?{urlencode(oauth_callback_params)}"

        # Redirect to web app with OAuth callback (URL encode the redirect parameter)
        login_url = f"{web_app_url}/?redirect={quote(oauth_callback_url, safe='')}"

        print(f"[DEBUG] Redirecting to login: {login_url}", file=sys.stderr, flush=True)

        return RedirectResponse(url=login_url)

    @server.custom_route(path="/oauth/callback", methods=["GET"])
    async def oauth_callback_endpoint(request: Request):
        """
        OAuth callback after Stytch authentication.

        Creates authorization code and redirects back to client.
        """
        # Get Stytch session token from query params (set by web app)
        stytch_token = request.query_params.get("stytch_token")

        # Get OAuth parameters
        client_id = request.query_params.get("client_id")
        redirect_uri = request.query_params.get("redirect_uri")
        state = request.query_params.get("state", "")
        code_challenge = request.query_params.get("code_challenge")
        code_challenge_method = request.query_params.get("code_challenge_method", "S256")
        scope = request.query_params.get("scope", "openid email profile quendoo:pms")

        print(f"[DEBUG] /oauth/callback: client_id={client_id}, stytch_token present={bool(stytch_token)}", file=sys.stderr, flush=True)

        if not stytch_token:
            return JSONResponse(
                {"error": "access_denied", "error_description": "No authentication token"},
                status_code=401
            )

        # Validate Stytch token and get user
        from stytch_auth import StytchAuthenticator
        stytch = StytchAuthenticator()
        token_data = stytch.validate_token(stytch_token)

        if not token_data or not token_data.get("is_valid"):
            return JSONResponse(
                {"error": "access_denied", "error_description": "Invalid authentication token"},
                status_code=401
            )

        stytch_user_id = token_data.get("user_id")
        email = token_data.get("email")

        # Get or create user in database
        from tools.database import DatabaseClient
        database_url = os.getenv("DATABASE_URL")
        db = DatabaseClient(database_url)
        user = db.get_user_by_stytch_id(stytch_user_id)
        if not user:
            user_id = db.create_or_update_stytch_user(
                stytch_user_id=stytch_user_id,
                email=email
            )
        else:
            user_id = user["id"]

        print(f"[DEBUG] User authenticated: user_id={user_id}, email={email}", file=sys.stderr, flush=True)

        # Create authorization code
        auth_code = oauth_server.create_authorization_code(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method
        )

        # Redirect back to client with authorization code
        separator = "&" if "?" in redirect_uri else "?"
        final_redirect = f"{redirect_uri}{separator}code={auth_code}&state={state}"

        print(f"[DEBUG] Redirecting to client: {final_redirect[:80]}...", file=sys.stderr, flush=True)

        return RedirectResponse(url=final_redirect)

    @server.custom_route(path="/oauth/token", methods=["POST"])
    async def oauth_token_endpoint(request: Request):
        """
        OAuth token endpoint.

        Exchanges authorization code for access token.
        """
        # Parse form data
        form_data = await request.form()
        form_dict = dict(form_data)

        print(f"[DEBUG] /oauth/token: grant_type={form_dict.get('grant_type')}", file=sys.stderr, flush=True)

        # Exchange code for token
        token_response = oauth_server.exchange_code_for_token(
            code=form_dict.get("code"),
            client_id=form_dict.get("client_id"),
            client_secret=form_dict.get("client_secret"),
            redirect_uri=form_dict.get("redirect_uri"),
            code_verifier=form_dict.get("code_verifier")
        )

        if not token_response:
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "Invalid authorization code or credentials"},
                status_code=400
            )

        return JSONResponse(token_response)

    @server.custom_route(path="/oauth/register", methods=["POST"])
    async def oauth_register_endpoint(request: Request):
        """OAuth Dynamic Client Registration endpoint (RFC 7591)."""
        body = await request.json()

        try:
            response = oauth_server.register_client(
                client_name=body.get("client_name", "Unknown Client"),
                redirect_uris=body.get("redirect_uris", []),
                grant_types=body.get("grant_types"),
                response_types=body.get("response_types"),
                token_endpoint_auth_method=body.get("token_endpoint_auth_method", "none"),
                scope=body.get("scope")
            )
            return JSONResponse(response, status_code=201)
        except Exception as e:
            print(f"[ERROR] Client registration failed: {e}", file=sys.stderr, flush=True)
            return JSONResponse(
                {"error": "invalid_request", "error_description": str(e)},
                status_code=400
            )

    # REST API endpoints for web app
    @server.custom_route(path="/api/users/{user_id}/quendoo-api-key", methods=["POST"])
    async def save_user_api_key(request: Request):
        """Save Quendoo API key for a user (called from web app)."""
        try:
            user_id = request.path_params.get("user_id")
            body = await request.json()
            quendoo_api_key = body.get("quendoo_api_key")

            if not quendoo_api_key:
                return JSONResponse(
                    {"error": "quendoo_api_key is required"},
                    status_code=400
                )

            database_url = os.getenv("DATABASE_URL")
            db = DatabaseClient(database_url)

            # Update user's API key
            success = db.update_user_api_key(int(user_id), quendoo_api_key)

            if success:
                return JSONResponse({"success": True, "message": "API key saved"})
            else:
                return JSONResponse(
                    {"error": "Failed to save API key"},
                    status_code=500
                )
        except Exception as e:
            print(f"[ERROR] Save API key failed: {e}", file=sys.stderr, flush=True)
            return JSONResponse(
                {"error": str(e)},
                status_code=500
            )

    @server.custom_route(path="/api/users/{user_id}/quendoo-api-key", methods=["GET"])
    async def get_user_api_key(request: Request):
        """Get Quendoo API key for a user (called from web app)."""
        try:
            user_id = request.path_params.get("user_id")

            database_url = os.getenv("DATABASE_URL")
            db = DatabaseClient(database_url)
            user = db.get_user_by_id(int(user_id))

            if not user:
                return JSONResponse(
                    {"error": "User not found"},
                    status_code=404
                )

            return JSONResponse({
                "quendoo_api_key": user.get("quendoo_api_key"),
                "has_api_key": bool(user.get("quendoo_api_key"))
            })
        except Exception as e:
            print(f"[ERROR] Get API key failed: {e}", file=sys.stderr, flush=True)
            return JSONResponse(
                {"error": str(e)},
                status_code=500
            )

    print("OAuth endpoints registered via custom_route:", file=sys.stderr, flush=True)
    print("  - /.well-known/oauth-authorization-server", file=sys.stderr, flush=True)
    print("  - /.well-known/oauth-protected-resource", file=sys.stderr, flush=True)
    print("  - /.well-known/jwks.json", file=sys.stderr, flush=True)
    print("  - /oauth/authorize", file=sys.stderr, flush=True)
    print("  - /oauth/callback", file=sys.stderr, flush=True)
    print("  - /oauth/token", file=sys.stderr, flush=True)
    print("  - /oauth/register", file=sys.stderr, flush=True)
    print("  - /api/users/{user_id}/quendoo-api-key (GET, POST)", file=sys.stderr, flush=True)
except Exception as e:
    print(f"Warning: Could not register OAuth endpoints: {e}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)

if __name__ == "__main__":
    print("Quendoo MCP server running locally (Python)", file=sys.stderr)
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    server.run(transport=transport)