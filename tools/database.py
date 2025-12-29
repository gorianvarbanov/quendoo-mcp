"""Database client for user authentication and API key storage."""
import os
import secrets
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor


class DatabaseClient:
    """PostgreSQL client for user management."""

    def __init__(self, connection_string: str | None = None) -> None:
        self.connection_string = connection_string or os.getenv("DATABASE_URL")
        if not self.connection_string:
            raise ValueError("DATABASE_URL environment variable is required")

    def _get_connection(self):
        """Get a database connection."""
        return psycopg2.connect(self.connection_string, cursor_factory=RealDictCursor)

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Get user by email address."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, password_hash, quendoo_api_key, email_api_key, stytch_user_id FROM users WHERE email = %s",
                    (email,)
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def get_user_by_stytch_id(self, stytch_user_id: str) -> dict[str, Any] | None:
        """Get user by Stytch user ID."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, password_hash, quendoo_api_key, email_api_key, stytch_user_id FROM users WHERE stytch_user_id = %s",
                    (stytch_user_id,)
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def create_or_update_stytch_user(self, stytch_user_id: str, email: str, quendoo_api_key: str | None = None) -> int:
        """Create or update user from Stytch authentication."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Check if user exists by stytch_user_id
                cur.execute(
                    "SELECT id FROM users WHERE stytch_user_id = %s",
                    (stytch_user_id,)
                )
                existing = cur.fetchone()

                if existing:
                    # Update existing user
                    if quendoo_api_key:
                        cur.execute(
                            "UPDATE users SET email = %s, quendoo_api_key = %s WHERE stytch_user_id = %s RETURNING id",
                            (email, quendoo_api_key, stytch_user_id)
                        )
                    else:
                        cur.execute(
                            "UPDATE users SET email = %s WHERE stytch_user_id = %s RETURNING id",
                            (email, stytch_user_id)
                        )
                    result = cur.fetchone()
                    conn.commit()
                    return result["id"] if result else existing["id"]
                else:
                    # Check if user exists by email (might be from old system or different stytch_user_id)
                    cur.execute(
                        "SELECT id FROM users WHERE email = %s",
                        (email,)
                    )
                    existing_by_email = cur.fetchone()

                    if existing_by_email:
                        # Update existing user with new stytch_user_id
                        if quendoo_api_key:
                            cur.execute(
                                "UPDATE users SET stytch_user_id = %s, quendoo_api_key = %s WHERE email = %s RETURNING id",
                                (stytch_user_id, quendoo_api_key, email)
                            )
                        else:
                            cur.execute(
                                "UPDATE users SET stytch_user_id = %s WHERE email = %s RETURNING id",
                                (stytch_user_id, email)
                            )
                        result = cur.fetchone()
                        conn.commit()
                        return result["id"] if result else existing_by_email["id"]
                    else:
                        # Create new user
                        import bcrypt
                        # Generate random password for Stytch users (they login via OAuth)
                        random_password = secrets.token_urlsafe(32)
                        password_hash = bcrypt.hashpw(random_password.encode(), bcrypt.gensalt()).decode()

                        cur.execute(
                            """
                            INSERT INTO users (email, password_hash, quendoo_api_key, stytch_user_id)
                            VALUES (%s, %s, %s, %s)
                            RETURNING id
                            """,
                            (email, password_hash, quendoo_api_key, stytch_user_id)
                        )
                        result = cur.fetchone()
                        conn.commit()
                        return result["id"] if result else 0

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        """Get user by ID."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, password_hash, quendoo_api_key, email_api_key FROM users WHERE id = %s",
                    (user_id,)
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def create_user(self, email: str, password_hash: str, quendoo_api_key: str, email_api_key: str | None = None) -> int:
        """Create a new user and return their ID."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (email, password_hash, quendoo_api_key, email_api_key)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (email, password_hash, quendoo_api_key, email_api_key)
                )
                result = cur.fetchone()
                conn.commit()
                return result["id"] if result else 0

    def authenticate_user(self, email: str, password: str) -> dict[str, Any] | None:
        """Authenticate user with email and password."""
        import bcrypt

        user = self.get_user_by_email(email)
        if not user:
            return None

        # Verify password
        password_hash = user.get("password_hash", "")
        if not password_hash:
            return None

        try:
            if bcrypt.checkpw(password.encode(), password_hash.encode()):
                return user
        except Exception:
            return None

        return None

    def update_api_keys(self, user_id: int, quendoo_api_key: str | None = None, email_api_key: str | None = None) -> bool:
        """Update API keys for a user."""
        updates = []
        params = []

        if quendoo_api_key is not None:
            updates.append("quendoo_api_key = %s")
            params.append(quendoo_api_key)

        if email_api_key is not None:
            updates.append("email_api_key = %s")
            params.append(email_api_key)

        if not updates:
            return False

        params.append(user_id)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE users SET {', '.join(updates)} WHERE id = %s",
                    params
                )
                conn.commit()
                return cur.rowcount > 0

    def update_user_api_key(self, user_id: int, quendoo_api_key: str) -> bool:
        """Update Quendoo API key for a user (alias for update_api_keys)."""
        return self.update_api_keys(user_id, quendoo_api_key=quendoo_api_key)
