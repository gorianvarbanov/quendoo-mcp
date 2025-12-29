# Stytch OAuth Integration - Complete Setup Guide

## Overview

This guide covers the complete Stytch OAuth integration for Quendoo MCP server with web-based API key management.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│                 │         │                  │         │                  │
│  Claude Desktop │◄────────│   MCP Server     │◄────────│   Supabase DB    │
│  (MCP Client)   │  OAuth  │  (Cloud Run)     │  User   │  (PostgreSQL)    │
│                 │  Token  │                  │  Data   │                  │
└─────────────────┘         └──────────────────┘         └──────────────────┘
                                      ▲
                                      │
                                      │ API Key Setup
                                      │
                            ┌─────────┴─────────┐
                            │                   │
                            │   Web App         │
                            │   (React+Flask)   │
                            │                   │
                            └───────────────────┘
                                      │
                                      │ Auth Flow
                                      ▼
                            ┌───────────────────┐
                            │                   │
                            │   Stytch OAuth    │
                            │   (M2M Provider)  │
                            │                   │
                            └───────────────────┘
```

## Components

### 1. **Stytch OAuth Provider**
- Handles user authentication
- Issues M2M access tokens
- Provides OAuth 2.1 authorization server

### 2. **MCP Server** (server.py)
- Validates Stytch tokens via `StytchTokenVerifier`
- Serves Protected Resource Metadata endpoint
- Provides MCP tools for Quendoo PMS

### 3. **Web App** (web-app/)
- React frontend with Stytch IdentityProvider
- API key management interface
- Flask backend API endpoints

### 4. **Database** (Supabase PostgreSQL)
- Stores users with `stytch_user_id`
- Links Stytch users to Quendoo API keys
- Multi-tenant safe storage

## Step-by-Step Setup

### Step 1: Configure Stytch Project

1. **Go to Stytch Dashboard**: https://stytch.com/dashboard

2. **Configure OAuth Settings**:
   - Navigate to Configuration → OAuth
   - Set Authorization Server URL: `https://ionized-crop-7678.customers.stytch.com`
   - Enable M2M (Machine-to-Machine) authentication

3. **Configure Email/Password Authentication in Stytch Dashboard**:
   - Navigate to Configuration → Passwords
   - Enable "Email and Password" authentication
   - Password requirements:
     - Minimum length: 8 characters
     - No special requirements (default is fine)
   - Enable "Allow signups" to let users create accounts
   - Save configuration

4. **Get Credentials** (Consumer Project):
   - Project ID: `project-live-2a1e5d46-f255-4175-942a-e585ac4e7c24`
   - Secret Key: `secret-live-xPTRsSg-yibk4GlqM46v6PMrXOoVUWOobQ0=`
   - Public Token: `public-token-live-b58a2742-33c6-4356-a083-879416574e5e`
   - Project Domain: `https://bumpy-puppy-0014.customers.stytch.com`
   - Project Type: **Consumer** (not B2B)

### Step 2: Deploy MCP Server

MCP server is already deployed with Stytch integration:

```bash
# Already done - MCP server running at:
https://quendoo-mcp-server-880871219885.us-central1.run.app

# Protected Resource Metadata endpoint:
https://quendoo-mcp-server-880871219885.us-central1.run.app/.well-known/oauth-protected-resource
```

### Step 3: Build and Deploy Web App

```bash
cd web-app

# Install dependencies
npm install

# Create .env file
cat > .env << EOF
REACT_APP_STYTCH_PUBLIC_TOKEN=public-token-live-37a7d963-33e1-4cea-93a2-cb97a3482f6c
REACT_APP_API_URL=https://quendoo-mcp-server-880871219885.us-central1.run.app
REACT_APP_STYTCH_PROJECT_DOMAIN=https://ionized-crop-7678.customers.stytch.com
EOF

# Build React app
npm run build

# Deploy to Cloud Run (from parent directory)
cd ..
gcloud builds submit --config web-app-cloudbuild.yaml
gcloud run deploy quendoo-web-app \
  --image gcr.io/quednoo-chatgtp-mailing/quendoo-web-app \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "DATABASE_URL=postgresql://postgres.tjrtbhemajqwzzdzyjtc:SuperSecret123!@aws-0-eu-central-1.pooler.supabase.com:6543/postgres,STYTCH_PROJECT_ID=project-live-b04e1ef7-7854-4c0d-97d0-796750c0919e,STYTCH_SECRET=secret-live-J7rQlBs578Jn9uXyXWK3pKNXQcEloTlbPOY=,STYTCH_PROJECT_DOMAIN=https://ionized-crop-7678.customers.stytch.com"
```

