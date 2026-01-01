"""Flask API Backend for Multi-Tenant Quendoo MCP SaaS Portal."""
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from functools import wraps

from database.connection import get_db_session
from database.models import User, Tenant, Session, DeviceSession, DeviceCode
from security.auth import auth_manager
from api_key_manager_v2 import mt_key_manager
import random
import string

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": False
    }
})
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# ==================== HELPER FUNCTIONS ====================

def get_current_user(token: str) -> dict:
    """
    Decode JWT and return user info if valid.

    Args:
        token: JWT token string

    Returns:
        User payload dict if valid, None if invalid/expired
    """
    payload = auth_manager.decode_jwt(token)
    if not payload:
        return None

    # Verify session exists and not expired
    with get_db_session() as session:
        db_session = session.query(Session).filter_by(
            token_jti=payload['jti']
        ).first()

        if not db_session or db_session.expires_at < datetime.utcnow():
            return None

        return payload


def require_auth(func):
    """
    Decorator to require authentication for endpoints.

    Usage:
        @app.route('/api/protected')
        @require_auth
        def protected_route(user):
            return jsonify({"user_id": user['user_id']})
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid authorization header"}), 401

        token = auth_header.split(' ')[1]
        user = get_current_user(token)
        if not user:
            return jsonify({"error": "Invalid or expired token"}), 401

        return func(user, *args, **kwargs)

    return wrapper


def require_admin(func):
    """
    Decorator to require admin access for endpoints.

    Usage:
        @app.route('/api/admin/users')
        @require_admin
        def admin_route(user):
            return jsonify({"message": "Admin only"})
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid authorization header"}), 401

        token = auth_header.split(' ')[1]
        user_payload = get_current_user(token)
        if not user_payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Check if user is admin
        with get_db_session() as session:
            user = session.query(User).filter_by(
                id=UUID(user_payload['user_id'])
            ).first()

            if not user or not user.is_admin:
                return jsonify({"error": "Admin access required"}), 403

        return func(user_payload, *args, **kwargs)

    return wrapper


# ==================== AUTH ENDPOINTS ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    Register new user and create tenant.

    Request Body:
        {
            "email": "user@example.com",
            "password": "securepassword123",
            "full_name": "John Doe"  (optional)
        }

    Response:
        {
            "success": true,
            "message": "User registered successfully",
            "user_id": "uuid-string"
        }
    """
    data = request.json
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')

    # Validation
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    try:
        with get_db_session() as session:
            # Check if user already exists
            existing_user = session.query(User).filter_by(email=email).first()
            if existing_user:
                return jsonify({"error": "User with this email already exists"}), 409

            # Create user
            user = User(
                email=email,
                password_hash=auth_manager.hash_password(password),
                full_name=full_name,
                is_active=True,
                is_admin=False
            )
            session.add(user)
            session.flush()  # Get user.id

            # Create tenant (1 user = 1 tenant model)
            tenant = Tenant(
                user_id=user.id,
                tenant_name=full_name or email.split('@')[0]
            )
            session.add(tenant)
            session.commit()

            return jsonify({
                "success": True,
                "message": "User registered successfully",
                "user_id": str(user.id)
            }), 201

    except Exception as e:
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Login user and generate JWT token.

    Request Body:
        {
            "email": "user@example.com",
            "password": "securepassword123"
        }

    Response:
        {
            "success": true,
            "token": "eyJhbGciOiJSUzI1NiIs...",
            "expires_at": "2025-02-01T00:00:00",
            "user": {
                "id": "uuid-string",
                "email": "user@example.com",
                "full_name": "John Doe"
            }
        }
    """
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        with get_db_session() as session:
            user = session.query(User).filter_by(email=email, is_active=True).first()

            if not user or not auth_manager.verify_password(password, user.password_hash):
                return jsonify({"error": "Invalid email or password"}), 401

            # Update last login timestamp
            user.last_login_at = datetime.utcnow()

            # Get tenant for user
            tenant = session.query(Tenant).filter_by(user_id=user.id).first()
            if not tenant:
                return jsonify({"error": "Tenant not found for user"}), 500

            # Create session
            jti = str(uuid4())
            expires_at = datetime.utcnow() + timedelta(days=30)

            db_session = Session(
                user_id=user.id,
                token_jti=jti,
                expires_at=expires_at,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')[:500]  # Truncate long user agents
            )
            session.add(db_session)
            session.commit()

            # Generate JWT token with tenant_id
            token = auth_manager.generate_jwt(user.id, user.email, jti, tenant_id=tenant.id)

            return jsonify({
                "success": True,
                "token": token,
                "expires_at": expires_at.isoformat(),
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_admin": user.is_admin
                }
            })

    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500


