"""
Custom OAuth 2.1 Authorization Server for FastMCP with Supabase Auth backend.

Provides:
- /authorize endpoint with login form
- /token endpoint for code exchange
- /.well-known/oauth-authorization-server metadata
- Issues JWT tokens signed with our own key
"""
import os
import secrets
import hashlib
import base64
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs, urlparse

import requests
import jwt
from fastapi import FastAPI, Request, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
BASE_URL = os.getenv("BASE_URL", "https://quendoo-mcp-multitenant-851052272168.us-central1.run.app")

# In-memory storage for authorization codes (5 min TTL)
auth_codes: Dict[str, Dict[str, Any]] = {}


def cleanup_expired_codes():
    """Remove expired authorization codes"""
    now = datetime.utcnow()
    expired = [code for code, data in auth_codes.items() if now > data["expires_at"]]
    for code in expired:
        del auth_codes[code]


@app.get("/.well-known/oauth-authorization-server")
async def oauth_metadata():
    """OAuth 2.0 Authorization Server Metadata"""
    return {
        "issuer": BASE_URL,  # OAuth server is the issuer
        "authorization_endpoint": f"{BASE_URL}/authorize",
        "token_endpoint": f"{BASE_URL}/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "token_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["S256"],
    }


@app.get("/authorize", response_class=HTMLResponse)
async def authorize(request: Request):
    """
    OAuth authorization endpoint - shows login form.

    Query params:
    - response_type: must be "code"
    - client_id: client identifier
    - redirect_uri: where to redirect after login
    - state: client state
    - code_challenge: PKCE challenge
    - code_challenge_method: PKCE method (S256)
    """
    params = dict(request.query_params)

    # Validate required parameters
    if params.get("response_type") != "code":
        return HTMLResponse("<h1>Error: Invalid response_type</h1>", status_code=400)

    if not params.get("redirect_uri"):
        return HTMLResponse("<h1>Error: Missing redirect_uri</h1>", status_code=400)

    # Store params in form for POST
    params_encoded = urlencode(params)

    # Return login form
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
            input[type="email"]:focus,
            input[type="password"]:focus {{
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
                transition: background 0.3s;
            }}
            button:hover {{
                background: #5568d3;
            }}
            .error {{
                background: #fee;
                border: 1px solid #fcc;
                color: #c33;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 20px;
                font-size: 14px;
            }}
            .test-users {{
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                font-size: 12px;
                color: #666;
            }}
            .test-users strong {{
                display: block;
                margin-bottom: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <h1>🔐 Quendoo MCP</h1>
            <div class="subtitle">Multi-Tenant Property Management System</div>

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
                <strong>Test Accounts:</strong>
                test@example.com / Test123456!<br>
                demo@quendoo.com / Demo123456!
            </div>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(html)


@app.post("/authorize")
async def authorize_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    """
    Handle login form submission.
    Validates credentials with Supabase Auth and returns authorization code.
    """
    params = dict(request.query_params)
    redirect_uri = params.get("redirect_uri")
    state = params.get("state")
    code_challenge = params.get("code_challenge")

    # Authenticate with Supabase Auth
    auth_response = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        json={"email": email, "password": password},
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        }
    )

    if auth_response.status_code != 200:
        # Login failed - show error
        error_msg = auth_response.json().get("error_description", "Invalid credentials")
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Login Error</title></head>
        <body>
            <div class="error">
                <h2>Login Failed</h2>
                <p>{error_msg}</p>
                <a href="/authorize?{urlencode(params)}">Try Again</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(html, status_code=401)

    # Login successful - get user data
    auth_data = auth_response.json()
    user = auth_data["user"]

    # Generate authorization code
    code = secrets.token_urlsafe(32)

    # Store code with user data and PKCE challenge
    cleanup_expired_codes()
    auth_codes[code] = {
        "user_id": user["id"],
        "email": user["email"],
        "user_metadata": user.get("user_metadata", {}),
        "code_challenge": code_challenge,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=5),
    }

    # Redirect back to client with code
    redirect_params = {"code": code}
    if state:
        redirect_params["state"] = state

    redirect_url = f"{redirect_uri}?{urlencode(redirect_params)}"
    return RedirectResponse(redirect_url)


@app.post("/token")
async def token_exchange(
    request: Request,
    grant_type: str = Form(...),
    code: str = Form(...),
    redirect_uri: str = Form(...),
    code_verifier: str = Form(None)
):
    """
    Token endpoint - exchange authorization code for access token.
    """
    if grant_type != "authorization_code":
        raise HTTPException(400, "Unsupported grant_type")

    # Lookup authorization code
    code_data = auth_codes.get(code)
    if not code_data:
        raise HTTPException(400, "Invalid or expired authorization code")

    # Check expiration
    if datetime.utcnow() > code_data["expires_at"]:
        del auth_codes[code]
        raise HTTPException(400, "Authorization code expired")

    # Verify PKCE if challenge was provided
    if code_data.get("code_challenge"):
        if not code_verifier:
            raise HTTPException(400, "code_verifier required")

        # Compute challenge from verifier
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")

        if challenge != code_data["code_challenge"]:
            raise HTTPException(400, "Invalid code_verifier")

    # Generate our own JWT token
    user_id = code_data["user_id"]
    email = code_data["email"]

    # Create JWT payload
    payload = {
        "sub": user_id,  # Subject (user ID)
        "email": email,
        "iss": BASE_URL,  # Issuer (OAuth server)
        "aud": BASE_URL,  # Audience
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=30),
        "jti": str(uuid.uuid4()),
    }

    # Sign token with Supabase JWT secret (HMAC HS256)
    access_token = jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")

    # Delete used code (one-time use)
    del auth_codes[code]

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 2592000,  # 30 days
    }


@app.get("/")
async def root():
    """Health check"""
    return {"status": "ok", "service": "Quendoo MCP OAuth Server"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
