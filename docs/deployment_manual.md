# IshemaLink Deployment Manual
**How to deploy IshemaLink on a clean Ubuntu 24.04 Server**

---

## Prerequisites

- Ubuntu 24.04 LTS (minimum 4 CPU, 8GB RAM, 50GB SSD)
- Root or sudo access
- Domain name pointed at the server (e.g., `ishemalink.rw`)
- SSL certificate (Let's Encrypt recommended)

---

## Step 1: Install Docker & Docker Compose

```bash
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to the docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version        # Docker 25+
docker compose version  # Compose 2.x
```

---

## Step 2: Clone the Repository

```bash
cd /opt
sudo git clone https://github.com/your-org/ishemalink.git
sudo chown -R $USER:$USER ishemalink
cd ishemalink
```

---

## Step 3: Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Fill in all values:
```dotenv
DJANGO_SECRET_KEY=<generate with: python3 -c "import secrets; print(secrets.token_hex(50))">
DEBUG=False
ALLOWED_HOSTS=ishemalink.rw www.ishemalink.rw

DB_NAME=ishemalink
DB_USER=ishemalink
DB_PASSWORD=<strong-random-password>

MTN_MOMO_BASE_URL=https://sandbox.momodeveloper.mtn.com
GRAFANA_PASSWORD=<admin-password>
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=<access-key>
MINIO_SECRET_KEY=<secret-key>
```

---

## Step 4: SSL Certificates

```bash
# Using Let's Encrypt (certbot)
sudo apt install certbot
sudo certbot certonly --standalone -d ishemalink.rw -d www.ishemalink.rw

# Copy certs to docker volume
mkdir -p docker/ssl
sudo cp /etc/letsencrypt/live/ishemalink.rw/fullchain.pem docker/ssl/
sudo cp /etc/letsencrypt/live/ishemalink.rw/privkey.pem docker/ssl/
sudo chown $USER:$USER docker/ssl/*
```

---

## Step 5: Build & Start

```bash
# Build the Django image
docker compose -f docker/docker-compose.prod.yml build

# Run database migrations
docker compose -f docker/docker-compose.prod.yml run --rm web \
    python manage.py migrate

# Create superuser
docker compose -f docker/docker-compose.prod.yml run --rm web \
    python manage.py createsuperuser

# Collect static files
docker compose -f docker/docker-compose.prod.yml run --rm web \
    python manage.py collectstatic --noinput

# Seed initial Zones and Commodities (optional)
docker compose -f docker/docker-compose.prod.yml run --rm web \
    python manage.py seed_initial_data

# Start all services
docker compose -f docker/docker-compose.prod.yml up -d
```

---

## Step 6: Verify Deployment

```bash
# Check all containers are running
docker compose -f docker/docker-compose.prod.yml ps

# Test health endpoint
curl https://ishemalink.rw/api/health/deep/
# Expected: {"status": "ok", "checks": {"database": "ok", "redis": "ok", ...}}

# Check logs for errors
docker compose -f docker/docker-compose.prod.yml logs web --tail=50
```

---

## Step 7: Set Up Automated Backups

```bash
# Make backup script executable
chmod +x docker/backup.sh

# Set up cron job (runs daily at 02:00 EAT)
(crontab -l; echo "0 2 * * * /opt/ishemalink/docker/backup.sh >> /var/log/ishemalink/backup.log 2>&1") | crontab -

# Create log directory
sudo mkdir -p /var/log/ishemalink
sudo chown $USER:$USER /var/log/ishemalink
```

---

## Step 8: Set Up Auto-Renewal for SSL

```bash
# Test renewal
sudo certbot renew --dry-run

# Add renewal hook to copy certs
echo '#!/bin/bash
cp /etc/letsencrypt/live/ishemalink.rw/fullchain.pem /opt/ishemalink/docker/ssl/
cp /etc/letsencrypt/live/ishemalink.rw/privkey.pem /opt/ishemalink/docker/ssl/
docker compose -f /opt/ishemalink/docker/docker-compose.prod.yml restart nginx
' | sudo tee /etc/letsencrypt/renewal-hooks/deploy/ishemalink.sh
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/ishemalink.sh
```

---

## Common Operations

### Restart a specific service
```bash
docker compose -f docker/docker-compose.prod.yml restart web
```

### View live logs
```bash
docker compose -f docker/docker-compose.prod.yml logs -f web celery_worker
```

### Enable maintenance mode
```bash
curl -X POST https://ishemalink.rw/api/ops/maintenance/toggle/ \
     -H "Authorization: Bearer <admin-token>"
```

### Scale workers during harvest peak
```bash
docker compose -f docker/docker-compose.prod.yml up -d --scale celery_worker=4
```

### Run a Django management command
```bash
docker compose -f docker/docker-compose.prod.yml exec web python manage.py shell
```

---

## Monitoring

- **Grafana:** http://your-server:3000 (default admin / password from `.env`)
- **Prometheus:** http://your-server:9090
- **API Docs:** https://ishemalink.rw/api/docs/

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| `502 Bad Gateway` | Check `docker compose logs web` — likely app crash |
| `Database connection refused` | Check `docker compose ps db pgbouncer` |
| Celery tasks not running | Check `docker compose logs celery_worker` |
| SSL error | Verify cert paths in `docker/ssl/`, check nginx.conf |
| Out of disk space | Run `docker system prune` to clean unused images/volumes |
