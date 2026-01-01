"""Authentication manager for password hashing and JWT token management."""
import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict
from uuid import UUID
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

load_dotenv()

# JWT configuration
JWT_PRIVATE_KEY_PEM = os.getenv("JWT_PRIVATE_KEY", "")  # Full RSA private key PEM
JWT_ALGORITHM = "RS256"  # Asymmetric algorithm for FastMCP JWTVerifier
TOKEN_EXPIRY_DAYS = 30  # 30-day validity as per requirements

# Load RSA private key
try:
    if JWT_PRIVATE_KEY_PEM:
        JWT_PRIVATE_KEY = serialization.load_pem_private_key(
            JWT_PRIVATE_KEY_PEM.encode(),
            password=None,
            backend=default_backend()
        )
        JWT_PUBLIC_KEY = JWT_PRIVATE_KEY.public_key()
    else:
        JWT_PRIVATE_KEY = None
        JWT_PUBLIC_KEY = None
except Exception as e:
    print(f"[WARNING] Failed to load RSA keys: {e}")
    JWT_PRIVATE_KEY = None
    JWT_PUBLIC_KEY = None


class AuthManager:
    """
    Handles password hashing (bcrypt) and JWT token generation/validation.
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt with automatically generated salt.

        Args:
            password: Plain text password

        Returns:
            Bcrypt hashed password

        Example:
            >>> hashed = AuthManager.hash_password("mypassword123")
            >>> print(hashed)  # '$2b$12$...'
        """
        if not password:
            raise ValueError("Password cannot be empty")

        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)
        return hashed.decode()

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify password against hash.

        Args:
            password: Plain text password to verify
            password_hash: Bcrypt hashed password

        Returns:
            True if password matches, False otherwise

        Example:
            >>> hashed = AuthManager.hash_password("mypassword123")
            >>> AuthManager.verify_password("mypassword123", hashed)  # True
            >>> AuthManager.verify_password("wrongpassword", hashed)  # False
        """
        if not password or not password_hash:
            return False

        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except Exception:
            return False

    @staticmethod
    def generate_jwt(user_id: UUID, email: str, jti: str, tenant_id: Optional[UUID] = None) -> str:
        """
        Generate JWT token with 30-day expiry using RS256.

        Args:
            user_id: User's UUID
            email: User's email
            jti: JWT ID (unique identifier for token revocation)
            tenant_id: Tenant UUID (optional)

        Returns:
            JWT token string

        Example:
            >>> import uuid
            >>> token = AuthManager.generate_jwt(
            ...     user_id=uuid.uuid4(),
            ...     email="user@example.com",
            ...     jti=str(uuid.uuid4())
            ... )
            >>> print(token)  # 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...'
        """
        if not JWT_PRIVATE_KEY:
            raise ValueError("JWT_PRIVATE_KEY environment variable is required")

        payload = {
            "user_id": str(user_id),
            "email": email,
            "jti": jti,  # JWT ID for revocation support
            "exp": datetime.utcnow() + timedelta(days=TOKEN_EXPIRY_DAYS),
            "iat": datetime.utcnow(),  # Issued at
            "sub": str(user_id),  # Subject claim (standard)
            "iss": os.getenv("JWT_ISSUER", "https://quendoo-mcp-multitenant-851052272168.us-central1.run.app"),  # Issuer
        }

        if tenant_id:
            payload["tenant_id"] = str(tenant_id)

        return jwt.encode(payload, JWT_PRIVATE_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def decode_jwt(token: str) -> Optional[Dict]:
        """
        Decode and validate JWT token using RS256 public key.

        Args:
            token: JWT token string

        Returns:
            Decoded payload dict if valid, None if invalid/expired

        Example:
            >>> token = AuthManager.generate_jwt(...)
            >>> payload = AuthManager.decode_jwt(token)
            >>> print(payload['user_id'])  # UUID string
            >>> print(payload['email'])    # 'user@example.com'
        """
        if not JWT_PUBLIC_KEY:
            raise ValueError("JWT_PRIVATE_KEY environment variable is required")

        try:
            payload = jwt.decode(token, JWT_PUBLIC_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            # Token has expired
            return None
        except jwt.InvalidTokenError:
            # Token is invalid
            return None

    @staticmethod
    def get_public_key_pem() -> str:
        """
        Get public key in PEM format for JWKS endpoint.

        Returns:
            Public key PEM string
        """
        if not JWT_PUBLIC_KEY:
            raise ValueError("JWT_PRIVATE_KEY environment variable is required")

        public_pem = JWT_PUBLIC_KEY.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return public_pem.decode()


# Singleton instance
auth_manager = AuthManager()
