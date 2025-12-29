"""
Flask server with Stytch OAuth endpoints for MCP.

Provides:
- Protected Resource Metadata (/.well-known/oauth-protected-resource)
- Token validation middleware
- Integration with MCP server
"""

import os
from functools import wraps

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from stytch_auth import StytchAuthenticator
from tools.database import DatabaseClient

# Serve React static files if they exist
static_folder = os.path.join(os.path.dirname(__file__), 'static')
if os.path.exists(static_folder):
    app = Flask(__name__, static_folder=static_folder, static_url_path='')
else:
    app = Flask(__name__)

CORS(app)

# Initialize database client
database_url = os.getenv("DATABASE_URL")
if database_url:
    try:
        db_client = DatabaseClient(database_url)
        DB_ENABLED = True
    except Exception as e:
        print(f"Warning: Database not configured - {e}")
        DB_ENABLED = False
else:
    DB_ENABLED = False

# Initialize Stytch authenticator
try:
    stytch_auth = StytchAuthenticator()
    STYTCH_ENABLED = True
except ValueError as e:
    print(f"Warning: Stytch not configured - {e}")
    STYTCH_ENABLED = False


def require_stytch_auth(f):
    """Decorator to require Stytch authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not STYTCH_ENABLED:
            return jsonify({"error": "Stytch authentication not configured"}), 500

        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            www_authenticate = stytch_auth.create_www_authenticate_header()
            return jsonify({"error": "Unauthorized"}), 401, {
                "WWW-Authenticate": www_authenticate
            }

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Validate token
        token_data = stytch_auth.validate_token(token)
        if not token_data:
            www_authenticate = stytch_auth.create_www_authenticate_header()
            return jsonify({"error": "Invalid or expired token"}), 401, {
                "WWW-Authenticate": www_authenticate
            }

        # Attach token data to request
        request.stytch_user = token_data
        return f(*args, **kwargs)

    return decorated_function


@app.route("/.well-known/oauth-protected-resource", methods=["GET"])
def protected_resource_metadata():
    """
    Protected Resource Metadata endpoint (RFC 9728).

    This tells MCP clients where to find the OAuth authorization server.
    """
    if not STYTCH_ENABLED:
        return jsonify({"error": "Stytch not configured"}), 500

    mcp_server_url = os.getenv(
        "MCP_SERVER_URL",
        "https://quendoo-mcp-server-880871219885.us-central1.run.app"
    )

    metadata = stytch_auth.get_protected_resource_metadata(mcp_server_url)
    return jsonify(metadata)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "stytch_enabled": STYTCH_ENABLED,
        "mcp_version": "1.0.0"
    })


@app.route("/auth/test", methods=["GET"])
@require_stytch_auth
def test_auth():
    """Test endpoint to verify Stytch authentication."""
    return jsonify({
        "message": "Authentication successful!",
        "user": request.stytch_user
    })


@app.route("/api/user/api-key", methods=["GET"])
@require_stytch_auth
def get_api_key():
    """Get user's Quendoo API key."""
    if not DB_ENABLED:
        return jsonify({"error": "Database not configured"}), 500

    stytch_user_id = request.stytch_user.get("user_id")
    email = request.stytch_user.get("email")

    if not stytch_user_id:
        return jsonify({"error": "Invalid user"}), 400

    # Get or create user
    user = db_client.get_user_by_stytch_id(stytch_user_id)
    if not user:
        # Create new user
        user_id = db_client.create_or_update_stytch_user(
            stytch_user_id=stytch_user_id,
            email=email
        )
        return jsonify({
            "email": email,
            "quendoo_api_key": None
        })

    return jsonify({
        "email": user.get("email"),
        "quendoo_api_key": user.get("quendoo_api_key")
    })


@app.route("/api/user/api-key", methods=["POST"])
@require_stytch_auth
def update_api_key():
    """Update user's Quendoo API key."""
    if not DB_ENABLED:
        return jsonify({"error": "Database not configured"}), 500

    stytch_user_id = request.stytch_user.get("user_id")
    email = request.stytch_user.get("email")

    data = request.get_json()
    quendoo_api_key = data.get("quendoo_api_key")

    if not quendoo_api_key:
        return jsonify({"error": "quendoo_api_key is required"}), 400

    if not stytch_user_id:
        return jsonify({"error": "Invalid user"}), 400

    try:
        # Get or create user
        user = db_client.get_user_by_stytch_id(stytch_user_id)

        if user:
            # Update existing user
            db_client.update_api_keys(user["id"], quendoo_api_key=quendoo_api_key)
        else:
            # Create new user with API key
            db_client.create_or_update_stytch_user(
                stytch_user_id=stytch_user_id,
                email=email,
                quendoo_api_key=quendoo_api_key
            )

        return jsonify({
            "message": "API key updated successfully",
            "email": email
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    """Serve React app for all non-API routes."""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
