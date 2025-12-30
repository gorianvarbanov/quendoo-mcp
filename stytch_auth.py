"""
Stytch OAuth authentication for MCP server.
"""

import os
import sys
from typing import Any

import stytch
from stytch.core.response_base import StytchError


class StytchAuthenticator:
    """Handle Stytch OAuth authentication for MCP server."""

    def __init__(self):
        """Initialize Stytch client."""
        self.project_id = os.getenv("STYTCH_PROJECT_ID")
        self.secret = os.getenv("STYTCH_SECRET")
        self.project_domain = os.getenv("STYTCH_PROJECT_DOMAIN")

        if not all([self.project_id, self.secret, self.project_domain]):
            raise ValueError(
                "Missing Stytch credentials. Please set STYTCH_PROJECT_ID, "
                "STYTCH_SECRET, and STYTCH_PROJECT_DOMAIN environment variables."
            )

        # Initialize Stytch client
        # Auto-detect environment from project_id
        environment = "test" if self.project_id.startswith("project-test-") else "live"
        print(f"[DEBUG] Initializing Stytch client with environment: {environment}", file=sys.stderr, flush=True)

        self.client = stytch.Client(
            project_id=self.project_id,
            secret=self.secret,
            environment=environment
        )

    def validate_token(self, token: str) -> dict[str, Any] | None:
        """
        Validate Stytch JWT access token (OAuth flow).

        Args:
            token: JWT access token from Authorization header

        Returns:
            Token data including user_id or None if invalid
        """
        try:
            print(f"[DEBUG] Validating JWT token (first 20 chars): {token[:20]}...", file=sys.stderr, flush=True)

            # Try OAuth JWT validation first (for Claude Desktop OAuth flow)
            try:
                import jwt
                import requests
                from jwt import PyJWKClient

                # Fetch JWKS from Stytch
                jwks_url = f"{self.project_domain}/.well-known/jwks.json"
                print(f"[DEBUG] Fetching JWKS from: {jwks_url}", file=sys.stderr, flush=True)

                jwks_client = PyJWKClient(jwks_url)
                signing_key = jwks_client.get_signing_key_from_jwt(token)

                # Verify JWT token
                decoded = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    audience=self.project_id,
                    issuer=f"stytch.com/{self.project_id}",
                    options={"verify_exp": True}
                )

                print(f"[DEBUG] JWT validated successfully for user: {decoded.get('sub')}", file=sys.stderr, flush=True)

                # Extract user info from JWT claims
                return {
                    "user_id": decoded.get("sub"),  # subject claim contains user_id
                    "email": decoded.get("email"),
                    "is_valid": True
                }

            except Exception as jwks_error:
                # Catch PyJWKClientError (wrong key ID) or any JWT validation error
                print(f"[DEBUG] JWT/JWKS validation failed: {type(jwks_error).__name__}: {jwks_error}", file=sys.stderr, flush=True)

                # If this is an old token with wrong kid, return None (unauthorized)
                if "signing key" in str(jwks_error).lower() or "kid" in str(jwks_error).lower():
                    print(f"[DEBUG] Old token with wrong key ID - rejecting", file=sys.stderr, flush=True)
                    return None

                print(f"[DEBUG] JWT validation failed: {jwks_error}, trying session token...", file=sys.stderr, flush=True)

                # Fallback: Try session token validation (for web app)
                response = self.client.sessions.authenticate(session_token=token)

                print(f"[DEBUG] Stytch session response status: {response.status_code}", file=sys.stderr, flush=True)
                if response.status_code == 200:
                    print(f"[DEBUG] Session token valid for user: {response.user.user_id}", file=sys.stderr, flush=True)
                    return {
                        "user_id": response.user.user_id,
                        "email": response.user.emails[0].email if response.user.emails else None,
                        "is_valid": True
                    }
                return None

        except StytchError as e:
            print(f"[ERROR] Stytch token validation error: {e}", file=sys.stderr, flush=True)
            print(f"[ERROR] Error type: {type(e).__name__}", file=sys.stderr, flush=True)
            print(f"[ERROR] Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details'}", file=sys.stderr, flush=True)
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error validating token: {e}", file=sys.stderr, flush=True)
            print(f"[ERROR] Error type: {type(e).__name__}", file=sys.stderr, flush=True)
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}", file=sys.stderr, flush=True)
            return None

    def get_protected_resource_metadata(self, resource_url: str) -> dict[str, Any]:
        """
        Get Protected Resource Metadata for OAuth discovery.

        Args:
            resource_url: Your MCP server's HTTPS URL

        Returns:
            PRM document as dict
        """
        # Ensure resource URL ends with /
        if not resource_url.endswith("/"):
            resource_url = f"{resource_url}/"

        # Ensure authorization server domain ends with /
        auth_server = self.project_domain
        if not auth_server.endswith("/"):
            auth_server = f"{auth_server}/"

        return {
            "resource": resource_url,
            "authorization_servers": [auth_server],
            "bearer_methods_supported": ["header"],
            "scopes_supported": ["openid", "email", "profile", "quendoo:pms"]
        }

    def create_www_authenticate_header(self, realm: str = "Quendoo MCP Server") -> str:
        """
        Create WWW-Authenticate header for 401 responses.

        Args:
            realm: Authentication realm name

        Returns:
            WWW-Authenticate header value
        """
        prm_url = f"{os.getenv('MCP_SERVER_URL')}/.well-known/oauth-protected-resource"
        return f'Bearer realm="{realm}", as_uri="{prm_url}"'
