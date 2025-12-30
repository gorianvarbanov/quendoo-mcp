# Linode VPS Deployment Guide

Complete guide for deploying Quendoo MCP Server on Linode VPS.

## 🚀 Quick Start (5 minutes)

### Option 1: One-Command Setup (Recommended)

1. Create a new Linode instance (Ubuntu 22.04 or 24.04)
2. SSH into your server
3. Run this single command:

```bash
curl -fsSL https://raw.githubusercontent.com/gorianvarbanov/quendoo-mcp/main/deploy/linode-setup.sh | bash
```

4. Edit configuration:
```bash
nano /opt/quendoo-mcp/.env
# Add your API keys
```

5. Restart service:
```bash
systemctl restart quendoo-mcp
```

Done! Your server is running at `http://YOUR_LINODE_IP/sse`

---

## 📋 Manual Setup (Step by Step)

### Step 1: Create Linode Instance

**Recommended specs:**
- **Distribution**: Ubuntu 22.04 LTS
- **Plan**: Shared CPU - Nanode 1GB ($5/month) or Linode 2GB ($10/month)
- **Region**: Choose closest to your users
- **Label**: `quendoo-mcp-prod`

### Step 2: Initial Server Setup

```bash
# SSH into your server
ssh root@YOUR_LINODE_IP

# Update system
apt-get update && apt-get upgrade -y

# Install required packages
apt-get install -y git curl python3 python3-pip python3-venv nginx supervisor ufw
```

### Step 3: Clone Repository

```bash
cd /opt
git clone https://github.com/gorianvarbanov/quendoo-mcp.git
cd quendoo-mcp
```

### Step 4: Setup Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 5: Configure Environment

```bash
# Create .env file
cat > .env << 'EOF'
MCP_TRANSPORT=sse
HOST=0.0.0.0
PORT=8080

# Add your API keys here
QUENDOO_API_KEY=your_actual_api_key
EMAIL_API_KEY=your_email_api_key
QUENDOO_AUTOMATION_BEARER=your_automation_bearer
EOF
```

### Step 6: Create Systemd Service

```bash
cat > /etc/systemd/system/quendoo-mcp.service << 'EOF'
[Unit]
Description=Quendoo MCP Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/quendoo-mcp
Environment="PATH=/opt/quendoo-mcp/venv/bin"
ExecStart=/opt/quendoo-mcp/venv/bin/python server_simple.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable quendoo-mcp
systemctl start quendoo-mcp
```

### Step 7: Setup Nginx Reverse Proxy

```bash
cat > /etc/nginx/sites-available/quendoo-mcp << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;

        # SSE specific
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/quendoo-mcp /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx
```

### Step 8: Configure Firewall

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

---

## 🔐 SSL/HTTPS Setup (Optional but Recommended)

### With Domain Name

If you have a domain pointing to your Linode:

```bash
# Install Certbot
apt-get install -y certbot python3-certbot-nginx

# Get SSL certificate
certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

Update nginx config:
```bash
server_name your-domain.com;  # Replace _ with your domain
```

---

## 🔄 Updates and Maintenance

### Update Server Code

```bash
cd /opt/quendoo-mcp
git pull
source venv/bin/activate
pip install -r requirements.txt
systemctl restart quendoo-mcp
```

Or use the auto-generated update script:
```bash
/opt/quendoo-mcp/update.sh
```

### Check Service Status

```bash
# Service status
systemctl status quendoo-mcp

# View logs
journalctl -u quendoo-mcp -f

# Restart service
systemctl restart quendoo-mcp
```

### Monitor Resources

```bash
# CPU and memory usage
htop

# Disk usage
df -h

# Network connections
netstat -tulpn | grep :8080
```

---

## 🐳 Docker Deployment (Alternative)

If you prefer Docker:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Build and run
cd /opt/quendoo-mcp
docker build -t quendoo-mcp .
docker run -d \
  --name quendoo-mcp \
  --restart always \
  -p 8080:8080 \
  -e MCP_TRANSPORT=sse \
  -e QUENDOO_API_KEY=your_key \
  quendoo-mcp
```

---

## 📊 Monitoring

### Setup Simple Monitoring

```bash
# Install monitoring tools
apt-get install -y htop iotop nethogs

# Check if service is running
systemctl is-active quendoo-mcp

# Test endpoint
curl http://localhost:8080/sse -I
```

### Setup Uptime Monitoring (External)

Use free services like:
- UptimeRobot (https://uptimerobot.com)
- Pingdom (https://www.pingdom.com)
- StatusCake (https://www.statuscake.com)

Monitor URL: `http://YOUR_LINODE_IP/sse`

---

## 🔧 Troubleshooting

### Service won't start

```bash
# Check logs
journalctl -u quendoo-mcp -n 50

# Check if port is in use
netstat -tulpn | grep :8080

# Test Python directly
cd /opt/quendoo-mcp
source venv/bin/activate
python server_simple.py
```

### Nginx errors

```bash
# Test nginx config
nginx -t

# Check nginx logs
tail -f /var/log/nginx/error.log
```

### Out of memory

```bash
# Add swap space
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

---

## 💰 Cost Estimates

- **Nanode 1GB**: $5/month (good for testing)
- **Linode 2GB**: $10/month (recommended for production)
- **Linode 4GB**: $20/month (for high traffic)

---

## 🔄 Backup Strategy

```bash
# Backup script
cat > /opt/backup-quendoo.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cd /opt/quendoo-mcp
tar -czf $BACKUP_DIR/quendoo-mcp-$DATE.tar.gz \
  --exclude=venv \
  --exclude=__pycache__ \
  .env server_simple.py tools/ requirements.txt

# Keep only last 7 backups
ls -t $BACKUP_DIR/quendoo-mcp-*.tar.gz | tail -n +8 | xargs rm -f

echo "✅ Backup created: quendoo-mcp-$DATE.tar.gz"
EOF

chmod +x /opt/backup-quendoo.sh

# Run daily via cron
echo "0 2 * * * /opt/backup-quendoo.sh" | crontab -
```

---

## 📞 Support

For issues specific to this deployment:
- Check logs: `journalctl -u quendoo-mcp -f`
- GitHub Issues: https://github.com/gorianvarbanov/quendoo-mcp/issues
- Review [DEPLOYMENT.md](../DEPLOYMENT.md) for general deployment info
