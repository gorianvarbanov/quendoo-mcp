#!/bin/bash
# Quendoo MCP Server - Linode VPS Setup Script
# This script sets up everything needed to run the MCP server on a fresh Ubuntu VPS

set -e  # Exit on error

echo "========================================="
echo "Quendoo MCP Server - Linode VPS Setup"
echo "========================================="

# Update system
echo "📦 Updating system packages..."
apt-get update
apt-get upgrade -y

# Install required packages
echo "📦 Installing required packages..."
apt-get install -y \
    git \
    curl \
    wget \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    certbot \
    python3-certbot-nginx \
    supervisor

# Install Docker (optional, for containerized deployment)
echo "🐳 Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Clone repository
echo "📥 Cloning Quendoo MCP repository..."
cd /opt
if [ -d "quendoo-mcp" ]; then
    echo "Repository already exists, pulling latest changes..."
    cd quendoo-mcp
    git pull
else
    git clone https://github.com/gorianvarbanov/quendoo-mcp.git
    cd quendoo-mcp
fi

# Create Python virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create environment file
echo "⚙️  Creating environment configuration..."
cat > .env << 'EOF'
# MCP Server Configuration
MCP_TRANSPORT=sse
HOST=0.0.0.0
PORT=8080

# Quendoo API Keys (REPLACE WITH YOUR ACTUAL KEYS)
QUENDOO_API_KEY=your_api_key_here
EMAIL_API_KEY=your_email_api_key_here
QUENDOO_AUTOMATION_BEARER=your_automation_bearer_here
EOF

echo ""
echo "⚠️  IMPORTANT: Edit /opt/quendoo-mcp/.env and add your API keys!"
echo ""

# Create systemd service
echo "🔧 Creating systemd service..."
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

# Configure nginx as reverse proxy
echo "🌐 Configuring Nginx..."
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
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE specific settings
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
EOF

# Enable nginx site
ln -sf /etc/nginx/sites-available/quendoo-mcp /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# Configure firewall
echo "🔒 Configuring firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Enable and start service
echo "🚀 Starting Quendoo MCP service..."
systemctl daemon-reload
systemctl enable quendoo-mcp
systemctl start quendoo-mcp

# Create update script
echo "📝 Creating update script..."
cat > /opt/quendoo-mcp/update.sh << 'EOF'
#!/bin/bash
cd /opt/quendoo-mcp
git pull
source venv/bin/activate
pip install -r requirements.txt
systemctl restart quendoo-mcp
echo "✅ Quendoo MCP updated and restarted!"
EOF
chmod +x /opt/quendoo-mcp/update.sh

echo ""
echo "========================================="
echo "✅ Installation Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit /opt/quendoo-mcp/.env and add your API keys"
echo "2. Restart the service: systemctl restart quendoo-mcp"
echo "3. Check status: systemctl status quendoo-mcp"
echo "4. View logs: journalctl -u quendoo-mcp -f"
echo ""
echo "To update the server in the future:"
echo "  cd /opt/quendoo-mcp && ./update.sh"
echo ""
echo "Server URL: http://$(curl -s ifconfig.me)/sse"
echo ""
