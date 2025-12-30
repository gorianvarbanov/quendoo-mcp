# Deployment Guide

## Production vs Development Projects

### 🚀 PRODUCTION (Live Users)
- **Project**: `quendoo-mcp-prod`
- **Region**: `us-central1`
- **Service Name**: `quendoo-mcp-server`
- **URL**: `https://quendoo-mcp-server-urxohjcmba-uc.a.run.app/sse`
- **Deploy Command**:
  ```bash
  gcloud run deploy quendoo-mcp-server --source . --region us-central1 --allow-unauthenticated --project quendoo-mcp-prod
  ```

### 🧪 DEVELOPMENT/TEST
- **Project**: `quednoo-chatgtp-mailing`
- **Services**:
  - `quendoo-mcp-server` (us-central1)
  - `quendoo-mcp-unified` (us-central1)

---

## Quick Deploy to Production

```bash
# 1. Make sure you're in the project directory
cd c:\Users\Gorian\quendoo-mcp

# 2. Set the production project
gcloud config set project quendoo-mcp-prod

# 3. Deploy to production
gcloud run deploy quendoo-mcp-server --source . --region us-central1 --allow-unauthenticated --project quendoo-mcp-prod

# 4. Verify deployment
curl -s "https://quendoo-mcp-server-urxohjcmba-uc.a.run.app/sse" -I | head -5
```

---

## What Gets Deployed

The deployment includes:
- `server_simple.py` - Main MCP server
- `tools/` - All Quendoo API integration tools
- `api_key_manager.py` - API key management
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container configuration

**Environment variables are configured in Cloud Run console, NOT from .env file!**

---

## Important Notes

⚠️ **ALWAYS deploy to production project for live users**
- Production URL: `https://quendoo-mcp-server-urxohjcmba-uc.a.run.app/sse`
- Project: `quendoo-mcp-prod`

✅ **Test in development first**
- Dev project: `quednoo-chatgtp-mailing`
- Test changes before deploying to production

🔒 **Security**
- API keys are managed via Cloud Run environment variables
- Never commit secrets to git
- Use `.gitignore` to exclude sensitive files

---

## Deployment History

### 2025-12-30 - Fixed get_booking_offers endpoint
- Changed endpoint from `/Booking/getBookingOffers` to `/Property/getBookingOffers`
- Changed HTTP method from POST to GET
- Added URL parameter format for guests
- Added auto-detection of first active booking module
- **Production Revision**: `quendoo-mcp-server-00003-wk5`
- **Deployed at**: 20:45:27 UTC
