# IshemaLink — Deployment Manual
## How to Deploy on a Clean Ubuntu 24.04 Server (AOS / KtRN Data Center)

**Team:** Abraham Chan Deng Garang · Ashina Cecilia Wesebebe · Munezero Hubert  
**Version:** 2.0.0 — National Rollout

---

## Prerequisites

- Ubuntu 24.04 LTS server (minimum 8 vCPU, 16GB RAM, 200GB SSD)
- Docker 26+ and Docker Compose v2
- Domain name pointing to server IP (for SSL)
- Ports 80, 443 open in firewall

---

## Step 1: Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version && docker compose version
```

---

## Step 2: Clone Repository

```bash
git clone https://github.com/yourteam/ishemalink.git
cd ishemalink
git checkout main
```

---

## Step 3: Configure Environment

```bash
cp .env.example .env
nano .env
```

Set these values:
```env
DJANGO_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(50))">
DB_NAME=ishemalink
DB_USER=ishemalink
DB_PASSWORD=<strong-password>
ALLOWED_HOSTS=ishemalink.rw www.ishemalink.rw
DEBUG=False
MTN_MOMO_BASE_URL=https://sandbox.momodeveloper.mtn.com
GRAFANA_PASSWORD=<admin-password>
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=<access-key>
MINIO_SECRET_KEY=<secret-key>
```

---

## Step 4: SSL Certificate

```bash
# Install Certbot
sudo apt install certbot -y

# Obtain certificate (Nginx must be stopped first)
sudo certbot certonly --standalone -d ishemalink.rw -d www.ishemalink.rw

# Copy certs to docker/ssl/
sudo cp /etc/letsencrypt/live/ishemalink.rw/fullchain.pem docker/ssl/
sudo cp /etc/letsencrypt/live/ishemalink.rw/privkey.pem docker/ssl/
sudo chown $USER docker/ssl/*
```

---

## Step 5: Build and Deploy

```bash
cd docker/

# Build production image
docker compose -f docker-compose.prod.yml build

# Start all services
docker compose -f docker-compose.prod.yml up -d

# Run database migrations
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# Create admin superuser
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# Verify all containers are healthy
docker compose -f docker-compose.prod.yml ps
```

---

## Step 6: Seed Initial Data

```bash
# Load zones and commodities via Django admin or management command
docker compose -f docker-compose.prod.yml exec web python manage.py shell << 'EOF'
from apps.shipments.models import Zone, Commodity
from decimal import Decimal

# Rwandan logistics zones
zones = [
    ("Kigali Central", "Kigali", "50.00"),
    ("Musanze",        "Northern", "45.00"),
    ("Nyamagabe",      "Southern", "42.00"),
    ("Huye",           "Southern", "43.00"),
    ("Rwamagana",      "Eastern",  "41.00"),
    ("Rubavu",         "Western",  "44.00"),
]
for name, province, rate in zones:
    Zone.objects.get_or_create(name=name, defaults={"province": province, "base_rate_kg": Decimal(rate)})

# Key commodities
commodities = [
    ("Potatoes",       "0701.90", True),
    ("Coffee",         "0901.11", True),
    ("Tea",            "0902.10", True),
    ("Maize",          "1005.90", True),
    ("Steel Pipes",    "7304.11", False),
    ("Electronics",    "8471.30", False),
    ("Clothing",       "6109.10", False),
]
for name, hs, perishable in commodities:
    Commodity.objects.get_or_create(name=name, defaults={"hs_code": hs, "is_perishable": perishable})

print("Seed complete.")
EOF
```

---

## Step 7: Configure Automated Backups

```bash
# Install mc (MinIO client)
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc && sudo mv mc /usr/local/bin/

# Set up cron job (runs daily at 02:00 EAT = 23:00 UTC)
crontab -e
# Add: 0 23 * * * /home/ubuntu/ishemalink/docker/backup.sh >> /var/log/ishemalink_backup.log 2>&1
```

---

## Step 8: Verify Deployment

```bash
# Health check
curl https://ishemalink.rw/api/health/deep/

# Expected response:
# {"status": "ok", "checks": {"database": "ok", "redis": "ok", "disk": "ok"}}

# Check metrics
curl -u admin:password https://ishemalink.rw/api/ops/metrics/

# View Grafana dashboard
# Open: http://your-server-ip:3000 (Grafana)
# Default login: admin / <GRAFANA_PASSWORD>
```

---

## Monitoring & Alerts

- **Grafana:** `http://server:3000` — CPU, memory, request latency, error rate
- **Prometheus:** `http://server:9090` — raw metrics
- **Structured logs:** `docker compose logs -f web | python -m json.tool`

---

## Running Tests

```bash
# Unit + integration tests
docker compose -f docker-compose.prod.yml exec web \
    pytest tests/ -v --cov=apps --cov-report=term-missing

# Load test (from your local machine against staging)
pip install locust
locust -f locust_tests/locustfile.py \
    --host=https://staging.ishemalink.rw \
    --users=2000 --spawn-rate=100 --run-time=5m --headless

# Security scan
bandit -r apps/ -f txt -o docs/security_audit.txt
safety check -r requirements.txt
```

---

## Disaster Recovery

See `docs/IshemaLink_Written_Reports.pdf` for the full Disaster Recovery Plan.

**Quick Recovery (RTO < 2 hours):**
```bash
# Restore from latest backup
BACKUP_FILE=$(mc ls minio/ishemalink-backups/ | sort | tail -1 | awk '{print $5}')
mc cp minio/ishemalink-backups/$BACKUP_FILE /tmp/restore.dump

PGPASSWORD=$DB_PASSWORD pg_restore \
    --host=localhost --username=$DB_USER \
    --dbname=$DB_NAME --clean /tmp/restore.dump

docker compose -f docker-compose.prod.yml restart web
```

---

## File Structure

```
ishemalink/
├── ishemalink/          # Django project settings, URLs, ASGI, Celery
├── apps/
│   ├── authentication/  # Custom Agent model, JWT auth
│   ├── shipments/       # Shipment model, BookingService, TariffCalculator
│   ├── payments/        # Payment model, MomoMockAdapter, webhook
│   ├── notifications/   # SMS + Email service
│   ├── tracking/        # WebSocket consumer, GPS REST endpoint
│   ├── govtech/         # RRAConnector, RURAConnector, customs XML
│   ├── analytics/       # BI endpoints for MINICOM
│   └── ops/             # Health, metrics, maintenance, admin dashboard
├── tests/               # Full test suite (pytest)
├── locust_tests/        # Load testing scripts
├── docker/              # Docker Compose, Nginx, mock servers, backup
├── docs/                # Architecture diagram, written reports PDF
├── requirements.txt
├── Dockerfile
└── pytest.ini
```

## Author

Munezero Hubert

## Github

https://github.com/Hubert2c/Summative_IshemaLink_National-Rollout_Munez.git