@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout(user):
    """
    Logout user by invalidating session.

    Headers:
        Authorization: Bearer <jwt-token>

    Response:
        {
            "success": true,
            "message": "Logged out successfully"
        }
    """
    try:
        with get_db_session() as session:
            db_session = session.query(Session).filter_by(
                token_jti=user['jti']
            ).first()

            if db_session:
                session.delete(db_session)
                session.commit()

        return jsonify({
            "success": True,
            "message": "Logged out successfully"
        })

    except Exception as e:
        return jsonify({"error": f"Logout failed: {str(e)}"}), 500


@app.route('/api/auth/validate', methods=['GET'])
@require_auth
def validate_token(user):
    """
    Validate JWT token and return user info.

    Headers:
        Authorization: Bearer <jwt-token>

    Response:
        {
            "valid": true,
            "user_id": "uuid-string",
            "email": "user@example.com"
        }
    """
    return jsonify({
        "valid": True,
        "user_id": user['user_id'],
        "email": user['email']
    })


# ==================== API KEY MANAGEMENT ENDPOINTS ====================

@app.route('/api/keys/list', methods=['GET'])
@require_auth
def list_keys(user):
    """
    List all API keys for the current tenant (without decrypted values).

    Headers:
        Authorization: Bearer <jwt-token>

    Response:
        {
            "keys": [
                {
                    "id": "uuid-string",
                    "key_name": "QUENDOO_API_KEY",
                    "created_at": "2025-01-01T00:00:00",
                    "updated_at": "2025-01-01T00:00:00"
                },
                ...
            ]
        }
    """
    try:
        with get_db_session() as session:
            tenant = session.query(Tenant).filter_by(
                user_id=UUID(user['user_id'])
            ).first()

            if not tenant:
                return jsonify({"error": "Tenant not found"}), 404

            keys = mt_key_manager.list_api_keys(tenant.id)
            return jsonify({"keys": keys})

    except Exception as e:
        return jsonify({"error": f"Failed to list API keys: {str(e)}"}), 500


@app.route('/api/keys/save', methods=['POST'])
@require_auth
def save_key(user):
    """
    Save or update an encrypted API key for the current tenant.

    Headers:
        Authorization: Bearer <jwt-token>

    Request Body:
        {
            "key_name": "QUENDOO_API_KEY",
            "key_value": "246dcadb1ed8f76dee198dae12370285"
        }

    Response:
        {
            "success": true,
            "message": "API key 'QUENDOO_API_KEY' saved successfully",
            "key_id": "uuid-string"
        }
    """
    data = request.json
    key_name = data.get('key_name')
    key_value = data.get('key_value')

    if not key_name or not key_value:
        return jsonify({"error": "key_name and key_value are required"}), 400

    try:
        with get_db_session() as session:
            tenant = session.query(Tenant).filter_by(
                user_id=UUID(user['user_id'])
            ).first()

            if not tenant:
                return jsonify({"error": "Tenant not found"}), 404

            result = mt_key_manager.save_api_key(tenant.id, key_name, key_value)
            return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"Failed to save API key: {str(e)}"}), 500


@app.route('/api/keys/delete', methods=['DELETE'])
@require_auth
def delete_key(user):
    """
    Delete an API key for the current tenant.

    Headers:
        Authorization: Bearer <jwt-token>

    Query Parameters:
        key_name: Name of the key to delete (e.g., "QUENDOO_API_KEY")

    Response:
        {
            "success": true,
            "message": "API key 'QUENDOO_API_KEY' deleted successfully"
        }
    """
    key_name = request.args.get('key_name')

    if not key_name:
        return jsonify({"error": "key_name query parameter is required"}), 400

    try:
        with get_db_session() as session:
            tenant = session.query(Tenant).filter_by(
                user_id=UUID(user['user_id'])
            ).first()

            if not tenant:
                return jsonify({"error": "Tenant not found"}), 404

            result = mt_key_manager.delete_api_key(tenant.id, key_name)
            return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"Failed to delete API key: {str(e)}"}), 500


