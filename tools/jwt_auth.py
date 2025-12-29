"""JWT token generation and validation."""
import base64
import os
from datetime import datetime, timedelta
from typing import Any

import jwt
import bcrypt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


# JWT settings - Using RS256 for OAuth compatibility
JWT_ALGORITHM = "RS256"
JWT_EXPIRATION_HOURS = 720  # 30 days

# Load or generate RSA private key
def _get_private_key():
    """Get RSA private key from environment or generate new one."""
    private_key_pem = os.getenv("JWT_PRIVATE_KEY")

    if private_key_pem:
        return serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
            backend=default_backend()
        )
    else:
        # Generate new 2048-bit RSA key
        import sys
        print("[WARNING] No JWT_PRIVATE_KEY found, generating new key", file=sys.stderr)
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # Print key for saving
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        print(f"[INFO] Save this to JWT_PRIVATE_KEY env var:\n{pem}", file=sys.stderr)

        return private_key

PRIVATE_KEY = _get_private_key()
PUBLIC_KEY = PRIVATE_KEY.public_key()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def create_jwt_token(user_id: int, email: str) -> str:
    """Create a JWT token for a user using RS256."""
    payload = {
        "user_id": user_id,
        "email": email,
        "sub": str(user_id),  # Standard JWT claim for subject
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
        "iss": os.getenv("MCP_SERVER_URL", "https://quendoo-mcp-server-880871219885.us-central1.run.app")
    }
    return jwt.encode(
        payload,
        PRIVATE_KEY,
        algorithm=JWT_ALGORITHM,
        headers={"kid": "quendoo-mcp-key-1"}
    )


def decode_jwt_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token using RS256."""
    try:
        payload = jwt.decode(
            token,
            PUBLIC_KEY,
            algorithms=[JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_jwks() -> dict[str, Any]:
    """Get JSON Web Key Set (JWKS) for public key distribution."""
    # Get public key numbers
    public_numbers = PUBLIC_KEY.public_numbers()

    # Convert to base64url format
    def int_to_base64url(n: int) -> str:
        byte_length = (n.bit_length() + 7) // 8
        n_bytes = n.to_bytes(byte_length, byteorder='big')
        return base64.urlsafe_b64encode(n_bytes).decode('utf-8').rstrip('=')

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": "quendoo-mcp-key-1",
                "alg": "RS256",
                "n": int_to_base64url(public_numbers.n),
                "e": int_to_base64url(public_numbers.e)
            }
        ]
    }
