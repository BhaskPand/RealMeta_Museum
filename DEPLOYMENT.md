# Deployment Guide for ScanArt MVP

This guide covers multiple deployment options for the ScanArt application.

## Table of Contents
1. [GitHub Setup](#github-setup)
2. [Deployment Options](#deployment-options)
   - [Option 1: Railway (Recommended - Easiest)](#option-1-railway-recommended---easiest)
   - [Option 2: Render](#option-2-render)
   - [Option 3: Heroku](#option-3-heroku)
   - [Option 4: VPS (DigitalOcean, AWS, etc.)](#option-4-vps-digitalocean-aws-etc)

---

## GitHub Setup

### Step 1: Initialize Git (if not already done)
```bash
cd /Users/apple/Documents/RealMeta_Museum/scanart-mvp
git init
```

### Step 2: Add all files
```bash
git add .
```

### Step 3: Create initial commit
```bash
git commit -m "Initial commit: ScanArt MVP - Museum Painting Scanner"
```

### Step 4: Create GitHub Repository
1. Go to [GitHub.com](https://github.com) and sign in
2. Click the **+** icon in the top right → **New repository**
3. Name it: `scanart-mvp` (or your preferred name)
4. **DO NOT** initialize with README, .gitignore, or license
5. Click **Create repository**

### Step 5: Connect and Push
```bash
# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/scanart-mvp.git

# Push to GitHub
git branch -M main
git push -u origin main
```

---

## Deployment Options

### Option 1: Railway (Recommended - Easiest)

**Pros:** Free tier, automatic deployments, easy setup

#### Steps:
1. **Sign up** at [railway.app](https://railway.app)
2. **Connect GitHub:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
3. **Configure:**
   - Railway will auto-detect Python
   - Add environment variable: `ADMIN_PASSWORD=your_secure_password`
4. **Set Start Command:**
   - In Railway dashboard → Settings → Deploy
   - Add start command: `cd backend && python app.py`
5. **Deploy:**
   - Railway will automatically build and deploy
   - Your app will be live at `your-app.railway.app`

---

### Option 2: Render

**Pros:** Free tier, automatic SSL, easy setup

#### Steps:
1. **Sign up** at [render.com](https://render.com)
2. **Create Web Service:**
   - Click "New" → "Web Service"
   - Connect your GitHub repository
3. **Configure:**
   - **Name:** scanart-mvp
   - **Environment:** Python 3
   - **Build Command:** `cd backend && pip install -r requirements.txt && python app.py precompute`
   - **Start Command:** `cd backend && python app.py`
   - **Root Directory:** (leave blank)
4. **Add Environment Variables:**
   - `ADMIN_PASSWORD`: your_secure_password
   - `PORT`: 10000 (Render sets this automatically, but add as backup)
5. **Deploy:**
   - Click "Create Web Service"
   - Render will build and deploy automatically

---

### Option 3: Heroku

**Pros:** Reliable, well-documented

#### Steps:
1. **Install Heroku CLI:**
   ```bash
   brew install heroku/brew/heroku  # macOS
   ```

2. **Login:**
   ```bash
   heroku login
   ```

3. **Create App:**
   ```bash
   heroku create scanart-mvp
   ```

4. **Set Environment Variables:**
   ```bash
   heroku config:set ADMIN_PASSWORD=your_secure_password
   ```

5. **Deploy:**
   ```bash
   git push heroku main
   ```

6. **Run Precompute:**
   ```bash
   heroku run python backend/app.py precompute
   ```

---

### Option 4: VPS (DigitalOcean, AWS, etc.)

**Pros:** Full control, scalable

#### Steps:

1. **SSH into your server:**
   ```bash
   ssh user@your-server-ip
   ```

2. **Install dependencies:**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv nginx
   ```

3. **Clone repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/scanart-mvp.git
   cd scanart-mvp
   ```

4. **Setup virtual environment:**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. **Run precompute:**
   ```bash
   python app.py precompute
   ```

6. **Setup systemd service** (create `/etc/systemd/system/scanart.service`):
   ```ini
   [Unit]
   Description=ScanArt Flask App
   After=network.target

   [Service]
   User=your-user
   WorkingDirectory=/home/your-user/scanart-mvp/backend
   Environment="PATH=/home/your-user/scanart-mvp/backend/venv/bin"
   Environment="ADMIN_PASSWORD=your_secure_password"
   ExecStart=/home/your-user/scanart-mvp/backend/venv/bin/python app.py

   [Install]
   WantedBy=multi-user.target
   ```

7. **Start service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable scanart
   sudo systemctl start scanart
   ```

8. **Setup Nginx** (create `/etc/nginx/sites-available/scanart`):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

9. **Enable site:**
   ```bash
   sudo ln -s /etc/nginx/sites-available/scanart /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

---

## Post-Deployment Checklist

1. **Precompute embeddings:**
   - Visit: `https://your-app.com/precompute` (POST request)
   - Or run locally and upload `embeddings.json`

2. **Test the app:**
   - Visit your deployed URL
   - Test camera scan
   - Test admin dashboard at `/admin`

3. **Set up domain (optional):**
   - Most platforms allow custom domains
   - Update DNS records as instructed by platform

---

## Troubleshooting

### Common Issues:

1. **Port binding error:**
   - Ensure app uses `PORT` environment variable or binds to `0.0.0.0`

2. **Missing embeddings.json:**
   - Run precompute endpoint after deployment

3. **Static files not loading:**
   - Ensure Flask static file serving is configured correctly

4. **Admin password not working:**
   - Check environment variable is set correctly

---

## Environment Variables

- `ADMIN_PASSWORD`: Admin dashboard password (default: `admin123`)
- `PORT`: Server port (auto-set by most platforms)

---

## Support

For issues, check:
- Platform-specific documentation
- Flask deployment guides
- Project README.md