### Step 4: User Workflow

1. **User opens web app**: `https://quendoo-web-app-880871219885.us-central1.run.app`

2. **User signs in with Email/Password**:
   - First time: Click "Don't have an account? Sign up"
   - Enter email address and create password (min 8 characters)
   - Click "Sign Up" to create account
   - Next time: Enter email and password, click "Sign In"

3. **User enters Quendoo API key**:
   - Paste API key from Quendoo PMS dashboard
   - Click "Save API Key"
   - API key stored in database linked to Stytch user ID

4. **User connects Claude Desktop**:
   - Configure MCP server in Claude Desktop
   - OAuth flow starts automatically
   - Claude Desktop gets Stytch token
   - MCP server validates token and loads API key from database
   - User can now use Quendoo PMS tools!

### Step 5: Claude Desktop Configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "quendoo-pms": {
      "url": "https://quendoo-mcp-server-880871219885.us-central1.run.app/sse"
    }
  }
}
```

Claude Desktop will:
1. Fetch Protected Resource Metadata from `/.well-known/oauth-protected-resource`
2. Discover Stytch as authorization server
3. Start OAuth flow automatically
4. Get access token from Stytch
5. Send token in Authorization header to MCP server
6. MCP server validates token and loads user's API key

## API Endpoints

### Protected Resource Metadata
```
GET /.well-known/oauth-protected-resource
Response:
{
  "resource": "https://quendoo-mcp-server-880871219885.us-central1.run.app/",
  "authorization_servers": ["https://ionized-crop-7678.customers.stytch.com/"],
  "bearer_methods_supported": ["header"]
}
```

### Get User API Key
```
GET /api/user/api-key
Headers:
  Authorization: Bearer <stytch_token>

Response:
{
  "email": "user@example.com",
  "quendoo_api_key": "qpms_..."
}
```

### Update User API Key
```
POST /api/user/api-key
Headers:
  Authorization: Bearer <stytch_token>
  Content-Type: application/json

Body:
{
  "quendoo_api_key": "qpms_new_key..."
}

Response:
{
  "message": "API key updated successfully",
  "email": "user@example.com"
}
```

## Security

- ✅ OAuth 2.1 with PKCE
- ✅ M2M token validation
- ✅ Multi-tenant database isolation
- ✅ HTTPS only
- ✅ CORS configured
- ✅ Password hashing with bcrypt

## Troubleshooting

### Token Validation Fails
Check Stytch credentials in Cloud Run environment variables:
```bash
gcloud run services describe quendoo-mcp-server --region us-central1 --format="get(spec.template.spec.containers[0].env)"
```

### Database Connection Fails
Verify DATABASE_URL is set:
```bash
gcloud run services describe quendoo-mcp-server --region us-central1 --format="value(spec.template.spec.containers[0].env.find(name=DATABASE_URL))"
```

### Web App Can't Reach API
Check REACT_APP_API_URL in .env and rebuild:
```bash
cd web-app
cat .env
npm run build
```

## Development

### Run Locally

**MCP Server:**
```bash
python server.py
```

**Web App:**
```bash
cd web-app
npm start
```

**Flask API:**
```bash
python stytch_server.py
```

## Environment Variables

### MCP Server
```
STYTCH_PROJECT_ID=project-live-b04e1ef7-7854-4c0d-97d0-796750c0919e
STYTCH_SECRET=secret-live-J7rQlBs578Jn9uXyXWK3pKNXQcEloTlbPOY=
STYTCH_PROJECT_DOMAIN=https://ionized-crop-7678.customers.stytch.com
MCP_SERVER_URL=https://quendoo-mcp-server-880871219885.us-central1.run.app
DATABASE_URL=postgresql://...
HOST=0.0.0.0
PORT=8080
MCP_TRANSPORT=sse
```

### Web App
```
REACT_APP_STYTCH_PUBLIC_TOKEN=public-token-live-37a7d963-33e1-4cea-93a2-cb97a3482f6c
REACT_APP_API_URL=https://quendoo-mcp-server-880871219885.us-central1.run.app
REACT_APP_STYTCH_PROJECT_DOMAIN=https://ionized-crop-7678.customers.stytch.com
```

## References

- [Stytch MCP Server Guide](https://stytch.com/docs/guides/connected-apps/mcp-server-overview)
- [OAuth 2.1 RFC](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-10)
- [Protected Resource Metadata RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728)
- [MCP Specification](https://modelcontextprotocol.io/)
