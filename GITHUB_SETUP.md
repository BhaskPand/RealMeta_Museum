# Quick GitHub Setup Guide

## Step-by-Step Instructions

### 1. Open Terminal and Navigate to Project
```bash
cd /Users/apple/Documents/RealMeta_Museum/scanart-mvp
```

### 2. Initialize Git (if not already done)
```bash
git init
```

### 3. Add All Files
```bash
git add .
```

### 4. Create Initial Commit
```bash
git commit -m "Initial commit: ScanArt MVP - Museum Painting Scanner with colorful UI"
```

### 5. Create GitHub Repository
1. Go to [github.com](https://github.com) and sign in
2. Click the **+** icon (top right) → **New repository**
3. Repository name: `scanart-mvp`
4. Description: "Museum Painting Scanner - Scan artwork with your camera and get detailed information"
5. Choose **Public** or **Private**
6. **DO NOT** check any boxes (README, .gitignore, license)
7. Click **Create repository**

### 6. Connect Local Repository to GitHub
```bash
# Replace YOUR_USERNAME with your actual GitHub username
git remote add origin https://github.com/YOUR_USERNAME/scanart-mvp.git

# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

### 7. Verify
- Go to your GitHub repository URL
- You should see all your files there!

---

## For Future Updates

Whenever you make changes:

```bash
# Check what changed
git status

# Add changes
git add .

# Commit with message
git commit -m "Description of changes"

# Push to GitHub
git push
```

---

## Need Help?

- **GitHub not found?** Make sure you're logged in at github.com
- **Permission denied?** You may need to set up SSH keys or use a personal access token
- **Branch issues?** Run `git branch -M main` to rename to main

---

## Next Steps

After pushing to GitHub, see `DEPLOYMENT.md` for deployment options!

