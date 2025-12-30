# Quendoo MCP Server

[![Latest Release](https://img.shields.io/github/v/release/gorianvarbanov/quendoo-mcp)](https://github.com/gorianvarbanov/quendoo-mcp/releases/latest)

**One-click installer for Quendoo Property Management System integration with Claude Desktop**

Model Context Protocol (MCP) server for Quendoo PMS with integrated email and voice call capabilities.

## ✨ Features

- 🏨 **Property Management** - Manage properties, rooms, rates
- 📅 **Availability Checking** - Real-time availability queries
- 📦 **Booking Operations** - Create, view, manage bookings
- 📧 **Email Service** - Send HTML emails to guests
- 📞 **Voice Calls** - Automated voice calls with text-to-speech
- 🔑 **API Key Management** - Secure 24-hour API key caching

## 🚀 Quick Start

### Windows Installation (5 minutes)

1. **Download** the [latest release](https://github.com/gorianvarbanov/quendoo-mcp/releases/latest)
2. **Extract** to a folder (e.g., `C:\quendoo-mcp`)
3. **Run** `install.bat`
4. **Enter** your Quendoo API key when prompted
5. **Restart** Claude Desktop
6. **Done!** 🎉

For detailed instructions, see [INSTALLATION.md](./INSTALLATION.md) or [QUICK_START.md](./QUICK_START.md)

### Verify Installation

Open Claude Desktop and ask:
```
Check my Quendoo API key status
```

---

## 📚 Documentation

- **[QUICK_START.md](./QUICK_START.md)** - Get started in 5 minutes
- **[INSTALLATION.md](./INSTALLATION.md)** - Detailed installation guide
- **[FEATURES.md](./FEATURES.md)** - Complete feature documentation
- **[API_KEY_SETUP.md](./API_KEY_SETUP.md)** - API key management guide
- **[RELEASE_NOTES.md](./RELEASE_NOTES.md)** - Version history

---

## 🔧 Requirements

- **Windows 10/11** (Mac/Linux coming soon)
- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Claude Desktop** ([Download](https://claude.ai/download))
- **Quendoo API Key** (from your Quendoo dashboard)

---

## 💡 Usage Examples

### Check API Key Status
```
Check my Quendoo API key status
```

### Query Availability
```
Show me availability for March 2025
```

### Get Room Details
```
What rooms do we have?
```

### Send Email
```
Send email to guest@example.com with subject "Booking Confirmation"
```

### Make Voice Call
```
Call +359888123456 and say "Your booking is confirmed"
```

---

## 🏗️ Architecture

**Local Server (Recommended)**
```
Claude Desktop → server_simple.py (local) → Quendoo API
                    ↓
               API Key Cache (24h)
                    ↓
                 .env file
```

**Benefits:**
- ✅ Simple setup
- ✅ Secure (keys stay local)
- ✅ Fast (no network hop)
- ✅ Each user has own API key

---

## 🔐 Security

- API keys stored locally in `.env` and cache file
- 24-hour automatic cache expiration
- Keys never committed to git (protected by `.gitignore`)
- No cloud storage of sensitive data

---

## 📦 What's Included

- `install.bat` - One-click Windows installer
- `server_simple.py` - Main MCP server
- `api_key_manager.py` - API key management with caching
- `tools/` - Complete Quendoo API integration
- Documentation - Complete setup and usage guides

---

## 🔄 API Key Management Tools

Available via Claude:

- `set_quendoo_api_key(api_key)` - Set your API key (cached for 24h)
- `get_quendoo_api_key_status()` - Check API key status and expiry
- `cleanup_quendoo_api_key()` - Remove cached API key

See [API_KEY_SETUP.md](./API_KEY_SETUP.md) for details.

---

## 🛠️ Development

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Set your API key
python api_key_manager.py set YOUR_API_KEY

# Test the server
python server_simple.py
```

### Project Structure

```
quendoo-mcp/
├── install.bat                  # Windows installer
├── server_simple.py             # Main MCP server
├── api_key_manager.py           # API key management
├── tools/                       # Quendoo API integration
│   ├── client.py               # Quendoo HTTP client
│   ├── property.py             # Property tools
│   ├── booking.py              # Booking tools
│   ├── availability.py         # Availability tools
│   ├── email.py                # Email tools
│   └── automation.py           # Voice call tools
└── requirements.txt            # Python dependencies
```

---

## 🐛 Troubleshooting

### Server not connecting?
1. Check Python is installed: `python --version`
2. Verify Claude Desktop config: `%APPDATA%\Claude\claude_desktop_config.json`
3. Restart Claude Desktop

### API key expired?
```
Set my API key to: YOUR_NEW_KEY
```

### Need more help?
- See [INSTALLATION.md](./INSTALLATION.md) for detailed troubleshooting
- Check [QUICK_START.md](./QUICK_START.md) for common issues

---

## 📝 Version History

See [RELEASE_NOTES.md](./RELEASE_NOTES.md) for detailed changelog.

**Current Version:** v1.0.0 - Simplified Installer Edition

---

## 🙏 Acknowledgments

Built with:
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP framework
- [Quendoo API](https://quendoo.com) - Property management API
- [Claude Desktop](https://claude.ai/download) - AI assistant

---

## 📄 License

[Add your license here]

---

## 🚀 Ready to Get Started?

1. [Download the latest release](https://github.com/gorianvarbanov/quendoo-mcp/releases/latest)
2. Run `install.bat`
3. Start using Claude with your Quendoo data!

**Questions?** Check the [documentation](./INSTALLATION.md) or open an issue.
