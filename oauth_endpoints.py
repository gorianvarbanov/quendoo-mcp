"""
Flask endpoints for OAuth 2.1 Authorization Server.

Provides HTTP endpoints for:
- /.well-known/openid-configuration (metadata discovery)
- /oauth/register (dynamic client registration)
- /oauth/authorize (authorization endpoint with user consent)
- /oauth/token (token endpoint)
- /oauth/userinfo (user info endpoint)
"""

import os
from urllib.parse import urlencode, urlparse

from flask import Flask, jsonify, redirect, render_template, request, session
from flask_cors import CORS

from oauth_server import OAuthServer
from tools.database import DatabaseClient
from tools.jwt_auth import decode_jwt_token


def create_oauth_app() -> Flask:
    """Create Flask app with OAuth endpoints."""
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "CHANGE_THIS_IN_PRODUCTION")
    CORS(app)

    oauth = OAuthServer()
    db = DatabaseClient()

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
                return jsonify({"error": "invalid_client_metadata", "error_description": "client_name is required"}), 400

            if not redirect_uris:
                return jsonify({"error": "invalid_redirect_uri", "error_description": "redirect_uris is required"}), 400

            # Optional fields
            grant_types = data.get("grant_types", ["authorization_code", "refresh_token"])
            response_types = data.get("response_types", ["code"])
            token_endpoint_auth_method = data.get("token_endpoint_auth_method", "client_secret_basic")
            scope = data.get("scope", "openid profile email quendoo:pms")

            # Register client
            client_info = oauth.register_client(
                client_name=client_name,
                redirect_uris=redirect_uris,
                grant_types=grant_types,
                response_types=response_types,
                token_endpoint_auth_method=token_endpoint_auth_method,
                scope=scope
            )

            return jsonify(client_info), 201

        except Exception as e:
            return jsonify({"error": "server_error", "error_description": str(e)}), 500

    @app.route("/oauth/authorize", methods=["GET", "POST"])
    def authorize():
        """
        Authorization endpoint with user consent.

        GET: Show login/consent page
        POST: Process user authorization decision
        """
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
                return jsonify({
                    "error": "invalid_request",
                    "error_description": "Missing required parameters: client_id, redirect_uri, code_challenge"
                }), 400

            # Verify client exists
            client = oauth.get_client(client_id)
            if not client:
                return jsonify({
                    "error": "invalid_client",
                    "error_description": "Unknown client_id"
                }), 400

            # Verify redirect_uri is registered
            if redirect_uri not in client["redirect_uris"]:
                return jsonify({
                    "error": "invalid_request",
                    "error_description": "redirect_uri not registered for this client"
                }), 400

            # Store OAuth params in session
            session["oauth_request"] = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": response_type,
                "scope": scope,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "client_name": client["client_name"]
            }

            # Show authorization/login page
            return render_template(
                "authorize.html",
                client_name=client["client_name"],
                scope=scope
            )

        elif request.method == "POST":
            # Get OAuth request from session
            oauth_request = session.get("oauth_request")
            if not oauth_request:
                return jsonify({
                    "error": "invalid_request",
                    "error_description": "No active authorization request"
                }), 400

            # Get login credentials or existing JWT token
            email = request.form.get("email")
            password = request.form.get("password")
            jwt_token = request.form.get("jwt_token")
            action = request.form.get("action")

            # Check if user denied authorization
            if action == "deny":
                error_params = {
                    "error": "access_denied",
                    "error_description": "User denied authorization"
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
                    error="Invalid credentials or token"
                )

            # Create authorization code
            code = oauth.create_authorization_code(
                client_id=oauth_request["client_id"],
                user_id=user["id"],
                redirect_uri=oauth_request["redirect_uri"],
                scope=oauth_request["scope"],
                code_challenge=oauth_request["code_challenge"],
                code_challenge_method=oauth_request["code_challenge_method"]
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
                return jsonify({
                    "error": "unsupported_grant_type",
                    "error_description": "Only authorization_code grant type is supported"
                }), 400

            # Validate required parameters
            if not all([code, redirect_uri, client_id, code_verifier]):
                return jsonify({
                    "error": "invalid_request",
                    "error_description": "Missing required parameters"
                }), 400

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
                code_verifier=code_verifier
            )

            if not token_response:
                return jsonify({
                    "error": "invalid_grant",
                    "error_description": "Invalid authorization code or verification failed"
                }), 400

            return jsonify(token_response)

        except Exception as e:
            return jsonify({
                "error": "server_error",
                "error_description": str(e)
            }), 500

    @app.route("/oauth/userinfo", methods=["GET"])
    def userinfo():
        """User info endpoint."""
        # Get access token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({
                "error": "invalid_token",
                "error_description": "Missing or invalid Authorization header"
            }), 401

        access_token = auth_header[7:]  # Remove "Bearer " prefix

        # Get user info
        user_info = oauth.get_user_info(access_token)
        if not user_info:
            return jsonify({
                "error": "invalid_token",
                "error_description": "Invalid or expired access token"
            }), 401

        return jsonify(user_info)

    return app


if __name__ == "__main__":
    app = create_oauth_app()
    port = int(os.getenv("AUTH_PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
