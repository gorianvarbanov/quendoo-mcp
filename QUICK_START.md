# Quendoo MCP Server - Quick Start Guide

## 📦 Installation (5 minutes)

### 1. Prerequisites
- ✅ Windows 10/11
- ✅ Python 3.11+ ([Download](https://www.python.org/downloads/))
- ✅ Claude Desktop ([Download](https://claude.ai/download))
- ✅ Quendoo API Key (from your dashboard)

### 2. Install

**Option A: Automatic (Recommended)**
```cmd
1. Download quendoo-mcp folder
2. Double-click install.bat
3. Follow prompts
```

**Option B: Manual**
```bash
cd quendoo-mcp
pip install -r requirements.txt
python api_key_manager.py set YOUR_API_KEY
```

Then edit `claude_desktop_config.json` - see [INSTALLATION.md](./INSTALLATION.md)

### 3. Verify

Restart Claude Desktop and ask:
```
Check my Quendoo API key status
```

---

## 🎯 First Steps

### 1. Set Your API Key (if skipped during install)

Tell Claude:
```
Set my Quendoo API key to: YOUR_KEY_HERE
```

### 2. Check Property Availability

```
Show me availability for March 2025
```

### 3. Get Room Details

```
What rooms do we have available?
```

### 4. Get Property Settings

```
Show me our property settings
```

---

## 🔑 Common Commands

### API Key Management
```
# Check status
Check my API key status

# Update key
Set my API key to: NEW_KEY

# Clear cache
Clear my API key
```

### Property Queries
```
# Availability
Show availability for April 2025
What's available next week?

# Rooms
List all rooms
Show room 2666 details

# Bookings
Show all bookings
Get booking #12345
```

### Email & Calls
```
# Send email
Send email to guest@example.com with subject "Confirmation"

# Make voice call
Call +359888123456 with message "Your booking is confirmed"
```

---

## ⚙️ Configuration

### API Key Storage

Your API key is stored in two places:

1. **Cache** (24h): `~/.quendoo_api_key_cache.json`
2. **Permanent**: `quendoo-mcp/.env`

### Claude Desktop Config

Location: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "quendoo-pms": {
      "command": "C:\\Path\\To\\Python\\python.exe",
      "args": ["C:\\Path\\To\\quendoo-mcp\\server_simple.py"]
    }
  }
}
```

---

## 🐛 Troubleshooting

### Issue: Server not connecting

**Check:**
1. Python is in PATH: `python --version`
2. Dependencies installed: `pip list | findstr mcp`
3. Config file exists: `%APPDATA%\Claude\claude_desktop_config.json`
4. Claude Desktop restarted

### Issue: API key expired

**Solution:**
```
Set my API key to: YOUR_KEY
```

API keys expire after 24h. Just set it again.

### Issue: "Module not found" error

**Solution:**
```bash
cd quendoo-mcp
pip install -r requirements.txt
```

---

## 📚 Next Steps

- 📖 Read [FEATURES.md](./FEATURES.md) for all available features
- 🔧 Check [INSTALLATION.md](./INSTALLATION.md) for detailed setup
- 🔑 See [API_KEY_SETUP.md](./API_KEY_SETUP.md) for key management

---

## 🎉 You're Ready!

Your Quendoo MCP server is now running locally. Ask Claude anything about:
- Property availability
- Room management
- Bookings
- Email sending
- Voice calls

Enjoy! 🚀
