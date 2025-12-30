# Quendoo MCP Server - Installation Guide

## 📋 Prerequisites

Before installing, make sure you have:

1. **Python 3.11 or higher** installed
   - Download from: https://www.python.org/downloads/
   - ⚠️ **Important**: Check "Add Python to PATH" during installation

2. **Claude Desktop** installed
   - Download from: https://claude.ai/download

3. **Quendoo API Key**
   - Get it from your Quendoo dashboard
   - You can set it up during or after installation

---

## 🚀 Quick Install (Windows)

### Step 1: Download

Download or clone this repository:
```bash
git clone https://github.com/your-repo/quendoo-mcp.git
cd quendoo-mcp
```

Or download as ZIP and extract to a folder (e.g., `C:\quendoo-mcp`)

### Step 2: Run Installer

Double-click `install.bat` or run in Command Prompt:
```cmd
install.bat
```

The installer will:
1. ✅ Check Python installation
2. ✅ Install all dependencies
3. ✅ Ask for your Quendoo API key (optional)
4. ✅ Configure Claude Desktop automatically

### Step 3: Restart Claude Desktop

1. Close all Claude Desktop windows
2. Reopen Claude Desktop
3. The Quendoo PMS server should now be available!

---

## 🔧 Manual Installation

If you prefer manual setup:

### 1. Install Dependencies

```bash
cd c:\Users\Gorian\quendoo-mcp
pip install -r requirements.txt
```

### 2. Set API Key

Choose one method:

**Method A: Via CLI**
```bash
python api_key_manager.py set YOUR_API_KEY_HERE
```

**Method B: Via .env file**
1. Open `.env` file
2. Add line: `QUENDOO_API_KEY=YOUR_API_KEY_HERE`
3. Save

**Method C: Via Claude (after setup)**
Tell Claude: `Set my Quendoo API key to: YOUR_KEY_HERE`

### 3. Configure Claude Desktop

Edit `C:\Users\YOUR_USERNAME\AppData\Roaming\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "quendoo-pms": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python313\\python.exe",
      "args": ["c:\\Users\\Gorian\\quendoo-mcp\\server_simple.py"]
    }
  }
}
```

**Important**: Replace paths with your actual paths:
- Python path: Run `where python` in Command Prompt
- Server path: Full path to `server_simple.py`

### 4. Restart Claude Desktop

---

## ✅ Verify Installation

After restarting Claude Desktop, test with these commands:

1. **Check API key status:**
   ```
   Check my Quendoo API key status
   ```

2. **Test availability query:**
   ```
   Show me availability for March 2025
   ```

3. **List available tools:**
   ```
   What Quendoo tools are available?
   ```

---

## 🔑 API Key Management

### Set/Update API Key

Tell Claude:
```
Set my Quendoo API key to: YOUR_NEW_KEY
```

### Check Status

```
Check my API key status
```

Response will show:
- ✅ Valid/Invalid
- 🕐 Expiry time (24h cache)
- ⏱️ Time remaining

### Clear API Key

```
Clear my Quendoo API key
```

---

## 🐛 Troubleshooting

### Issue: "Python not found"

**Solution:**
1. Install Python from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"
3. Restart Command Prompt and try again

### Issue: "MCP server not showing in Claude"

**Solutions:**
1. Verify `claude_desktop_config.json` exists in:
   ```
   C:\Users\YOUR_USERNAME\AppData\Roaming\Claude\
   ```

2. Check Python path is correct:
   ```cmd
   where python
   ```

3. Verify server path is correct (use full path, not relative)

4. Restart Claude Desktop completely (close all windows)

### Issue: "API key expired"

**Solution:**
Set a new API key:
```
Set my Quendoo API key to: YOUR_KEY
```

API keys are cached for 24 hours. After expiry, just set it again.

### Issue: "Dependencies installation failed"

**Solution:**
Try upgrading pip first:
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## 📂 File Structure

```
quendoo-mcp/
├── install.bat              # Windows installer
├── server_simple.py         # Main MCP server
├── api_key_manager.py       # API key management
├── requirements.txt         # Python dependencies
├── tools/                   # Quendoo API tools
│   ├── client.py           # Quendoo API client
│   └── ...
├── .env                     # Local configuration
└── README.md               # Documentation
```

---

## 🔄 Updating

To update to the latest version:

1. **Pull latest changes:**
   ```bash
   cd c:\Users\Gorian\quendoo-mcp
   git pull
   ```

2. **Update dependencies:**
   ```bash
   pip install -r requirements.txt --upgrade
   ```

3. **Restart Claude Desktop**

---

## 🆘 Support

If you encounter issues:

1. Check the [Troubleshooting](#-troubleshooting) section
2. Review [FEATURES.md](./FEATURES.md) for feature documentation
3. Check [API_KEY_SETUP.md](./API_KEY_SETUP.md) for API key help

---

## 🎯 What's Next?

Once installed, you can:

- ✅ Query property availability
- ✅ Manage bookings
- ✅ Get room details
- ✅ Send emails
- ✅ Make automated voice calls

Tell Claude: `Show me what Quendoo features are available`
