"""
Production MCP Server with FastAPI wrapper for proper HTTP authentication.
Handles multi-tenant authentication at the HTTP boundary before passing to FastMCP.
"""
import os
import sys
import json
import asyncio
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from uuid import UUID, uuid4
from typing import Dict, Optional
import httpx

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import load_dotenv

from security.auth import auth_manager
from database.connection import get_db_session
from database.models import Tenant, User, DeviceSession, DeviceCode
from api_key_manager_v2 import mt_key_manager
import random
import string

load_dotenv()

# ========================================
# GLOBAL TENANT CONTEXT
# ========================================

# Thread-safe storage for current request's tenant_id
_tenant_context: Dict[int, UUID] = {}

def set_current_tenant(tenant_id: UUID):
    """Set the current tenant for this request"""
    import threading
    thread_id = threading.get_ident()
    _tenant_context[thread_id] = tenant_id
    print(f"[DEBUG] Set tenant {tenant_id} for thread {thread_id}", file=sys.stderr, flush=True)

def get_current_tenant() -> Optional[UUID]:
    """Get the current tenant for this request"""
    import threading
    thread_id = threading.get_ident()
    tenant_id = _tenant_context.get(thread_id)
    print(f"[DEBUG] Get tenant for thread {thread_id}: {tenant_id}", file=sys.stderr, flush=True)
    return tenant_id

def clear_current_tenant():
    """Clear the current tenant"""
    import threading
    thread_id = threading.get_ident()
    if thread_id in _tenant_context:
        del _tenant_context[thread_id]

# ========================================
# DEVICE CODE HELPERS
# ========================================

def generate_user_code(length=8):
    """Generate human-readable device code like ABCD-1234"""
    chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choices(chars, k=length))
    # Format as XXXX-XXXX for readability
    return f"{code[:4]}-{code[4:]}"

def generate_device_code():
    """Generate internal device code (UUID-like)"""
    return str(uuid4())

def create_device_code_entry():
    """Create a new device code entry in database"""
    user_code = generate_user_code()
    device_code = generate_device_code()
    expires_at = datetime.utcnow() + timedelta(minutes=10)  # 10 minute expiry

    with get_db_session() as session:
        device_code_entry = DeviceCode(
            device_code=device_code,
            user_code=user_code,
            expires_at=expires_at,
            is_activated=False
        )
        session.add(device_code_entry)
        session.commit()
        session.refresh(device_code_entry)

    return device_code_entry

# ========================================
# FASTAPI APP
# ========================================

