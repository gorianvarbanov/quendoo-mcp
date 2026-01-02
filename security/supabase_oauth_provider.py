"""
Custom OAuth Authorization Server Provider for FastMCP with Supabase Auth backend.

Implements OAuthAuthorizationServerProvider protocol to provide:
- Login form at /authorize
- Token exchange at /token
- Supabase email/password authentication
"""
import os
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

import requests
from fastapi import Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from mcp.server.auth.oauth import OAuthAuthorizationServerProvider
from dotenv import load_dotenv

load_dotenv()


@dataclass
class SupabaseOAuthProvider(OAuthAuthorizationServerProvider):
    """
    OAuth Authorization Server that authenticates users via Supabase Auth.

    Provides full OAuth 2.1 flow with email/password login.
    """

    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", "https://tjrtbhemajqwzzdzyjtc.supabase.co"))
    supabase_anon_key: str = field(default_factory=lambda: os.getenv("SUPABASE_ANON_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("BASE_URL", "https://quendoo-mcp-multitenant-851052272168.us-central1.run.app"))

    # In-memory storage for authorization codes
    _auth_codes: Dict[str, Dict[str, Any]] = field(default_factory=dict, init=False, repr=False)

    def _cleanup_expired_codes(self):
        """Remove expired authorization codes"""
        now = datetime.utcnow()
        expired = [code for code, data in self._auth_codes.items() if now > data["expires_at"]]
        for code in expired:
            del self._auth_codes[code]

    async def authorize(self, request: Request) -> HTMLResponse | RedirectResponse:
        """
        Handle GET /authorize - show login form or process authentication.
        """
        if request.method == "GET":
            return await self._show_login_form(request)
        else:
            return await self._handle_login(request)

    async def _show_login_form(self, request: Request) -> HTMLResponse:
        """Show login form"""
        params = dict(request.query_params)

        # Validate required parameters
        if params.get("response_type") != "code":
            return HTMLResponse("<h1>Error: Invalid response_type</h1>", status_code=400)

        if not params.get("redirect_uri"):
            return HTMLResponse("<h1>Error: Missing redirect_uri</h1>", status_code=400)

        # Build query string for form POST
        from urllib.parse import urlencode
        params_encoded = urlencode(params)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Quendoo MCP - Login</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .login-container {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    width: 100%;
                    max-width: 400px;
                }}
                h1 {{
                    margin: 0 0 10px 0;
                    font-size: 24px;
                    color: #333;
                }}
                .subtitle {{
                    color: #666;
                    margin-bottom: 30px;
                    font-size: 14px;
                }}
                .form-group {{
                    margin-bottom: 20px;
                }}
                label {{
                    display: block;
                    margin-bottom: 5px;
                    color: #333;
                    font-weight: 500;
                }}
                input[type="email"],
                input[type="password"] {{
                    width: 100%;
                    padding: 12px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    font-size: 14px;
                    box-sizing: border-box;
                }}
                input:focus {{
                    outline: none;
                    border-color: #667eea;
                }}
                button {{
                    width: 100%;
                    padding: 12px;
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                }}
                button:hover {{
                    background: #5568d3;
                }}
                .test-users {{
                    margin-top: 20px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="login-container">
                <h1>🔐 Quendoo MCP</h1>
                <div class="subtitle">Property Management System</div>

                <form method="POST" action="/authorize?{params_encoded}">
                    <div class="form-group">
                        <label for="email">Email</label>
                        <input type="email" id="email" name="email" required autofocus>
                    </div>

                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required>
                    </div>

                    <button type="submit">Sign In</button>
                </form>

                <div class="test-users">
                    <strong>Test Accounts:</strong><br>
                    test@example.com / Test123456!<br>
                    demo@quendoo.com / Demo123456!
                </div>
            </div>
        </body>
        </html>
        """

        return HTMLResponse(html)

    async def _handle_login(self, request: Request) -> RedirectResponse | HTMLResponse:
        """Handle login form submission"""
        form_data = await request.form()
        email = form_data.get("email")
        password = form_data.get("password")

        params = dict(request.query_params)
        redirect_uri = params.get("redirect_uri")
        state = params.get("state")
        code_challenge = params.get("code_challenge")

        # Authenticate with Supabase Auth
        try:
            auth_response = requests.post(
                f"{self.supabase_url}/auth/v1/token?grant_type=password",
                json={"email": email, "password": password},
                headers={
                    "apikey": self.supabase_anon_key,
                    "Content-Type": "application/json"
                },
                timeout=10
            )

            if auth_response.status_code != 200:
                error_msg = auth_response.json().get("error_description", "Invalid credentials")
                return HTMLResponse(f"<h1>Login Failed</h1><p>{error_msg}</p>", status_code=401)

            # Login successful
            auth_data = auth_response.json()
            user = auth_data["user"]
            access_token = auth_data["access_token"]

            # Generate authorization code
            code = secrets.token_urlsafe(32)

            # Store code with user data
            self._cleanup_expired_codes()
            self._auth_codes[code] = {
                "user_id": user["id"],
                "email": user["email"],
                "access_token": access_token,
                "code_challenge": code_challenge,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(minutes=5),
            }

            # Redirect back to client with code
            from urllib.parse import urlencode
            redirect_params = {"code": code}
            if state:
                redirect_params["state"] = state

            redirect_url = f"{redirect_uri}?{urlencode(redirect_params)}"
            return RedirectResponse(redirect_url, status_code=302)

        except Exception as e:
            return HTMLResponse(f"<h1>Authentication Error</h1><p>{str(e)}</p>", status_code=500)

    async def token(self, request: Request) -> Dict[str, Any]:
        """
        Handle POST /token - exchange authorization code for access token.
        """
        form_data = await request.form()
        grant_type = form_data.get("grant_type")
        code = form_data.get("code")
        code_verifier = form_data.get("code_verifier")

        if grant_type != "authorization_code":
            raise HTTPException(400, "Unsupported grant_type")

        # Lookup authorization code
        code_data = self._auth_codes.get(code)
        if not code_data:
            raise HTTPException(400, "Invalid or expired authorization code")

        # Check expiration
        if datetime.utcnow() > code_data["expires_at"]:
            del self._auth_codes[code]
            raise HTTPException(400, "Authorization code expired")

        # Verify PKCE if challenge was provided
        if code_data.get("code_challenge"):
            if not code_verifier:
                raise HTTPException(400, "code_verifier required")

            challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip("=")

            if challenge != code_data["code_challenge"]:
                raise HTTPException(400, "Invalid code_verifier")

        # Return access token (Supabase JWT)
        access_token = code_data["access_token"]

        # Delete used code (one-time use)
        del self._auth_codes[code]

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
        }

    def get_metadata(self) -> Dict[str, Any]:
        """OAuth 2.0 Authorization Server Metadata"""
        return {
            "issuer": self.base_url,
            "authorization_endpoint": f"{self.base_url}/authorize",
            "token_endpoint": f"{self.base_url}/token",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "token_endpoint_auth_methods_supported": ["none"],
            "code_challenge_methods_supported": ["S256"],
        }
