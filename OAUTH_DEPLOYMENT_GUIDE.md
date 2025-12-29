# OAuth 2.1 Deployment Guide

## ✅ Completed Steps

1. ✅ Built unified MCP server with OAuth 2.1 support
2. ✅ Deployed to Cloud Run: `https://quendoo-mcp-unified-880871219885.us-central1.run.app`
3. ✅ OAuth metadata endpoint working: `/.well-known/openid-configuration`

## 📋 Next Steps

### Step 1: Update Supabase Database Schema

You need to add OAuth tables to your Supabase database.

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Click on your project: **quendoo-mcp**
3. Click **SQL Editor** in the left sidebar
4. Click **New Query**
5. Copy and paste the **entire contents** of [`schema_oauth.sql`](schema_oauth.sql)
6. Click **Run** (or press Ctrl+Enter)
7. You should see: "Success. 3 statements executed"

### Step 2: Verify Database Tables

Run this query in SQL Editor to verify:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('oauth_clients', 'authorization_codes', 'access_tokens');
```

You should see 3 rows:
- `oauth_clients`
- `authorization_codes`
- `access_tokens`

### Step 3: Configure Claude Desktop

Update your Claude Desktop config file to use OAuth 2.1:

**Location:** `C:\Users\Gorian\AppData\Roaming\Claude\claude_desktop_config.json`

**New Configuration:**

```json
{
  "mcpServers": {
    "quendoo-pms": {
      "url": "https://quendoo-mcp-unified-880871219885.us-central1.run.app/sse",
      "oauth": {
        "authorizationUrl": "https://quendoo-mcp-unified-880871219885.us-central1.run.app/oauth/authorize",
        "tokenUrl": "https://quendoo-mcp-unified-880871219885.us-central1.run.app/oauth/token",
        "clientRegistrationUrl": "https://quendoo-mcp-unified-880871219885.us-central1.run.app/oauth/register",
        "scope": "openid profile email quendoo:pms"
      }
    }
  }
}
```

### Step 4: Test OAuth Flow

1. **Restart Claude Desktop** completely (close and reopen)

2. Claude Desktop should automatically:
   - Register as an OAuth client
   - Redirect you to the authorization page
   - Ask you to login with email/password or JWT token

3. On the authorization page, you can login using:
   - **Option A:** Your JWT token from web registration (if you registered at `https://quendoo-mcp-auth-880871219885.us-central1.run.app`)
   - **Option B:** Email: `gorian@quendoo.com` and your password

4. After authorization, Claude Desktop will receive an access token

5. All PMS tools should work automatically without needing to call `set_quendoo_api_key`!

## 🔍 Troubleshooting

### Check OAuth Endpoints

```bash
# Test metadata discovery
curl https://quendoo-mcp-unified-880871219885.us-central1.run.app/.well-known/openid-configuration

# Test health check
curl https://quendoo-mcp-unified-880871219885.us-central1.run.app/health
```

### Check Logs

```bash
# View Cloud Run logs
gcloud run services logs read quendoo-mcp-unified --region us-central1 --limit 50
```

### Common Issues

**Issue:** "could not load app settings"
- **Solution:** Make sure JSON config is valid (no trailing commas)

**Issue:** OAuth redirect fails
- **Solution:** Check that database tables are created properly

**Issue:** "Invalid client_id"
- **Solution:** Delete and recreate Claude Desktop config, restart app

## 📊 OAuth Flow Diagram

```
1. Claude Desktop reads config
2. Claude Desktop calls /oauth/register → Gets client_id, client_secret
3. Claude Desktop generates code_challenge (PKCE)
4. Claude Desktop redirects browser to /oauth/authorize
5. User logs in (email/password or JWT token)
6. User authorizes application
7. Server creates authorization code
8. Server redirects back to Claude Desktop with code
9. Claude Desktop calls /oauth/token with code + code_verifier
10. Server validates and returns JWT access token
11. Claude Desktop stores token
12. All future MCP calls include: Authorization: Bearer <token>
```

## 🎉 Benefits of OAuth 2.1

✅ **One-time authentication** - No need to enter API key every 24 hours
✅ **Secure** - Uses PKCE, short-lived authorization codes
✅ **Standard** - Works with all MCP clients (Claude Desktop, Cursor, etc.)
✅ **Multi-tenant** - Each user has their own credentials
✅ **Revocable** - Can revoke tokens from database

## 🔗 Important URLs

- **MCP Server:** https://quendoo-mcp-unified-880871219885.us-central1.run.app
- **Auth Server (for web registration):** https://quendoo-mcp-auth-880871219885.us-central1.run.app
- **OAuth Metadata:** https://quendoo-mcp-unified-880871219885.us-central1.run.app/.well-known/openid-configuration
- **Authorization:** https://quendoo-mcp-unified-880871219885.us-central1.run.app/oauth/authorize
- **Token Exchange:** https://quendoo-mcp-unified-880871219885.us-central1.run.app/oauth/token
