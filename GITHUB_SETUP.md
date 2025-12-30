# GitHub Release Setup - Step by Step

## 🎯 Current Status

✅ All code committed and tagged (v1.0.0)
✅ README updated for release
✅ Documentation complete
✅ Ready to push to GitHub

---

## 📋 Step 1: Create GitHub Repository

1. Go to [github.com](https://github.com) and log in
2. Click the **"+"** icon in top-right corner → **"New repository"**
3. Fill in the details:
   - **Repository name**: `quendoo-mcp`
   - **Description**: `Quendoo Property Management System MCP Server with One-Click Installer`
   - **Visibility**: Choose **Public** or **Private**
   - **DO NOT** initialize with README (we already have one)
   - **DO NOT** add .gitignore or license (we have them)
4. Click **"Create repository"**

---

## 📋 Step 2: Add GitHub Remote

After creating the repository, GitHub will show you commands. Copy the repository URL and run:

```bash
cd c:\Users\Gorian\quendoo-mcp

# Add the remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/quendoo-mcp.git

# Verify remote was added
git remote -v
```

You should see:
```
origin  https://github.com/YOUR_USERNAME/quendoo-mcp.git (fetch)
origin  https://github.com/YOUR_USERNAME/quendoo-mcp.git (push)
```

---

## 📋 Step 3: Push Code to GitHub

```bash
# Push the main branch
git push -u origin main

# Push the v1.0.0 tag
git push origin v1.0.0
```

**Expected output:**
```
Enumerating objects: ..., done.
...
To https://github.com/YOUR_USERNAME/quendoo-mcp.git
 * [new branch]      main -> main
 * [new tag]         v1.0.0 -> v1.0.0
```

---

## 📋 Step 4: Create GitHub Release

1. Go to your repository on GitHub: `https://github.com/YOUR_USERNAME/quendoo-mcp`
2. Click **"Releases"** in the right sidebar (or go to `/releases`)
3. Click **"Create a new release"** or **"Draft a new release"**

### Release Details:

**Tag version:** `v1.0.0` (select from dropdown - it should exist now)

**Release title:** `v1.0.0 - Simplified Installer Edition`

**Description:** (Copy this markdown)

```markdown
# 🎉 Easy Installation with One-Click Installer

This release simplifies Quendoo MCP Server installation with a Windows installer and API key management.

## ✨ Highlights

- ✅ **One-click Windows installer** (`install.bat`)
- ✅ **API key management tools** (set, check, cleanup)
- ✅ **24-hour API key caching** for seamless usage
- ✅ **Comprehensive documentation** for easy setup
- ✅ **Local server architecture** - secure and fast

## 📦 Installation (5 minutes)

1. Download `Source code (zip)` below
2. Extract to a folder (e.g., `C:\quendoo-mcp`)
3. Run `install.bat`
4. Enter your Quendoo API key when prompted
5. Restart Claude Desktop
6. Done! 🎉

## 🔧 Requirements

- Windows 10/11
- Python 3.11+
- Claude Desktop
- Quendoo API Key

## 📚 Documentation

- [INSTALLATION.md](./INSTALLATION.md) - Complete installation guide
- [QUICK_START.md](./QUICK_START.md) - 5-minute quick start
- [FEATURES.md](./FEATURES.md) - All features and tools
- [API_KEY_SETUP.md](./API_KEY_SETUP.md) - API key management

## 🆚 What Changed from OAuth Version

### Removed
- ❌ OAuth 2.1 flow (too complex for local setup)
- ❌ Stytch integration
- ❌ Database user management
- ❌ JWT token generation

### Added
- ✅ Simple API key authentication
- ✅ Local API key caching (24h)
- ✅ API key management tools
- ✅ Windows installer
- ✅ Comprehensive documentation

### Why This Change?

The OAuth-based approach was too complex for local deployment. The new approach is **simpler**, **more reliable**, and **more secure**:
- API key stored locally (never sent to cloud)
- No external dependencies
- Easy to set up
- Each user manages their own key

## 📝 Changelog

**Added:**
- One-click installer for Windows (`install.bat`)
- API key management system with 24h cache
- Three new tools: `set_quendoo_api_key()`, `get_quendoo_api_key_status()`, `cleanup_quendoo_api_key()`
- Complete documentation suite (5 markdown files)
- Simplified `server_simple.py` without OAuth complexity

**Changed:**
- Architecture from cloud-based OAuth to local API key management
- Installation process from manual to automated
- API key storage from database to local cache + .env file

**Removed:**
- OAuth 2.1 flow and Stytch integration
- Database dependencies for user management
- JWT token generation and validation
- Complex authentication middleware

## 🐛 Known Issues

None at this time. Report issues on GitHub.

## 🙏 Acknowledgments

Built with:
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP framework
- [Quendoo API](https://quendoo.com) - Property management API
- [Claude Desktop](https://claude.ai/download) - AI assistant

---

**Full documentation:** See [README.md](./README.md)
```

4. **Attach files:** GitHub automatically includes source code. Make sure these files are included:
   - ✅ `install.bat` (most important!)
   - ✅ `server_simple.py`
   - ✅ `api_key_manager.py`
   - ✅ `requirements.txt`
   - ✅ `tools/` folder
   - ✅ All documentation files

5. **Set as latest release:** ✅ Check **"Set as the latest release"**

6. **Pre-release:** ⬜ Leave unchecked (this is a stable release)

7. Click **"Publish release"**

---

## 📋 Step 5: Update README with Correct Links

After creating the release, update the README badges with your actual GitHub username:

1. Note your GitHub username
2. Edit [README.md](./README.md) and replace `YOUR_USERNAME` with your actual username in these places:
   - Line 3: Badge link
   - Line 22: Download link
   - Line 215: Download link

Example:
```markdown
[![Latest Release](https://img.shields.io/github/v/release/gorian123/quendoo-mcp)](https://github.com/gorian123/quendoo-mcp/releases/latest)
```

3. Commit and push the change:
```bash
git add README.md
git commit -m "Update README with correct GitHub username"
git push origin main
```

---

## ✅ Step 6: Verify Release

1. Go to your repository: `https://github.com/YOUR_USERNAME/quendoo-mcp`
2. Click **"Releases"** → You should see **v1.0.0**
3. Click on the release to view it
4. Download the **"Source code (zip)"** file
5. Test it on a clean machine or VM:
   - Extract the ZIP
   - Run `install.bat`
   - Verify it works

---

## 🎉 You're Done!

Your Quendoo MCP Server is now publicly available on GitHub!

### Share the Installation Link:

```
https://github.com/YOUR_USERNAME/quendoo-mcp
```

Users can now:
1. Download the latest release
2. Run the installer
3. Start using Claude with Quendoo!

---

## 🔄 Future Releases

For v1.1.0 and beyond, follow this workflow:

1. Make changes on a new branch:
   ```bash
   git checkout -b feature/new-feature
   ```

2. Commit changes and merge to main:
   ```bash
   git checkout main
   git merge feature/new-feature
   ```

3. Tag the new version:
   ```bash
   git tag -a v1.1.0 -m "Version 1.1.0 - Description"
   git push origin main
   git push origin v1.1.0
   ```

4. Create a new release on GitHub with the new tag

---

## 🆘 Troubleshooting

### "Permission denied" when pushing
- Make sure you're logged into GitHub
- Use SSH key or Personal Access Token for authentication
- See: https://docs.github.com/en/authentication

### "Repository not found"
- Check the remote URL: `git remote -v`
- Make sure the repository exists on GitHub
- Verify you have write access

### Tag already exists
- If you need to recreate a tag:
  ```bash
  git tag -d v1.0.0
  git push origin :refs/tags/v1.0.0
  git tag -a v1.0.0 -m "New message"
  git push origin v1.0.0
  ```

---

**Need help?** Open an issue on GitHub or refer to [GitHub's documentation](https://docs.github.com/en/repositories/releasing-projects-on-github).
