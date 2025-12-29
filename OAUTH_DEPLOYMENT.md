# OAuth Deployment Guide

This guide explains how to deploy the Quendoo MCP server with full OAuth authentication and database-backed API key storage.

## Architecture

```
User → Web Registration → PostgreSQL Database (stores API keys)
          ↓
    JWT Token Generated
          ↓
Claude Desktop (with token) → MCP Server → Validates JWT → Loads API keys from DB
```

## Prerequisites

1. Google Cloud project with billing enabled
2. `gcloud` CLI installed and configured
3. PostgreSQL database (Cloud SQL or external)

## Step 1: Set Up PostgreSQL Database

### Option A: Google Cloud SQL (Recommended)

```bash
# Create Cloud SQL instance
gcloud sql instances create quendoo-mcp-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=YOUR_STRONG_PASSWORD

# Create database
gcloud sql databases create quendoo_mcp \
  --instance=quendoo-mcp-db

# Get connection string
gcloud sql instances describe quendoo-mcp-db --format="value(connectionName)"
# Output: project:region:instance-name
```

### Option B: Supabase (Free Tier Available)

1. Go to [supabase.com](https://supabase.com)
2. Create new project
3. Go to Settings → Database → Connection String
4. Copy the connection string (format: `postgresql://...`)

### Initialize Database Schema

```bash
# Connect to your database and run schema.sql
psql "your-connection-string" < schema.sql
```

## Step 2: Deploy Authentication Web Server

The auth server handles user registration and login.

### Create Dockerfile for Auth Server

```dockerfile
# Dockerfile.auth
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY auth_server.py .
COPY templates/ templates/
COPY tools/database.py tools/
COPY tools/jwt_auth.py tools/
COPY tools/__init__.py tools/

ENV HOST=0.0.0.0
ENV AUTH_PORT=8080

EXPOSE 8080

CMD ["python", "auth_server.py"]
```

### Deploy Auth Server to Cloud Run

```bash
# Build and deploy
gcloud run deploy quendoo-mcp-auth \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "DATABASE_URL=your-postgres-connection-string,JWT_SECRET=your-random-secret-key,FLASK_SECRET_KEY=another-random-secret" \
  --platform managed

# Get the URL
gcloud run services describe quendoo-mcp-auth --region us-central1 --format="value(status.url)"
# Example output: https://quendoo-mcp-auth-851052272168.us-central1.run.app
```

**Important:** Generate strong random secrets:
```bash
# Generate JWT_SECRET
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate FLASK_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Step 3: Deploy MCP Server with OAuth

```bash
gcloud run deploy quendoo-mcp-server \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "\
DATABASE_URL=your-postgres-connection-string,\
JWT_SECRET=same-as-auth-server,\
EMAIL_API_KEY=your-email-key,\
QUENDOO_AUTOMATION_BEARER=your-automation-bearer,\
AUTH_ISSUER_URL=https://quendoo-mcp-auth-YOUR-ID.us-central1.run.app,\
AUTH_RESOURCE_URL=https://quendoo-mcp-server-YOUR-ID.us-central1.run.app" \
  --platform managed \
  --project YOUR-PROJECT-ID
```

**Critical:** Use the same `JWT_SECRET` for both auth and MCP servers!

## Step 4: User Registration Flow

### 1. User Registers

Visit: `https://quendoo-mcp-auth-YOUR-ID.us-central1.run.app/register`

Fill in:
- Email address
- Password
- Quendoo API Key (from Quendoo dashboard)
- Email API Key (optional)

After registration, copy the JWT token displayed.

### 2. Configure Claude Desktop

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "quendoo-pms": {
      "url": "https://quendoo-mcp-server-851052272168.us-central1.run.app/sse",
      "headers": {
        "Authorization": "Bearer YOUR_JWT_TOKEN_HERE"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

The MCP server will:
1. Validate the JWT token
2. Extract user_id from the token
3. Load Quendoo API key from database
4. All PMS tools work automatically - no need to call `set_quendoo_api_key`

## Step 5: Verify Deployment

### Test Auth Server

```bash
# Test registration
curl -X POST https://quendoo-mcp-auth-YOUR-ID.us-central1.run.app/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123",
    "quendoo_api_key": "your-test-key"
  }'

# Should return: {"token": "eyJ...", "user_id": 1, ...}
```

### Test MCP Server

```bash
# Test with JWT token
curl https://quendoo-mcp-server-YOUR-ID.us-central1.run.app/sse \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Should return: SSE connection or tool list
```

## Environment Variables Reference

### Auth Server (`quendoo-mcp-auth`)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `JWT_SECRET` | Yes | Secret key for JWT signing (32+ chars) |
| `FLASK_SECRET_KEY` | Yes | Flask session secret (32+ chars) |
| `AUTH_PORT` | No | Server port (default: 8080) |

### MCP Server (`quendoo-mcp-server`)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string (same as auth) |
| `JWT_SECRET` | Yes | JWT secret (MUST match auth server) |
| `EMAIL_API_KEY` | Yes | Email cloud function API key |
| `QUENDOO_AUTOMATION_BEARER` | Yes | Voice call bearer token |
| `AUTH_ISSUER_URL` | No | Auth server URL (for validation) |
| `AUTH_RESOURCE_URL` | No | MCP server URL (for validation) |
| `PORT` | No | Auto-set by Cloud Run |
| `HOST` | No | Default: 0.0.0.0 |
| `MCP_TRANSPORT` | No | Default: sse |

## Security Best Practices

1. **Strong Secrets**: Use 32+ character random strings for JWT_SECRET and FLASK_SECRET_KEY
2. **HTTPS Only**: Both servers use HTTPS via Cloud Run
3. **Database Access**: Use Cloud SQL with private IP or restrict access by IP
4. **Token Expiration**: JWT tokens expire after 30 days
5. **Password Hashing**: bcrypt with salt (automatically handled)

## Troubleshooting

### "Invalid or expired token"

- Verify `JWT_SECRET` matches on both servers
- Check token hasn't expired (30-day limit)
- Ensure user exists in database

### "Failed to load profile"

- Check `DATABASE_URL` is correct
- Verify database is accessible from Cloud Run
- Check Cloud SQL connection settings

### "QUENDOO_API_KEY is not set"

- User hasn't registered with API key
- Database connection failed
- Token doesn't contain valid user_id

## Cost Estimates

**Google Cloud (Monthly)**
- Cloud Run (Auth): $0-5 (free tier covers most usage)
- Cloud Run (MCP): $0-5 (free tier covers most usage)
- Cloud SQL (db-f1-micro): ~$10

**Supabase**
- Free tier: 500MB database, 2GB bandwidth (sufficient for most users)
- Pro tier: $25/month if you exceed free limits

## Rollback to Non-OAuth Mode

If you need to revert to the old system without OAuth:

1. Remove `DATABASE_URL` from MCP server environment variables
2. Users will use `set_quendoo_api_key` tool again (24-hour cache)
3. Auth server can remain deployed for future use

## Support

For issues:
- Check Cloud Run logs: `gcloud logging read "resource.type=cloud_run_revision"`
- Verify environment variables: `gcloud run services describe SERVICE_NAME --format=yaml`
- Test database connection: `psql "your-connection-string" -c "SELECT 1"`
