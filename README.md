# Quendoo PMS & Communication MCP Server

Model Context Protocol (MCP) server for Quendoo Property Management System with integrated email and voice call capabilities.

## Features

### 🏨 Quendoo PMS Integration
- Property management
- Booking operations
- Availability checking
- Room and rate management

### 📧 Email Service
- Send HTML emails via Quendoo cloud function
- Customizable subject and recipients

### 📞 Voice Calls
- Automated voice calls with text-to-speech
- Bulgarian language support via Vonage/Nexmo

## Deployment

### Cloud Run (Production)

**Service URL:** `https://quendoo-mcp-server-851052272168.us-central1.run.app/sse`

Deployed to Google Cloud Run with:
- Auto-scaling
- HTTPS/SSE transport
- Environment-based configuration

### Deploy/Update

```bash
gcloud run deploy quendoo-mcp-server \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "EMAIL_API_KEY=your-key,QUENDOO_AUTOMATION_BEARER=your-token" \
  --platform managed \
  --project quendoo-mcp-prod
```

## Configuration

### Two Deployment Modes

#### Mode 1: Simple (No OAuth)
Users call `set_quendoo_api_key` tool to save API keys for 24 hours.

**Environment Variables:**
- `EMAIL_API_KEY` - API key for email cloud function
- `QUENDOO_AUTOMATION_BEARER` - Bearer token for voice calls
- `PORT` - Server port (auto-set by Cloud Run)
- `HOST` - Server host (default: 0.0.0.0)
- `MCP_TRANSPORT` - Transport protocol (default: sse)

**Claude Desktop Configuration:**
```json
{
  "mcpServers": {
    "quendoo-pms": {
      "url": "https://quendoo-mcp-server-851052272168.us-central1.run.app/sse"
    }
  }
}
```

#### Mode 2: OAuth with Database (Production)
Users register via web interface. API keys stored permanently in PostgreSQL.

**Environment Variables:**
- All from Mode 1, PLUS:
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET` - Secret key for JWT tokens (32+ chars)
- `FLASK_SECRET_KEY` - Flask session secret (32+ chars)

**Claude Desktop Configuration:**
```json
{
  "mcpServers": {
    "quendoo-pms": {
      "url": "https://quendoo-mcp-server-851052272168.us-central1.run.app/sse",
      "headers": {
        "Authorization": "Bearer YOUR_JWT_TOKEN_FROM_REGISTRATION"
      }
    }
  }
}
```

**📘 See [OAUTH_DEPLOYMENT.md](OAUTH_DEPLOYMENT.md) for complete OAuth setup guide.**

## Usage

### 1. Set Your API Key (First Time)

```
User: "Set my Quendoo API key: abc123xyz456"
Claude: ✅ Quendoo API key saved successfully for 24 hours!
```

### 2. Use PMS Features

```
User: "Show me all my properties"
Claude: [Lists properties using your saved API key]
```

### 3. Send Emails

```
User: "Send email to guest@example.com with subject 'Booking Confirmation'"
Claude: [Sends HTML email via cloud function]
```

### 4. Make Voice Calls

```
User: "Call +359888123456 and say 'Your booking is confirmed for tomorrow at 2pm'"
Claude: [Initiates automated voice call]
```

## API Key Management

### Per-Client Storage
- API keys are stored per-client for 24 hours
- No need to re-enter after initial setup
- Automatic expiration and cleanup

### Important Notes
- **Global fallback:** If MCP doesn't provide `client_id`, API keys are shared across clients on the same container
- **Acceptable for small-scale:** Cloud Run scales to multiple containers, reducing conflicts
- **24-hour TTL:** Keys automatically expire after 24 hours

### Tools

- `set_quendoo_api_key(api_key)` - Store PMS API key
- `clear_quendoo_api_key()` - Remove stored key
- `set_email_api_key(api_key)` - Store email API key (if different)
- `clear_email_api_key()` - Remove email key

## Architecture

```
Claude Desktop
    ↓ (SSE)
Google Cloud Run (MCP Server)
    ↓
    ├─→ Quendoo PMS API (properties, bookings, availability)
    ├─→ Email Cloud Function (send_quendoo_email)
    └─→ Voice Cloud Function (make_call → Vonage)
```

## Development

### Local Setup

```bash
# Install dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your keys

# Run locally
python server.py
```

### Project Structure

```
quendoo-mcp/
├── server.py              # Main MCP server
├── tools/
│   ├── api_keys.py       # Per-client API key management
│   ├── auth.py           # Authentication tools
│   ├── client.py         # Quendoo HTTP client
│   ├── property.py       # Property management tools
│   ├── booking.py        # Booking tools
│   ├── availability.py   # Availability tools
│   ├── email.py          # Email sending tools
│   └── automation.py     # Voice call tools
├── Dockerfile            # Cloud Run container
└── requirements.txt      # Python dependencies
```

## Security

- API keys stored in memory only (not persisted)
- 24-hour automatic expiration
- HTTPS/SSE encrypted transport
- Bearer token auth for cloud functions
- No keys logged or exposed in responses

## Support

For issues or questions:
- Check Cloud Run logs: `gcloud logging read "resource.type=cloud_run_revision"`
- Verify environment variables are set correctly
- Ensure API keys are valid and not expired

## License

Proprietary - Quendoo PMS Integration