# ==================== DEVICE SESSION ENDPOINTS ====================

@app.route('/api/devices/list', methods=['GET'])
@require_auth
def list_device_sessions(user):
    """
    List all device sessions for the current user.

    Headers:
        Authorization: Bearer <jwt-token>

    Response:
        {
            "success": true,
            "devices": [
                {
                    "id": "uuid-string",
                    "device_name": "My Laptop",
                    "is_active": true,
                    "created_at": "2025-01-01T00:00:00",
                    "last_used_at": "2025-01-01T00:00:00"
                }
            ]
        }
    """
    try:
        with get_db_session() as session:
            device_sessions = session.query(DeviceSession).filter_by(
                user_id=UUID(user['user_id'])
            ).order_by(DeviceSession.created_at.desc()).all()

            devices = []
            for device in device_sessions:
                devices.append({
                    "id": str(device.id),
                    "device_name": device.device_name,
                    "is_active": device.is_active,
                    "created_at": device.created_at.isoformat() if device.created_at else None,
                    "last_used_at": device.last_used_at.isoformat() if device.last_used_at else None
                })

            return jsonify({"success": True, "devices": devices})

    except Exception as e:
        return jsonify({"error": f"Failed to list device sessions: {str(e)}"}), 500


@app.route('/api/devices/create', methods=['POST'])
@require_auth
def create_device_session(user):
    """
    Create a new device session for Claude Desktop authentication.

    Headers:
        Authorization: Bearer <jwt-token>

    Request Body:
        {
            "device_name": "My Laptop"
        }

    Response:
        {
            "success": true,
            "device": {
                "id": "uuid-string",
                "device_name": "My Laptop",
                "is_active": true,
                "created_at": "2025-01-01T00:00:00"
            },
            "message": "Device session created. Use this ID in your Claude Desktop config."
        }
    """
    data = request.json
    device_name = data.get('device_name')

    if not device_name:
        return jsonify({"error": "device_name is required"}), 400

    try:
        with get_db_session() as session:
            # Create new device session
            device_session = DeviceSession(
                user_id=UUID(user['user_id']),
                device_name=device_name,
                is_active=True
            )
            session.add(device_session)
            session.commit()
            session.refresh(device_session)

            return jsonify({
                "success": True,
                "device": {
                    "id": str(device_session.id),
                    "device_name": device_session.device_name,
                    "is_active": device_session.is_active,
                    "created_at": device_session.created_at.isoformat()
                },
                "message": "Device session created. Use this ID in your Claude Desktop config."
            })

    except Exception as e:
        return jsonify({"error": f"Failed to create device session: {str(e)}"}), 500


@app.route('/api/devices/revoke', methods=['POST'])
@require_auth
def revoke_device_session(user):
    """
    Revoke (deactivate) a device session.

    Headers:
        Authorization: Bearer <jwt-token>

    Request Body:
        {
            "device_id": "uuid-string"
        }

    Response:
        {
            "success": true,
            "message": "Device session revoked successfully"
        }
    """
    data = request.json
    device_id = data.get('device_id')

    if not device_id:
        return jsonify({"error": "device_id is required"}), 400

    try:
        with get_db_session() as session:
            device_session = session.query(DeviceSession).filter_by(
                id=UUID(device_id),
                user_id=UUID(user['user_id'])
            ).first()

            if not device_session:
                return jsonify({"error": "Device session not found"}), 404

            device_session.is_active = False
            session.commit()

            return jsonify({
                "success": True,
                "message": "Device session revoked successfully"
            })

    except Exception as e:
        return jsonify({"error": f"Failed to revoke device session: {str(e)}"}), 500