app = FastAPI(
    title="Quendoo MCP Multi-Tenant Server",
    description="Production MCP server with JWT authentication",
    version="2.0.0"
)

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    Extract and validate JWT token for all MCP requests.
    Sets tenant context for the current thread.
    """
    path = request.url.path

    # Skip auth for health check and OAuth device flow SSE
    if path == "/health" or path == "/mcp/sse":
        return await call_next(request)

    # Extract token from multiple sources
    token = None

    # 1. Query parameter (most compatible with Claude Desktop)
    token = request.query_params.get('token') or request.query_params.get('auth_token')

    # 2. Authorization header (standard)
    if not token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

    # 3. Custom X-User-Token header
    if not token:
        token = request.headers.get('X-User-Token')

    # Require token for other MCP endpoints (not /mcp/sse)
    if not token and path.startswith('/mcp') and path != '/mcp/sse':
        print(f"[ERROR] No token provided for {path}", file=sys.stderr, flush=True)
        return JSONResponse(
            status_code=401,
            content={
                "error": "Authentication required",
                "detail": "Provide JWT token via: ?token=YOUR_TOKEN or Authorization: Bearer YOUR_TOKEN"
            }
        )

    # Validate token (JWT or Device Session ID)
    if token:
        try:
            user_id = None

            # Check if token is a UUID (device session ID) or JWT token
            try:
                # Try to parse as UUID first (device session)
                device_session_id = UUID(token)
                print(f"[INFO] Device session ID detected: {device_session_id}", file=sys.stderr, flush=True)

                # Look up device session in database
                with get_db_session() as db_session:
                    device_session = db_session.query(DeviceSession).filter_by(
                        id=device_session_id,
                        is_active=True
                    ).first()

                    if not device_session:
                        print(f"[ERROR] Invalid or inactive device session", file=sys.stderr, flush=True)
                        return JSONResponse(
                            status_code=401,
                            content={"error": "Invalid or inactive device session"}
                        )

                    user_id = device_session.user_id
                    print(f"[INFO] Device session authenticated for user: {user_id}", file=sys.stderr, flush=True)

                    # Update last_used_at
                    device_session.last_used_at = datetime.utcnow()
                    db_session.commit()

            except ValueError:
                # Not a UUID, try JWT validation
                print(f"[INFO] JWT token detected", file=sys.stderr, flush=True)
                payload = auth_manager.decode_jwt(token)
                if not payload:
                    print(f"[ERROR] Invalid JWT token", file=sys.stderr, flush=True)
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Invalid or expired token"}
                    )

                user_id = UUID(payload['user_id'])
                print(f"[INFO] JWT authenticated for user: {user_id}", file=sys.stderr, flush=True)

            # Get tenant for user
            with get_db_session() as session:
                tenant = session.query(Tenant).filter_by(user_id=user_id).first()

                if not tenant:
                    print(f"[ERROR] Tenant not found for user {user_id}", file=sys.stderr, flush=True)
                    return JSONResponse(
                        status_code=403,
                        content={"error": f"Tenant not found for user {user_id}"}
                    )

                # Set tenant context for this request
                set_current_tenant(tenant.id)
                request.state.tenant_id = str(tenant.id)
                request.state.user_id = str(user_id)

                print(f"[INFO] Tenant context set: {tenant.id}", file=sys.stderr, flush=True)

        except Exception as e:
            print(f"[ERROR] Auth middleware error: {e}", file=sys.stderr, flush=True)
            clear_current_tenant()
            return JSONResponse(
                status_code=401,
                content={"error": f"Authentication failed: {str(e)}"}
            )

    # Process request
    response = await call_next(request)

    # Clear tenant context after request
    clear_current_tenant()

    return response

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {
        "status": "healthy",
        "service": "quendoo-mcp-multitenant",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/mcp/sse")
async def mcp_sse_endpoint(request: Request):
    """
    SSE endpoint for MCP server with OAuth Device Flow support.

    Flow:
    1. Client connects WITHOUT authentication
    2. Server generates device code and sends to client
    3. User opens browser, logs in, enters code
    4. Server polls backend until code is activated
    5. Once activated, tenant context is set and MCP operates normally
    """

    print(f"[INFO] SSE connection request received", file=sys.stderr, flush=True)

    # Import FastMCP server (lazy import to avoid circular dependencies)
    from server_multitenant import server as mcp_server

    async def device_flow_generator():
        """OAuth Device Flow: Generate device code and wait for activation"""
        try:
            # Step 1: Generate device code
            print(f"[INFO] Generating device code for new connection", file=sys.stderr, flush=True)
            device_code_entry = create_device_code_entry()

            device_code = device_code_entry.device_code
            user_code = device_code_entry.user_code

            print(f"[INFO] Device code generated: {user_code} (internal: {device_code})",
                  file=sys.stderr, flush=True)

            # Step 2: Send device code to client
            activation_url = f"https://portal-851052272168.us-central1.run.app/activate?code={user_code}"
            device_auth_message = {
                'type': 'device_authorization_required',
                'user_code': user_code,
                'device_code': device_code,
                'verification_uri': activation_url,
                'expires_in': 600,
                'message': f'Please visit {activation_url} and enter code: {user_code}'
            }
            yield f"data: {json.dumps(device_auth_message)}\n\n"

            # Step 3: Poll backend until activated (max 10 minutes)
            max_attempts = 120  # 120 * 5 seconds = 10 minutes
            attempt = 0

            while attempt < max_attempts:
                await asyncio.sleep(5)  # Poll every 5 seconds
                attempt += 1

                # Check if device code is activated
                with get_db_session() as session:
                    device_code_entry = session.query(DeviceCode).filter_by(
                        device_code=device_code
                    ).first()

                    if not device_code_entry:
                        print(f"[ERROR] Device code not found: {device_code}", file=sys.stderr, flush=True)
                        yield f"data: {json.dumps({'type': 'error', 'message': 'Device code expired or invalid'})}\n\n"
                        return

                    # Check if expired
                    if device_code_entry.expires_at < datetime.utcnow():
                        print(f"[ERROR] Device code expired: {user_code}", file=sys.stderr, flush=True)
                        yield f"data: {json.dumps({'type': 'error', 'message': 'Device code expired. Please reconnect.'})}\n\n"
                        return

                    # Check if activated
                    if device_code_entry.is_activated and device_code_entry.user_id:
                        print(f"[INFO] Device code activated for user: {device_code_entry.user_id}",
                              file=sys.stderr, flush=True)

                        # Get tenant for user
                        tenant = session.query(Tenant).filter_by(
                            user_id=device_code_entry.user_id
                        ).first()

                        if not tenant:
                            print(f"[ERROR] Tenant not found for user {device_code_entry.user_id}",
                                  file=sys.stderr, flush=True)
                            yield f"data: {json.dumps({'type': 'error', 'message': 'Tenant not found'})}\n\n"
                            return

                        # Set tenant context
                        tenant_id = tenant.id
                        user_id = device_code_entry.user_id
                        set_current_tenant(tenant_id)

                        print(f"[INFO] Authentication successful - User: {user_id}, Tenant: {tenant_id}",
                              file=sys.stderr, flush=True)

                        # Send authentication success
                        auth_data = {
                            'type': 'authenticated',
                            'user_id': str(user_id),
                            'tenant_id': str(tenant_id)
                        }
                        yield f"data: {json.dumps(auth_data)}\n\n"

                        # Now start normal MCP operation
                        # Keep connection alive and handle MCP requests
                        while True:
                            await asyncio.sleep(30)
                            yield ": keepalive\n\n"

                # Still waiting for activation
                if attempt % 6 == 0:  # Log every 30 seconds
                    print(f"[INFO] Waiting for device code activation: {user_code} (attempt {attempt}/120)",
                          file=sys.stderr, flush=True)

            # Timeout reached
            print(f"[ERROR] Device code activation timeout: {user_code}", file=sys.stderr, flush=True)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Device activation timeout. Please reconnect.'})}\n\n"

        except asyncio.CancelledError:
            print(f"[INFO] SSE connection closed", file=sys.stderr, flush=True)
            clear_current_tenant()
            raise

        except Exception as e:
            print(f"[ERROR] Device flow error: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()
            clear_current_tenant()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        device_flow_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Quendoo MCP Multi-Tenant Server",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "mcp_sse": "/mcp/sse?token=YOUR_JWT_TOKEN"
        },
        "authentication": "JWT token required via query parameter or Authorization header"
    }

# ========================================
# MAIN
# ========================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"Starting Quendoo MCP Production Server on {host}:{port}", file=sys.stderr, flush=True)
    print(f"Transport: SSE over HTTP", file=sys.stderr, flush=True)

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )
