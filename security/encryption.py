"""Encryption manager for securing sensitive data like API keys."""
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from dotenv import load_dotenv

load_dotenv()


class EncryptionManager:
    """
    Handles encryption/decryption of sensitive data using AES-256 via Fernet.

    Uses JWT_PRIVATE_KEY as master key source and derives encryption key via PBKDF2.
    """

    def __init__(self):
        # Use JWT_PRIVATE_KEY as master key source (already exists in .env)
        master_key_source = os.getenv("JWT_PRIVATE_KEY", "")

        if not master_key_source:
            raise ValueError("JWT_PRIVATE_KEY environment variable is required for encryption")

        master_key = master_key_source.encode()

        # Derive encryption key using PBKDF2 (Key Derivation Function)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 32 bytes = 256 bits
            salt=b'quendoo_mcp_salt_v1',  # Static salt for consistent key derivation
            iterations=100000,  # High iteration count for security
        )
        derived_key = kdf.derive(master_key)

        # Create Fernet cipher with base64-encoded key
        key = base64.urlsafe_b64encode(derived_key)
        self.cipher = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext and return base64 encoded ciphertext.

        Args:
            plaintext: String to encrypt (e.g., API key)

        Returns:
            Base64 encoded encrypted string

        Example:
            >>> manager = EncryptionManager()
            >>> encrypted = manager.encrypt("my_secret_api_key")
            >>> print(encrypted)  # 'gAAAAABf...'
        """
        if not plaintext:
            raise ValueError("Plaintext cannot be empty")

        encrypted_bytes = self.cipher.encrypt(plaintext.encode())
        return encrypted_bytes.decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext and return plaintext.

        Args:
            ciphertext: Base64 encoded encrypted string

        Returns:
            Decrypted plaintext string

        Example:
            >>> manager = EncryptionManager()
            >>> decrypted = manager.decrypt("gAAAAABf...")
            >>> print(decrypted)  # 'my_secret_api_key'
        """
        if not ciphertext:
            raise ValueError("Ciphertext cannot be empty")

        try:
            decrypted_bytes = self.cipher.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")


# Singleton instance
encryption_manager = EncryptionManager()
