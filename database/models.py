"""SQLAlchemy database models for multi-tenant Quendoo MCP."""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()


class User(Base):
    """User model - represents registered users."""
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)

    # Relationships
    tenant = relationship("Tenant", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Tenant(Base):
    """Tenant model - 1 user = 1 tenant model."""
    __tablename__ = 'tenants'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        unique=True,
        nullable=False,
        index=True
    )
    tenant_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="tenant")
    api_keys = relationship("ApiKey", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(id={self.id}, name={self.tenant_name})>"


class ApiKey(Base):
    """ApiKey model - encrypted storage of tenant API keys."""
    __tablename__ = 'api_keys'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey('tenants.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    key_name = Column(String(100), nullable=False)  # 'QUENDOO_API_KEY', 'EMAIL_API_KEY', etc.
    encrypted_value = Column(Text, nullable=False)  # AES-256 encrypted
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")

    # Unique constraint: one key_name per tenant
    __table_args__ = (
        UniqueConstraint('tenant_id', 'key_name', name='uq_tenant_key_name'),
    )

    def __repr__(self):
        return f"<ApiKey(id={self.id}, tenant_id={self.tenant_id}, key_name={self.key_name})>"


class Session(Base):
    """Session model - JWT session tracking for revocation support."""
    __tablename__ = 'sessions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    token_jti = Column(String(255), unique=True, nullable=False, index=True)  # JWT ID
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))  # IPv4/IPv6
    user_agent = Column(Text)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"


class DeviceSession(Base):
    """DeviceSession model - long-lived device authentication for Claude Desktop.

    Instead of storing JWT tokens in Claude Desktop config, users store a device session ID.
    The MCP server uses this ID to look up the user and generate/fetch JWT tokens automatically.
    """
    __tablename__ = 'device_sessions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    device_name = Column(String(255), nullable=False)  # e.g., "My Laptop", "Work Computer"
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="device_sessions")

    def __repr__(self):
        return f"<DeviceSession(id={self.id}, user_id={self.user_id}, device_name={self.device_name})>"


class DeviceCode(Base):
    """DeviceCode model - OAuth Device Flow for passwordless MCP authentication.

    Allows Claude Desktop to connect without tokens in config.
    User authenticates via browser by entering device code.
    """
    __tablename__ = 'device_codes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_code = Column(String(20), unique=True, nullable=False, index=True)  # e.g., "ABCD-1234"
    user_code = Column(String(20), unique=True, nullable=False, index=True)    # Human-readable code
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=True,  # NULL until user activates
        index=True
    )
    device_name = Column(String(255))  # Optional device name
    is_activated = Column(Boolean, default=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime)

    # Relationships
    user = relationship("User", backref="device_codes")

    def __repr__(self):
        return f"<DeviceCode(user_code={self.user_code}, is_activated={self.is_activated})>"
