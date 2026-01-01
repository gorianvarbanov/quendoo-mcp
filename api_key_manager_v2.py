"""Multi-tenant API Key Manager with database storage and encryption."""
from typing import Optional, Dict, List
from uuid import UUID
from database.connection import get_db_session
from database.models import ApiKey, Tenant
from security.encryption import encryption_manager


class MultiTenantApiKeyManager:
    """
    Manages API keys for multiple tenants with encryption.

    All API keys are encrypted before storage and decrypted on retrieval.
    Each tenant can have multiple API keys (QUENDOO_API_KEY, EMAIL_API_KEY, etc.).
    """

    @staticmethod
    def save_api_key(tenant_id: UUID, key_name: str, key_value: str) -> Dict:
        """
        Save or update an encrypted API key for a tenant.

        Args:
            tenant_id: UUID of the tenant
            key_name: Name of the key (e.g., 'QUENDOO_API_KEY')
            key_value: Plain text value of the API key

        Returns:
            Dictionary with success status and message

        Example:
            >>> result = MultiTenantApiKeyManager.save_api_key(
            ...     tenant_id=UUID('...'),
            ...     key_name='QUENDOO_API_KEY',
            ...     key_value='246dcadb1ed8f76dee198dae12370285'
            ... )
            >>> print(result)  # {'success': True, 'message': '...', 'key_id': '...'}
        """
        if not key_name or not key_value:
            return {
                "success": False,
                "message": "key_name and key_value are required"
            }

        # Encrypt the API key
        encrypted_value = encryption_manager.encrypt(key_value)

        with get_db_session() as session:
            # Check if key already exists for this tenant
            api_key = session.query(ApiKey).filter_by(
                tenant_id=tenant_id,
                key_name=key_name
            ).first()

            if api_key:
                # Update existing key
                api_key.encrypted_value = encrypted_value
                api_key.is_active = True
                message = f"API key '{key_name}' updated successfully"
            else:
                # Create new key
                api_key = ApiKey(
                    tenant_id=tenant_id,
                    key_name=key_name,
                    encrypted_value=encrypted_value,
                    is_active=True
                )
                session.add(api_key)
                message = f"API key '{key_name}' saved successfully"

            session.commit()

            return {
                "success": True,
                "message": message,
                "key_id": str(api_key.id)
            }

    @staticmethod
    def get_api_key(tenant_id: UUID, key_name: str) -> Optional[str]:
        """
        Retrieve and decrypt an API key for a tenant.

        Args:
            tenant_id: UUID of the tenant
            key_name: Name of the key (e.g., 'QUENDOO_API_KEY')

        Returns:
            Decrypted API key value if found, None otherwise

        Example:
            >>> key = MultiTenantApiKeyManager.get_api_key(
            ...     tenant_id=UUID('...'),
            ...     key_name='QUENDOO_API_KEY'
            ... )
            >>> print(key)  # '246dcadb1ed8f76dee198dae12370285' or None
        """
        with get_db_session() as session:
            api_key = session.query(ApiKey).filter_by(
                tenant_id=tenant_id,
                key_name=key_name,
                is_active=True
            ).first()

            if not api_key:
                return None

            # Decrypt and return
            try:
                return encryption_manager.decrypt(api_key.encrypted_value)
            except Exception as e:
                print(f"Error decrypting API key: {e}")
                return None

    @staticmethod
    def list_api_keys(tenant_id: UUID) -> List[Dict]:
        """
        List all API keys for a tenant (without decrypting values).

        Args:
            tenant_id: UUID of the tenant

        Returns:
            List of dictionaries with key metadata (no values)

        Example:
            >>> keys = MultiTenantApiKeyManager.list_api_keys(tenant_id=UUID('...'))
            >>> print(keys)
            [
                {
                    'id': '...',
                    'key_name': 'QUENDOO_API_KEY',
                    'created_at': '2025-01-01T00:00:00',
                    'updated_at': '2025-01-01T00:00:00'
                },
                ...
            ]
        """
        with get_db_session() as session:
            keys = session.query(ApiKey).filter_by(
                tenant_id=tenant_id,
                is_active=True
            ).all()

            return [
                {
                    "id": str(key.id),
                    "key_name": key.key_name,
                    "created_at": key.created_at.isoformat(),
                    "updated_at": key.updated_at.isoformat()
                }
                for key in keys
            ]

    @staticmethod
    def delete_api_key(tenant_id: UUID, key_name: str) -> Dict:
        """
        Delete (soft delete) an API key for a tenant.

        Args:
            tenant_id: UUID of the tenant
            key_name: Name of the key to delete

        Returns:
            Dictionary with success status and message

        Example:
            >>> result = MultiTenantApiKeyManager.delete_api_key(
            ...     tenant_id=UUID('...'),
            ...     key_name='QUENDOO_API_KEY'
            ... )
            >>> print(result)  # {'success': True, 'message': '...'}
        """
        with get_db_session() as session:
            api_key = session.query(ApiKey).filter_by(
                tenant_id=tenant_id,
                key_name=key_name
            ).first()

            if not api_key:
                return {
                    "success": False,
                    "message": f"API key '{key_name}' not found"
                }

            # Soft delete (mark as inactive)
            api_key.is_active = False
            session.commit()

            return {
                "success": True,
                "message": f"API key '{key_name}' deleted successfully"
            }

    @staticmethod
    def get_tenant_by_user_id(user_id: UUID) -> Optional[UUID]:
        """
        Get tenant_id for a given user_id.

        Args:
            user_id: UUID of the user

        Returns:
            Tenant UUID if found, None otherwise

        Example:
            >>> tenant_id = MultiTenantApiKeyManager.get_tenant_by_user_id(UUID('...'))
            >>> print(tenant_id)  # UUID('...') or None
        """
        with get_db_session() as session:
            tenant = session.query(Tenant).filter_by(user_id=user_id).first()
            return tenant.id if tenant else None


# Singleton instance
mt_key_manager = MultiTenantApiKeyManager()
