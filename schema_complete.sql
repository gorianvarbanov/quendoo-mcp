-- Complete PostgreSQL schema for Quendoo MCP with Stytch OAuth
-- This combines all tables: users, OAuth clients, authorization codes, and access tokens

-- ============================================================================
-- Users Table (with Stytch integration)
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    quendoo_api_key VARCHAR(255),
    email_api_key VARCHAR(255),
    stytch_user_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_stytch_user_id ON users(stytch_user_id);

COMMENT ON COLUMN users.stytch_user_id IS 'Stytch user ID from OAuth authentication';

-- ============================================================================
-- OAuth Clients Table (for Dynamic Client Registration)
-- ============================================================================

CREATE TABLE IF NOT EXISTS oauth_clients (
    client_id VARCHAR(255) PRIMARY KEY,
    client_secret VARCHAR(255),
    client_name VARCHAR(255),
    redirect_uris TEXT[],
    grant_types TEXT[],
    response_types TEXT[],
    scope TEXT,
    token_endpoint_auth_method VARCHAR(50) DEFAULT 'client_secret_basic',
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_oauth_clients_client_id ON oauth_clients(client_id);

-- ============================================================================
-- Authorization Codes Table (for OAuth flow)
-- ============================================================================

CREATE TABLE IF NOT EXISTS authorization_codes (
    code VARCHAR(255) PRIMARY KEY,
    client_id VARCHAR(255) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    redirect_uri TEXT NOT NULL,
    scope TEXT,
    code_challenge VARCHAR(255),
    code_challenge_method VARCHAR(10) DEFAULT 'S256',
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_auth_codes_code ON authorization_codes(code);
CREATE INDEX IF NOT EXISTS idx_auth_codes_client_id ON authorization_codes(client_id);
CREATE INDEX IF NOT EXISTS idx_auth_codes_user_id ON authorization_codes(user_id);

-- ============================================================================
-- Access Tokens Table (for revocation tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS access_tokens (
    token VARCHAR(500) PRIMARY KEY,
    client_id VARCHAR(255) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scope TEXT,
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_access_tokens_token ON access_tokens(token);
CREATE INDEX IF NOT EXISTS idx_access_tokens_client_id ON access_tokens(client_id);
CREATE INDEX IF NOT EXISTS idx_access_tokens_user_id ON access_tokens(user_id);

-- ============================================================================
-- Triggers for automatic timestamp updates
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER IF NOT EXISTS update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Verification queries (run these after schema creation to verify)
-- ============================================================================

-- Verify all tables exist
-- SELECT table_name
-- FROM information_schema.tables
-- WHERE table_schema = 'public'
-- AND table_name IN ('users', 'oauth_clients', 'authorization_codes', 'access_tokens')
-- ORDER BY table_name;

-- Verify users table columns
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'users'
-- ORDER BY ordinal_position;
