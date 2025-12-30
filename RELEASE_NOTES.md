# Release Notes - v1.0.0 - Simplified Installer Edition

## 🎉 What's New

### Easy Installation
- **One-click Windows installer** (`install.bat`)
- Automatic dependency installation
- Automatic Claude Desktop configuration
- Interactive API key setup

### Simplified Architecture
- **Local MCP server** (no OAuth complexity)
- **API key management tools** (set, check, cleanup)
- **24-hour API key caching**
- **Tenant-based design** (each user manages their own API key)

### New Features
- ✅ `set_quendoo_api_key()` - Set API key from Claude
- ✅ `get_quendoo_api_key_status()` - Check API key status
- ✅ `cleanup_quendoo_api_key()` - Remove cached API key
- ✅ Automatic fallback to `.env` file

### Documentation
- 📖 **INSTALLATION.md** - Complete installation guide
- 📖 **QUICK_START.md** - 5-minute quick start
- 📖 **FEATURES.md** - Full feature documentation
- 📖 **API_KEY_SETUP.md** - API key management guide

---

## 📦 Installation

### Quick Install (Windows)

1. Download the latest release
2. Extract to a folder (e.g., `C:\quendoo-mcp`)
3. Run `install.bat`
4. Enter your Quendoo API key when prompted
5. Restart Claude Desktop

**That's it!** 🎉

### Manual Install

```bash
pip install -r requirements.txt
python api_key_manager.py set YOUR_API_KEY
# Edit claude_desktop_config.json (see INSTALLATION.md)
```

---

## 🔧 Requirements

- Windows 10/11
- Python 3.11+
- Claude Desktop
- Quendoo API Key

---

## 🚀 Usage

After installation, tell Claude:

```
# Check setup
Check my Quendoo API key status

# Query availability
Show me availability for March 2025

# Get room details
What rooms do we have?

# Send email
Send email to guest@example.com with subject "Welcome"
```

---

## 🆚 Changes from Previous Version

### Removed
- ❌ OAuth 2.1 flow (too complex for local setup)
- ❌ Stytch integration
- ❌ Database user management
- ❌ JWT token generation
- ❌ local_client.py proxy (for OAuth)

### Added
- ✅ Simple API key authentication
- ✅ Local API key caching (24h)
- ✅ API key management tools
- ✅ Windows installer
- ✅ Comprehensive documentation

### Why This Change?

The OAuth-based approach was too complex for local deployment:
- Required browser redirects
- Needed database for user management
- Complex token validation
- Difficult troubleshooting

The new approach is **simpler** and **more reliable**:
- API key stored locally (secure)
- No external dependencies
- Easy to set up
- Each user manages their own key

---

## 🐛 Known Issues

None at this time. Report issues on GitHub.

---

## 🔮 Future Plans

- Mac/Linux installer scripts
- GUI installer
- Auto-update mechanism
- Proxy mode for Cloud Run (optional)

---

## 📚 Documentation

- [INSTALLATION.md](./INSTALLATION.md) - Full installation guide
- [QUICK_START.md](./QUICK_START.md) - Quick start guide
- [FEATURES.md](./FEATURES.md) - Feature documentation
- [API_KEY_SETUP.md](./API_KEY_SETUP.md) - API key management

---

## 👥 Contributors

- Gorian (with Claude Code assistance)

---

## 📄 License

[Your License Here]

---

## 🙏 Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- Powered by [Quendoo API](https://quendoo.com)
- Uses [Claude Desktop](https://claude.ai/download)