@app.route('/api/devices/delete', methods=['DELETE'])
@require_auth
def delete_device_session(user):
    """
    Permanently delete a device session.

    Headers:
        Authorization: Bearer <jwt-token>

    Query Parameters:
        device_id: UUID of the device session to delete

    Response:
        {
            "success": true,
            "message": "Device session deleted successfully"
        }
    """
    device_id = request.args.get('device_id')

    if not device_id:
        return jsonify({"error": "device_id query parameter is required"}), 400

    try:
        with get_db_session() as session:
            device_session = session.query(DeviceSession).filter_by(
                id=UUID(device_id),
                user_id=UUID(user['user_id'])
            ).first()

            if not device_session:
                return jsonify({"error": "Device session not found"}), 404

            session.delete(device_session)
            session.commit()

            return jsonify({
                "success": True,
                "message": "Device session deleted successfully"
            })

    except Exception as e:
        return jsonify({"error": f"Failed to delete device session: {str(e)}"}), 500


# ==================== DEVICE CODE (OAuth Device Flow) ENDPOINTS ====================

@app.route('/api/device-flow/generate', methods=['POST'])
@require_auth
def generate_device_code(user):
    """
    Generate a new device code for OAuth Device Flow.
    User can use this code to authenticate their Claude Desktop without token in config.

    Headers:
        Authorization: Bearer <jwt-token>

    Response:
        {
            "success": true,
            "user_code": "ABCD-1234",
            "device_code": "internal-uuid",
            "expires_at": "2025-01-01T00:10:00",
            "verification_url": "https://quendoo-backend.../api/device-flow/activate"
        }
    """
    try:
        user_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        user_code = f"{user_code[:4]}-{user_code[4:]}"  # Format as XXXX-XXXX
        device_code = str(uuid4())
        expires_at = datetime.utcnow() + timedelta(minutes=10)

        with get_db_session() as session:
            device_code_entry = DeviceCode(
                device_code=device_code,
                user_code=user_code,
                user_id=UUID(user['user_id']),
                expires_at=expires_at,
                is_activated=False
            )
            session.add(device_code_entry)
            session.commit()

            return jsonify({
                "success": True,
                "user_code": user_code,
                "device_code": device_code,
                "expires_at": expires_at.isoformat(),
                "verification_url": f"{request.url_root}api/device-flow/activate",
                "message": f"Enter code {user_code} in Claude Desktop or use device_code in MCP URL"
            })

    except Exception as e:
        return jsonify({"error": f"Failed to generate device code: {str(e)}"}), 500


@app.route('/api/device-flow/activate', methods=['POST'])
@require_auth
def activate_device_code(user):
    """
    Activate a device code (associate it with the logged-in user).

    Headers:
        Authorization: Bearer <jwt-token>

    Request Body:
        {
            "user_code": "ABCD-1234"
        }

    Response:
        {
            "success": true,
            "message": "Device activated successfully"
        }
    """
    data = request.json
    user_code = data.get('user_code')

    if not user_code:
        return jsonify({"error": "user_code is required"}), 400

    try:
        with get_db_session() as session:
            device_code_entry = session.query(DeviceCode).filter_by(
                user_code=user_code.upper(),
                is_activated=False
            ).first()

            if not device_code_entry:
                return jsonify({"error": "Invalid or expired device code"}), 404

            if device_code_entry.expires_at < datetime.utcnow():
                return jsonify({"error": "Device code expired"}), 400

            # Activate the device code for this user
            device_code_entry.user_id = UUID(user['user_id'])
            device_code_entry.is_activated = True
            device_code_entry.activated_at = datetime.utcnow()
            session.commit()

            return jsonify({
                "success": True,
                "message": "Device activated successfully. Your Claude Desktop is now connected."
            })

    except Exception as e:
        return jsonify({"error": f"Failed to activate device code: {str(e)}"}), 500


@app.route('/api/device-flow/check', methods=['GET'])
def check_device_code():
    """
    Check if a device code has been activated (used by MCP server polling).

    Query Parameters:
        device_code: The internal device code UUID

    Response:
        {
            "is_activated": true,
            "user_id": "uuid-string",
            "tenant_id": "uuid-string"
        }
    """
    device_code = request.args.get('device_code')

    if not device_code:
        return jsonify({"error": "device_code query parameter is required"}), 400

    try:
        with get_db_session() as session:
            device_code_entry = session.query(DeviceCode).filter_by(
                device_code=device_code,
                is_activated=True
            ).first()

            if not device_code_entry:
                return jsonify({"is_activated": False})

            if device_code_entry.expires_at < datetime.utcnow():
                return jsonify({"is_activated": False, "error": "Device code expired"})

            # Get tenant for user
            tenant = session.query(Tenant).filter_by(
                user_id=device_code_entry.user_id
            ).first()

            return jsonify({
                "is_activated": True,
                "user_id": str(device_code_entry.user_id),
                "tenant_id": str(tenant.id) if tenant else None
            })

    except Exception as e:
        return jsonify({"error": f"Failed to check device code: {str(e)}"}), 500


