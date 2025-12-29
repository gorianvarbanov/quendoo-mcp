# Which Mode Should You Use?

Quick guide to help you decide between Simple and OAuth modes.

## Quick Comparison

| Feature | Simple Mode | OAuth Mode |
|---------|-------------|------------|
| **Setup Time** | 5 minutes | 30 minutes |
| **Database Required** | ❌ No | ✅ Yes (PostgreSQL) |
| **API Key Entry** | Every 24 hours | Once (registration) |
| **Multi-tenant** | Global cache | Isolated per user |
| **Monthly Cost** | ~$0-5 | ~$10-15 |
| **User Experience** | Tell Claude API key | Register on web |
| **Security** | Basic | Production-grade |

## Decision Tree

```
START: How many users will use your MCP server?

├─ Just me (1 user)
│  └─ Use Simple Mode ✓
│     • No database needed
│     • Quick setup
│     • Re-enter key every 24h (no big deal)
│     • Already deployed!
│
├─ 2-5 users (small team)
│  ├─ Do you mind re-entering API key daily?
│  │  ├─ No → Simple Mode ✓
│  │  └─ Yes → OAuth Mode ✓
│  │
│  └─ Do users need isolated API keys?
│     ├─ No (can share) → Simple Mode ✓
│     └─ Yes (separate hotels) → OAuth Mode ✓
│
└─ 5+ users (multiple properties/hotels)
   └─ Use OAuth Mode ✓
      • Each user has own API key
      • Professional setup
      • No daily re-entry
```

## Use Simple Mode If:

- ✅ You're the only user
- ✅ Small team that can share API keys
- ✅ Don't mind calling `set_quendoo_api_key` daily
- ✅ Want to start quickly (already deployed!)
- ✅ Budget-conscious (save ~$10/month)

**Current Status:** ✅ Already deployed and working!

## Use OAuth Mode If:

- ✅ Multiple users with different hotels
- ✅ Need true multi-tenant isolation
- ✅ Want professional authentication
- ✅ Don't want to re-enter API key
- ✅ Building a product/service

**Current Status:** 📦 Ready to deploy (see OAUTH_DEPLOYMENT.md)

## My Recommendation

Based on your situation, I recommend:

### Start with Simple Mode (Current)
- It's already deployed and working
- You can test and validate everything
- No additional setup needed

### Upgrade to OAuth Later (Optional)
- When you have multiple users
- When daily API key entry becomes annoying
- When you want production-grade security

The beauty: **You can switch anytime!**
- Both modes are fully implemented
- No code changes needed
- Just deploy with different environment variables

## Quick Start Commands

### Continue with Simple Mode (No Action Needed)
Already deployed! Just use it:

```
Claude Desktop → MCP Server
User: "Set my Quendoo API key: abc123"
User: "Show my properties"
✓ Works!
```

### Deploy OAuth Mode
```bash
# 1. Set up database
psql "your-db-url" < schema.sql

# 2. Deploy
chmod +x deploy_oauth.sh
./deploy_oauth.sh

# 3. Register
Visit: https://auth-server-url/register
```

## Cost Breakdown

### Simple Mode
- Cloud Run (MCP Server): $0-5/month
- **Total: $0-5/month**

### OAuth Mode
- Cloud Run (MCP Server): $0-5/month
- Cloud Run (Auth Server): $0-5/month
- Cloud SQL (PostgreSQL): $10/month
- **OR Supabase (PostgreSQL): FREE**
- **Total: $0-10/month with Supabase**
- **Total: $10-15/month with Cloud SQL**

## What I Would Do

If I were you:

1. **Today:** Keep using Simple Mode
   - It's working perfectly
   - No setup needed
   - Validate your workflow

2. **If/When:**
   - You get more users → Deploy OAuth
   - Daily API key entry annoys you → Deploy OAuth
   - You want to productionize → Deploy OAuth

3. **Deployment:** Use Supabase for free database
   - Keeps OAuth mode at ~$0-5/month
   - Same cost as Simple mode!

## Questions to Ask Yourself

**"Do I need OAuth right now?"**
- No → Stick with Simple Mode
- Yes → Follow OAUTH_DEPLOYMENT.md

**"Will I have multiple users soon?"**
- No → Simple Mode is fine
- Yes → Plan OAuth deployment

**"Is re-entering API key daily annoying?"**
- No → Simple Mode works
- Yes → Deploy OAuth

## Summary

```
┌────────────────────────────────────────────────────┐
│  Simple Mode: Currently deployed ✓                 │
│  • Works great for 1-5 users                       │
│  • No additional cost                              │
│  • Re-enter API key every 24h                      │
│                                                     │
│  OAuth Mode: Ready to deploy 📦                    │
│  • Best for 5+ users                               │
│  • ~$0-15/month depending on database              │
│  • Enter API key once during registration          │
│                                                     │
│  Recommendation: Start Simple, upgrade later       │
└────────────────────────────────────────────────────┘
```

## Need Help Deciding?

Consider:
- **Number of users:** 1-5 = Simple, 5+ = OAuth
- **Budget:** Free = Simple, $10-15 = OAuth
- **Time to deploy:** 0 min = Simple, 30 min = OAuth
- **API key re-entry:** Daily = Simple, Never = OAuth

**Still unsure?** → Start with Simple Mode (already working!)
