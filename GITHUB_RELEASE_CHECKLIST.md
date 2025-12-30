# GitHub Release Checklist

## 📋 Pre-Release Steps

### 1. Create GitHub Repository

If you haven't already:

```bash
# Go to github.com and create new repository
# Name: quendoo-mcp
# Description: Quendoo PMS MCP Server with Installer
# Public or Private: [Your choice]
```

### 2. Add Remote and Push

```bash
cd c:\Users\Gorian\quendoo-mcp

# Add GitHub remote (replace with your URL)
git remote add origin https://github.com/YOUR_USERNAME/quendoo-mcp.git

# Push code
git push -u origin main

# Push tags
git push origin v1.0.0
```

---

## 🚀 Creating the Release on GitHub

### Step 1: Go to Releases

1. Go to your repository on GitHub
2. Click "Releases" (right sidebar)
3. Click "Create a new release"

### Step 2: Tag and Title

- **Tag**: `v1.0.0`
- **Target**: `main`
- **Release title**: `v1.0.0 - Simplified Installer Edition`

### Step 3: Description

Copy from [RELEASE_NOTES.md](./RELEASE_NOTES.md) or use this:

```markdown
# 🎉 Easy Installation with One-Click Installer

This release simplifies Quendoo MCP Server installation with:

## ✨ Highlights

- ✅ **One-click Windows installer** (`install.bat`)
- ✅ **API key management tools** (set, check, cleanup)
- ✅ **24-hour API key caching**
- ✅ **Comprehensive documentation**

## 📦 Installation

1. Download `quendoo-mcp.zip` below
2. Extract to a folder
3. Run `install.bat`
4. Enter your Quendoo API key
5. Restart Claude Desktop

## 📚 Documentation

- [INSTALLATION.md](./INSTALLATION.md) - Full guide
- [QUICK_START.md](./QUICK_START.md) - 5-minute start
- [FEATURES.md](./FEATURES.md) - All features

## 🔧 Requirements

- Windows 10/11
- Python 3.11+
- Claude Desktop
- Quendoo API Key
```

### Step 4: Attach Files

**Option A: ZIP the entire repository**

```bash
# Create release ZIP (exclude unnecessary files)
git archive --format=zip --output=quendoo-mcp-v1.0.0.zip v1.0.0
```

**Option B: Manual ZIP**

Create a ZIP with:
```
quendoo-mcp/
├── install.bat              ← Most important!
├── server_simple.py
├── api_key_manager.py
├── requirements.txt
├── tools/
├── INSTALLATION.md
├── QUICK_START.md
├── FEATURES.md
├── API_KEY_SETUP.md
└── README.md
```

**DO NOT include:**
- `.env` (contains secrets!)
- `.quendoo_api_key_cache.json`
- `jwt_key.txt`
- `__pycache__/`
- `.git/`

### Step 5: Pre-release or Latest

- [x] Set as the latest release
- [ ] This is a pre-release (uncheck for v1.0.0)

### Step 6: Publish

Click "Publish release"

---

## ✅ Post-Release Steps

### 1. Verify Release

- [ ] Download the ZIP from GitHub
- [ ] Extract to a clean folder
- [ ] Run `install.bat` on a test machine
- [ ] Verify it works end-to-end

### 2. Update README

Add badges to README.md:

```markdown
[![Latest Release](https://img.shields.io/github/v/release/YOUR_USERNAME/quendoo-mcp)](https://github.com/YOUR_USERNAME/quendoo-mcp/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
```

### 3. Announce

- [ ] Post in Quendoo community (if applicable)
- [ ] Share with early users
- [ ] Update documentation site (if any)

---

## 🔄 Future Releases

### For v1.1.0 and beyond:

1. Create new branch for development
   ```bash
   git checkout -b develop
   ```

2. Make changes and test

3. Merge to main
   ```bash
   git checkout main
   git merge develop
   ```

4. Tag new version
   ```bash
   git tag -a v1.1.0 -m "Version 1.1.0 - [Description]"
   ```

5. Push everything
   ```bash
   git push origin main
   git push origin v1.1.0
   ```

6. Create new release on GitHub

---

## 📝 Release Naming Convention

- **Major** (v2.0.0): Breaking changes, major rewrites
- **Minor** (v1.1.0): New features, non-breaking changes
- **Patch** (v1.0.1): Bug fixes, minor improvements

---

## 🎯 Current Release Info

- **Version**: v1.0.0
- **Tag**: `v1.0.0`
- **Branch**: `main`
- **Commit**: `05af471`
- **Files**: 20 changed, 2008 insertions

---

## ⚠️ Security Checklist

Before releasing, ensure:

- [ ] No API keys in code
- [ ] No passwords in commits
- [ ] `.gitignore` includes `.env`, `*.key`, `*.pem`
- [ ] No sensitive data in example files
- [ ] JWT keys not committed

✅ All checks passed for this release!
