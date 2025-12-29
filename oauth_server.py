"""
OAuth 2.1 Authorization Server for Quendoo MCP.

Implements:
- OAuth 2.0 Authorization Server Metadata (RFC 8414)
- OAuth 2.0 Dynamic Client Registration Protocol (RFC 7591)
- Authorization Code Flow with PKCE (RFC 7636)
- Token endpoint for code exchange
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import psycopg2
from psycopg2.extras import RealDictCursor

from tools.database import DatabaseClient
from tools.jwt_auth import create_jwt_token, decode_jwt_token


class OAuthServer:
    """OAuth 2.1 Authorization Server."""

    def __init__(self, database_url: str | None = None):
        self.db = DatabaseClient(database_url)
        self.db_url = database_url or os.getenv("DATABASE_URL")
        self.base_url = os.getenv(
            "OAUTH_BASE_URL",
            "https://quendoo-mcp-server-880871219885.us-central1.run.app"
        )

    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def get_metadata(self) -> dict[str, Any]:
        """
        Get OAuth 2.0 Authorization Server Metadata (RFC 8414).

        Returns metadata for /.well-known/openid-configuration endpoint.
        """
        return {
            "issuer": self.base_url,
            "authorization_endpoint": f"{self.base_url}/oauth/authorize",
            "token_endpoint": f"{self.base_url}/oauth/token",
            "registration_endpoint": f"{self.base_url}/oauth/register",
            "userinfo_endpoint": f"{self.base_url}/oauth/userinfo",
            "jwks_uri": f"{self.base_url}/.well-known/jwks.json",
            "scopes_supported": ["openid", "profile", "email", "quendoo:pms"],
            "response_types_supported": ["code"],
            "response_modes_supported": ["query"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
                "none"
            ],
            "code_challenge_methods_supported": ["S256"],
            "service_documentation": "https://github.com/quendoo/quendoo-mcp",
        }

    def register_client(
        self,
        client_name: str,
        redirect_uris: list[str],
        grant_types: list[str] | None = None,
        response_types: list[str] | None = None,
        token_endpoint_auth_method: str = "client_secret_basic",
        scope: str | None = None
    ) -> dict[str, Any]:
        """
        Register a new OAuth client (RFC 7591).

        Args:
            client_name: Human-readable client name
            redirect_uris: List of allowed redirect URIs
            grant_types: Supported grant types (default: authorization_code)
            response_types: Supported response types (default: code)
            token_endpoint_auth_method: Auth method for token endpoint
            scope: Requested scope

        Returns:
            Client registration response with client_id and client_secret
        """
        # Generate client credentials
        client_id = f"mcp_client_{secrets.token_urlsafe(16)}"
        client_secret = secrets.token_urlsafe(32)

        # Default values
        if grant_types is None:
            grant_types = ["authorization_code", "refresh_token"]
        if response_types is None:
            response_types = ["code"]
        if scope is None:
            scope = "openid profile email quendoo:pms"

        # Determine if this is a public client (no secret required)
        is_public = token_endpoint_auth_method == "none"

        # Store in database
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO oauth_clients (
                        client_id, client_secret, client_name, redirect_uris,
                        grant_types, response_types, scope,
                        token_endpoint_auth_method, is_public
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING client_id, created_at
                    """,
                    (
                        client_id,
                        None if is_public else client_secret,
                        client_name,
                        redirect_uris,
                        grant_types,
                        response_types,
                        scope,
                        token_endpoint_auth_method,
                        is_public
                    )
                )
                result = cur.fetchone()
                conn.commit()

        # Build response per RFC 7591
        response = {
            "client_id": client_id,
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "grant_types": grant_types,
            "response_types": response_types,
            "token_endpoint_auth_method": token_endpoint_auth_method,
            "scope": scope,
            "client_id_issued_at": int(result["created_at"].timestamp())
        }

        # Only include secret for confidential clients
        if not is_public:
            response["client_secret"] = client_secret

        return response

    def get_client(self, client_id: str) -> dict[str, Any] | None:
        """Get OAuth client by ID."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM oauth_clients WHERE client_id = %s",
                    (client_id,)
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def verify_client_credentials(
        self, client_id: str, client_secret: str | None
    ) -> bool:
        """Verify client credentials."""
        client = self.get_client(client_id)
        if not client:
            return False

        # Public clients don't need secret
        if client["is_public"]:
            return True

        # Confidential clients must provide matching secret
        return client["client_secret"] == client_secret

    def create_authorization_code(
        self,
        client_id: str,
        user_id: int,
        redirect_uri: str,
        scope: str,
        code_challenge: str,
        code_challenge_method: str = "S256"
    ) -> str:
        """
        Create an authorization code for OAuth flow.

        Args:
            client_id: OAuth client ID
            user_id: User ID from database
            redirect_uri: Redirect URI from authorization request
            scope: Requested scope
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE method (S256 or plain)

        Returns:
            Authorization code
        """
        # Generate secure authorization code
        code = secrets.token_urlsafe(32)

        # Code expires in 10 minutes per OAuth 2.1 spec
        expires_at = datetime.utcnow() + timedelta(minutes=10)

        # Store in database
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO authorization_codes (
                        code, client_id, user_id, redirect_uri, scope,
                        code_challenge, code_challenge_method, expires_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        code, client_id, user_id, redirect_uri, scope,
                        code_challenge, code_challenge_method, expires_at
                    )
                )
                conn.commit()

        return code

    def verify_code_challenge(
        self, code_verifier: str, code_challenge: str, method: str = "S256"
    ) -> bool:
        """
        Verify PKCE code challenge.

        Args:
            code_verifier: Code verifier from token request
            code_challenge: Code challenge from authorization request
            method: Challenge method (S256 or plain)

        Returns:
            True if verification succeeds
        """
        if method == "S256":
            # SHA256 hash and base64url encode
            verifier_hash = hashlib.sha256(code_verifier.encode()).digest()
            import base64
            computed_challenge = (
                base64.urlsafe_b64encode(verifier_hash)
                .decode()
                .rstrip("=")
            )
            return computed_challenge == code_challenge
        elif method == "plain":
            return code_verifier == code_challenge
        else:
            return False

    def exchange_code_for_token(
        self,
        code: str,
        client_id: str,
        client_secret: str | None,
        redirect_uri: str,
        code_verifier: str
    ) -> dict[str, Any] | None:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code
            client_id: OAuth client ID
            client_secret: OAuth client secret (if confidential client)
            redirect_uri: Redirect URI (must match authorization request)
            code_verifier: PKCE code verifier

        Returns:
            Token response or None if invalid
        """
        # Verify client credentials
        if not self.verify_client_credentials(client_id, client_secret):
            return None

        # Retrieve authorization code from database
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM authorization_codes
                    WHERE code = %s AND client_id = %s AND used = false
                    """,
                    (code, client_id)
                )
                auth_code = cur.fetchone()

                if not auth_code:
                    return None

                # Check if code expired
                if datetime.utcnow() > auth_code["expires_at"]:
                    return None

                # Verify redirect URI matches
                if auth_code["redirect_uri"] != redirect_uri:
                    return None

                # Verify PKCE code challenge
                if not self.verify_code_challenge(
                    code_verifier,
                    auth_code["code_challenge"],
                    auth_code["code_challenge_method"]
                ):
                    return None

                # Mark code as used
                cur.execute(
                    "UPDATE authorization_codes SET used = true WHERE code = %s",
                    (code,)
                )
                conn.commit()

        # Get user information
        user = self.db.get_user_by_id(auth_code["user_id"])
        if not user:
            return None

        # Create JWT access token (30 days expiry)
        access_token = create_jwt_token(user["id"], user["email"])

        # Store token in database for tracking
        expires_at = datetime.utcnow() + timedelta(days=30)
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO access_tokens (
                        token, client_id, user_id, scope, expires_at
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        access_token,
                        client_id,
                        user["id"],
                        auth_code["scope"],
                        expires_at
                    )
                )
                conn.commit()

        # Return token response per OAuth 2.1
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 30 * 24 * 60 * 60,  # 30 days in seconds
            "scope": auth_code["scope"]
        }

    def get_user_info(self, access_token: str) -> dict[str, Any] | None:
        """
        Get user information from access token.

        Args:
            access_token: JWT access token

        Returns:
            User info or None if invalid token
        """
        # Decode JWT token
        payload = decode_jwt_token(access_token)
        if not payload:
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        # Get user from database
        user = self.db.get_user_by_id(user_id)
        if not user:
            return None

        # Return standard OpenID Connect user info
        return {
            "sub": str(user["id"]),
            "email": user["email"],
            "email_verified": True,
            "quendoo_api_key_configured": bool(user.get("quendoo_api_key")),
            "email_api_key_configured": bool(user.get("email_api_key"))
        }
