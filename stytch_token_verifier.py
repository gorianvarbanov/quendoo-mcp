"""Stytch JWT Token Verifier for FastMCP."""
import os
import sys
from typing import Optional

import jwt
from jwt import PyJWKClient
from mcp.server.auth.provider import AccessToken, TokenVerifier


class StytchTokenVerifier(TokenVerifier):
    """Verify JWT tokens from Stytch OAuth provider."""

    def __init__(self, jwks_url: str, issuer: str, audience: str, required_scopes: list[str] | None = None):
        """
        Initialize Stytch token verifier.

        Args:
            jwks_url: JWKS endpoint URL (e.g., https://example.stytch.com/.well-known/jwks.json)
            issuer: Expected issuer (e.g., stytch.com/project-live-xxx)
            audience: Expected audience (project ID)
            required_scopes: List of required OAuth scopes
        """
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.audience = audience
        self.required_scopes = required_scopes or []
        self.jwks_client = PyJWKClient(jwks_url)
        print(f"[STYTCH VERIFIER] Initialized with JWKS: {jwks_url}", file=sys.stderr, flush=True)
        print(f"[STYTCH VERIFIER] Issuer: {issuer}", file=sys.stderr, flush=True)
        print(f"[STYTCH VERIFIER] Audience: {audience}", file=sys.stderr, flush=True)
        print(f"[STYTCH VERIFIER] Required scopes: {self.required_scopes}", file=sys.stderr, flush=True)

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        """
        Verify JWT token from either Stytch or our custom OAuth server.

        Args:
            token: JWT token string from Authorization header

        Returns:
            AccessToken with user info if valid, None otherwise
        """
        try:
            print(f"[TOKEN VERIFIER] Verifying token...", file=sys.stderr, flush=True)

            # First, try to decode without verification to check the issuer
            unverified = jwt.decode(token, options={"verify_signature": False})
            token_issuer = unverified.get("iss", "")
            print(f"[TOKEN VERIFIER] Token issuer: {token_issuer}", file=sys.stderr, flush=True)

            # Check if this is from our OAuth server or from Stytch
            if "quendoo-mcp-server" in token_issuer:
                # This is from our custom OAuth server - use local JWKS
                print(f"[TOKEN VERIFIER] Using custom OAuth server verification", file=sys.stderr, flush=True)
                from tools.jwt_auth import PUBLIC_KEY

                # Decode and validate with our RSA public key
                decoded = jwt.decode(
                    token,
                    PUBLIC_KEY,
                    algorithms=["RS256"],
                    options={"verify_exp": True, "verify_aud": False}  # Our tokens don't have aud
                )

                # Extract user info
                user_id = str(decoded.get("user_id") or decoded.get("sub", ""))

                print(f"[TOKEN VERIFIER] Custom JWT validated for user: {user_id}", file=sys.stderr, flush=True)

                return AccessToken(
                    token=token,
                    client_id=user_id,
                    scopes=["openid", "email", "profile", "quendoo:pms"],
                    expires_at=decoded.get("exp"),
                )

            else:
                # This is from Stytch - use Stytch JWKS
                print(f"[TOKEN VERIFIER] Using Stytch verification", file=sys.stderr, flush=True)
                signing_key = self.jwks_client.get_signing_key_from_jwt(token)

                # Decode and validate JWT
                decoded = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    audience=self.audience,
                    issuer=self.issuer,
                    options={"verify_exp": True}
                )

                print(f"[TOKEN VERIFIER] Stytch JWT validated for user: {decoded.get('sub')}", file=sys.stderr, flush=True)

                # Return AccessToken with scopes from JWT
                return AccessToken(
                    token=token,
                    client_id=decoded.get("sub", ""),
                    scopes=decoded.get("scope", "").split() if decoded.get("scope") else [],
                    expires_at=decoded.get("exp"),
                )

        except jwt.ExpiredSignatureError:
            print(f"[TOKEN VERIFIER] JWT token expired", file=sys.stderr, flush=True)
            return None
        except jwt.InvalidTokenError as e:
            print(f"[TOKEN VERIFIER] JWT validation failed: {e}", file=sys.stderr, flush=True)
            return None
        except Exception as e:
            print(f"[TOKEN VERIFIER] Token verification error: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return None
