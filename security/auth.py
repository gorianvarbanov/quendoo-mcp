"""Authentication manager for password hashing and JWT token management."""
import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict
from uuid import UUID
from dotenv import load_dotenv

load_dotenv()

# JWT configuration
JWT_SECRET_KEY = os.getenv("JWT_PRIVATE_KEY", "")[:64]  # Use first 64 chars as secret
JWT_ALGORITHM = "HS256"  # Symmetric algorithm for simplicity
TOKEN_EXPIRY_DAYS = 30  # 30-day validity as per requirements


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
    def generate_jwt(user_id: UUID, email: str, jti: str) -> str:
        """
        Generate JWT token with 30-day expiry.

        Args:
            user_id: User's UUID
            email: User's email
            jti: JWT ID (unique identifier for token revocation)

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
        if not JWT_SECRET_KEY:
            raise ValueError("JWT_PRIVATE_KEY environment variable is required")

        payload = {
            "user_id": str(user_id),
            "email": email,
            "jti": jti,  # JWT ID for revocation support
            "exp": datetime.utcnow() + timedelta(days=TOKEN_EXPIRY_DAYS),
            "iat": datetime.utcnow(),  # Issued at
        }

        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def decode_jwt(token: str) -> Optional[Dict]:
        """
        Decode and validate JWT token.

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
        if not JWT_SECRET_KEY:
            raise ValueError("JWT_PRIVATE_KEY environment variable is required")

        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            # Token has expired
            return None
        except jwt.InvalidTokenError:
            # Token is invalid
            return None


# Singleton instance
auth_manager = AuthManager()
