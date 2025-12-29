-- Additional tables for OAuth 2.1 support
-- Run this after schema.sql to add OAuth functionality

-- OAuth registered clients (for Dynamic Client Registration)
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

CREATE INDEX idx_oauth_clients_client_id ON oauth_clients(client_id);

-- Authorization codes for OAuth flow
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

CREATE INDEX idx_auth_codes_code ON authorization_codes(code);
CREATE INDEX idx_auth_codes_client_id ON authorization_codes(client_id);
CREATE INDEX idx_auth_codes_user_id ON authorization_codes(user_id);

-- Issued access tokens (for revocation tracking)
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

CREATE INDEX idx_access_tokens_token ON access_tokens(token);
CREATE INDEX idx_access_tokens_client_id ON access_tokens(client_id);
CREATE INDEX idx_access_tokens_user_id ON access_tokens(user_id);