# ==================== ADMIN ENDPOINTS ====================

@app.route('/api/admin/reset-password', methods=['POST'])
@require_admin
def admin_reset_password(user):
    """
    Admin endpoint to reset user password.

    Headers:
        Authorization: Bearer <admin-jwt-token>

    Request Body:
        {
            "email": "target-user@example.com",
            "new_password": "newpassword123"
        }

    Response:
        {
            "success": true,
            "message": "Password reset for target-user@example.com"
        }
    """
    data = request.json
    target_email = data.get('email')
    new_password = data.get('new_password')

    if not target_email or not new_password:
        return jsonify({"error": "email and new_password are required"}), 400

    if len(new_password) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400

    try:
        with get_db_session() as session:
            target_user = session.query(User).filter_by(email=target_email).first()
            if not target_user:
                return jsonify({"error": "User not found"}), 404

            target_user.password_hash = auth_manager.hash_password(new_password)
            session.commit()

            return jsonify({
                "success": True,
                "message": f"Password reset successfully for {target_email}"
            })

    except Exception as e:
        return jsonify({"error": f"Password reset failed: {str(e)}"}), 500


@app.route('/api/admin/users', methods=['GET'])
@require_admin
def admin_list_users(user):
    """
    Admin endpoint to list all users.

    Headers:
        Authorization: Bearer <admin-jwt-token>

    Response:
        {
            "users": [
                {
                    "id": "uuid-string",
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "is_active": true,
                    "is_admin": false,
                    "created_at": "2025-01-01T00:00:00"
                },
                ...
            ]
        }
    """
    try:
        with get_db_session() as session:
            users = session.query(User).all()

            return jsonify({
                "users": [
                    {
                        "id": str(u.id),
                        "email": u.email,
                        "full_name": u.full_name,
                        "is_active": u.is_active,
                        "is_admin": u.is_admin,
                        "created_at": u.created_at.isoformat() if u.created_at else None,
                        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None
                    }
                    for u in users
                ]
            })

    except Exception as e:
        return jsonify({"error": f"Failed to list users: {str(e)}"}), 500


# ==================== HEALTH & INFO ENDPOINTS ====================

@app.route('/api/health', methods=['GET'])
def health():
    """
    Health check endpoint.

    Response:
        {
            "status": "healthy",
            "service": "quendoo-mcp-backend",
            "version": "1.0.0"
        }
    """
    return jsonify({
        "status": "healthy",
        "service": "quendoo-mcp-backend",
        "version": "1.0.0"
    })


@app.route('/api/info', methods=['GET'])
def info():
    """
    API information endpoint.

    Response:
        {
            "name": "Quendoo MCP Multi-Tenant API",
            "version": "1.0.0",
            "endpoints": {
                "auth": ["/api/auth/register", "/api/auth/login", ...],
                "keys": ["/api/keys/list", "/api/keys/save", ...],
                "admin": ["/api/admin/reset-password", "/api/admin/users"]
            }
        }
    """
    return jsonify({
        "name": "Quendoo MCP Multi-Tenant API",
        "version": "1.0.0",
        "endpoints": {
            "auth": [
                "POST /api/auth/register",
                "POST /api/auth/login",
                "POST /api/auth/logout",
                "GET /api/auth/validate"
            ],
            "keys": [
                "GET /api/keys/list",
                "POST /api/keys/save",
                "DELETE /api/keys/delete"
            ],
            "admin": [
                "POST /api/admin/reset-password",
                "GET /api/admin/users"
            ],
            "info": [
                "GET /api/health",
                "GET /api/info"
            ]
        }
    })


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


# ==================== MAIN ====================

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    print(f"Starting Quendoo MCP Backend on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
