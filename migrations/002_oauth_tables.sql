-- OAuth 2.1 Authorization Server Tables

-- OAuth clients (applications that can use OAuth)
CREATE TABLE IF NOT EXISTS oauth_clients (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(255) UNIQUE NOT NULL,
    client_secret VARCHAR(255),  -- NULL for public clients
    client_name VARCHAR(255) NOT NULL,
    redirect_uris TEXT[] NOT NULL,  -- Array of allowed redirect URIs
    grant_types TEXT[] NOT NULL DEFAULT ARRAY['authorization_code'],
    response_types TEXT[] NOT NULL DEFAULT ARRAY['code'],
    scope TEXT DEFAULT 'openid profile email quendoo:pms',
    token_endpoint_auth_method VARCHAR(50) DEFAULT 'client_secret_basic',
    is_public BOOLEAN DEFAULT false,  -- True for native/desktop apps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Authorization codes (temporary codes exchanged for tokens)
CREATE TABLE IF NOT EXISTS authorization_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(255) UNIQUE NOT NULL,
    client_id VARCHAR(255) NOT NULL REFERENCES oauth_clients(client_id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    redirect_uri TEXT NOT NULL,
    scope TEXT NOT NULL,
    code_challenge VARCHAR(255) NOT NULL,  -- PKCE challenge
    code_challenge_method VARCHAR(10) NOT NULL DEFAULT 'S256',  -- S256 or plain
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for authorization_codes
CREATE INDEX IF NOT EXISTS idx_auth_code ON authorization_codes(code);
CREATE INDEX IF NOT EXISTS idx_auth_code_client ON authorization_codes(client_id);
CREATE INDEX IF NOT EXISTS idx_auth_code_user ON authorization_codes(user_id);

-- Access tokens (for tracking and revocation)
CREATE TABLE IF NOT EXISTS access_tokens (
    id SERIAL PRIMARY KEY,
    token TEXT NOT NULL,  -- JWT token
    client_id VARCHAR(255) NOT NULL REFERENCES oauth_clients(client_id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    scope TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for access_tokens
CREATE INDEX IF NOT EXISTS idx_access_token_user ON access_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_access_token_client ON access_tokens(client_id);

-- Create default public client for Claude Desktop
INSERT INTO oauth_clients (
    client_id,
    client_secret,
    client_name,
    redirect_uris,
    grant_types,
    response_types,
    scope,
    token_endpoint_auth_method,
    is_public
) VALUES (
    'claude-desktop-public',
    NULL,  -- No secret for public client
    'Claude Desktop',
    ARRAY[
        'http://127.0.0.1:3000',
        'http://127.0.0.1:3001',
        'http://127.0.0.1:3002',
        'http://127.0.0.1:8080'
    ],
    ARRAY['authorization_code'],
    ARRAY['code'],
    'openid profile email quendoo:pms',
    'none',  -- Public client
    true
) ON CONFLICT (client_id) DO NOTHING;
