# Enterprise AI Employee – Production Deployment Guide (Single Linux Server / AWS EC2)

This guide documents deploying the hardened **Enterprise AI Employee** application onto a single Linux host (e.g., AWS EC2) with Docker, Docker Compose, Nginx, and automated backups.

---

## 1. AWS EC2 Provisioning

### Recommended Server Specs
- **Instance Type:** `t3.small` (2 vCPU, 2 GB RAM) or `t3.medium` (2 vCPU, 4 GB RAM).
- **Architecture:** `x86_64` (or `t4g.small` ARM64).
- **Operating System:** Ubuntu 24.04 LTS.
- **Storage:** 30 GB gp3 SSD (root volume).

### Security Group Configuration
| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 22 | TCP | Your Admin IP (`x.x.x.x/32`) | Secure SSH access |
| 80 | TCP | `0.0.0.0/0` | HTTP (Certbot SSL challenges & redirection) |
| 443 | TCP | `0.0.0.0/0` | HTTPS (Production web traffic) |

---

## 2. Server Initialization & Docker Setup

Connect to your EC2 instance:
```bash
ssh -i your-key.pem ubuntu@<your-ec2-ip>
```

Update system packages and install Docker:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git ufw fail2ban certbot python3-certbot-nginx

# Install official Docker repository and Engine
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Allow non-root user to run Docker commands
sudo usermod -aG docker ubuntu
newgrp docker

# Verify Docker installation
docker --version
docker compose version
```

Configure UFW firewall:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 3. Clone Repository and Configure Environment

```bash
sudo mkdir -p /opt/enterprise-ai
sudo chown -R ubuntu:ubuntu /opt/enterprise-ai
cd /opt/enterprise-ai

# Clone the repository
git clone https://github.com/keshav-sudo/Enterprise-AI-Employee.git .
git checkout feature/hardening

# Configure production environment variables
cp .env.example .env
nano .env
```

Ensure the following variables are configured in `.env`:
```ini
ENV=production
APP_API_KEY=your_generated_secret_key_here
GEMINI_API_KEY=your_google_ai_studio_api_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_FAKE=0
ALLOWED_ORIGINS=https://your-domain.com
RATE_LIMIT_PER_MIN=30
MAX_MESSAGE_CHARS=4000
MEMORY_DB_PATH=/app/data/memory.db
```

Generate secure application keys with:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 4. Launching Application with Docker Compose

Build and launch the container in the background:
```bash
docker compose up -d --build
```

Verify container status and health:
```bash
docker compose ps
docker compose logs -f
```

Test internal health endpoint:
```bash
curl -i http://localhost:8000/health
```

Expected response:
```json
{"status":"healthy","version":"0.5.0","model":"gemini-2.5-flash","gemini_configured":true,"gemini_fake":false}
```

---

## 5. Nginx Reverse Proxy & SSL Setup

Install and configure Nginx:
```bash
sudo cp infra/nginx.conf /etc/nginx/sites-available/enterprise-ai
sudo ln -s /etc/nginx/sites-available/enterprise-ai /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

Obtain a free Let's Encrypt SSL certificate:
```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Test automatic SSL renewal:
```bash
sudo certbot renew --dry-run
```

---

## 6. Automated Persistent Backups

Create a daily backup script for SQLite chat history and ChromaDB vectors:
```bash
sudo mkdir -p /opt/backups
sudo tee /opt/enterprise-ai/scripts/backup.sh > /dev/null << 'EOF'
#!/bin/bash
set -e
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups/$TIMESTAMP"
mkdir -p "$BACKUP_DIR"

echo "Backing up SQLite database..."
# Use SQLite safe backup API to snapshot active WAL database safely
sqlite3 /opt/enterprise-ai/data/memory.db ".backup '$BACKUP_DIR/memory.db'"

echo "Backing up ChromaDB..."
tar -czf "$BACKUP_DIR/chroma.tar.gz" -C /opt/enterprise-ai/data chroma

echo "Backup completed successfully to $BACKUP_DIR"

# Keep last 14 days of backups
find /opt/backups -mindepth 1 -maxdepth 1 -type d -mtime +14 -exec rm -rf {} +
EOF

chmod +x /opt/enterprise-ai/scripts/backup.sh
```

Add cron job to run backup nightly at 2:00 AM:
```bash
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/enterprise-ai/scripts/backup.sh >> /var/log/backup.log 2>&1") | crontab -
```

---

## 7. Zero-Downtime Updates & Rollback Procedure

### Deploying Updates
```bash
cd /opt/enterprise-ai
git pull origin feature/hardening
docker compose build
docker compose up -d --no-deps app
```

### Emergency Rollback
If an issue occurs after deployment:
```bash
cd /opt/enterprise-ai
git log --oneline -n 5
git checkout <previous-commit-hash>
docker compose up -d --build
```
To restore database from backup:
```bash
docker compose stop
cp /opt/backups/<timestamp>/memory.db /opt/enterprise-ai/data/memory.db
docker compose start
```

