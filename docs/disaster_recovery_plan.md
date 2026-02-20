# IshemaLink Disaster Recovery Plan
**Version:** 2.0 | **Date:** February 2026 | **Owner:** IshemaLink Engineering

---

## 1. Overview

This document describes the Disaster Recovery (DR) procedures for IshemaLink — Rwanda's National Logistics Platform. It ensures business continuity in the event of infrastructure failures, data loss, or extended outages at the primary Rwanda data center (AOS/KtRN).

**Recovery Objectives:**
| Metric | Target |
|--------|--------|
| Recovery Time Objective (RTO) | ≤ 4 hours |
| Recovery Point Objective (RPO) | ≤ 24 hours (daily backups) |
| Target Uptime (SLA) | 99.5% |

---

## 2. System Architecture Summary

IshemaLink runs on Docker Compose at a local Rwanda data center with:
- **Web:** Django ASGI (Gunicorn + Uvicorn) behind Nginx
- **Database:** PostgreSQL 16 with PgBouncer pooling
- **Cache/Queue:** Redis 7
- **Async Workers:** Celery (worker + beat)
- **Backups:** MinIO (S3-compatible, on-premises)

All data remains within Rwanda borders to comply with data sovereignty requirements.

---

## 3. Backup Procedures

### 3.1 Automated Database Backups

A cron job runs **daily at 02:00 EAT** (`docker/backup.sh`):

```bash
# /etc/cron.d/ishemalink-backup
0 2 * * * root /app/docker/backup.sh >> /var/log/ishemalink/backup.log 2>&1
```

**Backup process:**
1. `pg_dump` creates a compressed custom-format dump
2. Dump is uploaded to MinIO bucket `ishemalink-backups`
3. Backup is verified by reading its table of contents (`pg_restore --list`)
4. Local temp file is deleted
5. Backups older than **30 days** are automatically pruned from MinIO

### 3.2 Backup Verification

Weekly, run:
```bash
# Download latest backup from MinIO
mc cp minio/ishemalink-backups/$(mc ls minio/ishemalink-backups | tail -1 | awk '{print $NF}') /tmp/test.dump

# Test restore on a clean DB
pg_restore --host=localhost --dbname=ishemalink_test --format=custom /tmp/test.dump
```

### 3.3 Redis Backup

Redis uses AOF (Append-Only File) persistence: `--appendonly yes`. The `/data` volume is included in the server's nightly filesystem snapshot.

---

## 4. Failure Scenarios & Responses

### 4.1 Container/Service Crash

**Detection:** Healthcheck probe at `GET /api/health/deep/` fails; Docker health check triggers.

**Auto-recovery:** All services run with `restart: unless-stopped`. Docker will restart crashed containers within 10–30 seconds automatically.

**Manual steps if persistent:**
```bash
docker compose -f docker/docker-compose.prod.yml logs web --tail=100
docker compose -f docker/docker-compose.prod.yml restart web
```

---

### 4.2 PostgreSQL Data Corruption

**RPO impact:** Up to 24 hours of data loss (last backup).

**Recovery steps:**
```bash
# 1. Stop the application
docker compose stop web celery_worker celery_beat

# 2. Enter PostgreSQL container
docker compose exec db psql -U ishemalink

# 3. Drop and recreate the database
DROP DATABASE ishemalink;
CREATE DATABASE ishemalink OWNER ishemalink;
\q

# 4. Download latest good backup from MinIO
mc cp minio/ishemalink-backups/ishemalink_YYYYMMDD_HHMMSS.dump /tmp/restore.dump

# 5. Restore
PGPASSWORD=$DB_PASSWORD pg_restore \
    --host=localhost --port=5432 \
    --username=ishemalink --dbname=ishemalink \
    --format=custom --no-privileges --no-owner \
    /tmp/restore.dump

# 6. Run any pending migrations
docker compose run web python manage.py migrate

# 7. Restart all services
docker compose start web celery_worker celery_beat
```

**Estimated recovery time:** 60–120 minutes

---

### 4.3 Complete Server/Data Center Failure

If the primary Rwanda data center is unavailable:

**Step 1: Activate Secondary (if configured)**
```bash
# SSH into secondary server
ssh deploy@secondary.ishemalink.rw

# Pull the latest images and start
docker compose -f docker/docker-compose.prod.yml pull
docker compose -f docker/docker-compose.prod.yml up -d
```

**Step 2: Restore database on secondary**
Follow Section 4.2 steps 4–7 on the secondary server.

**Step 3: Update DNS**
Point `ishemalink.rw` A record to the secondary server IP.
DNS TTL should be set to 300 seconds (5 minutes) for fast failover.

**Estimated total recovery time:** 2–4 hours

---

### 4.4 Redis Cache Loss

Redis data is **non-critical** for transactions (all financial data is in PostgreSQL). Loss of Redis means:
- Active WebSocket connections are dropped (users must reconnect)
- Celery task queue is lost (any queued tasks must be re-triggered)
- Sessions cache is lost (users must log in again)

**Recovery:**
```bash
docker compose restart redis
# Redis will start empty; AOF will replay if available
# Celery workers reconnect automatically within 30 seconds
```

---

### 4.5 Internet Outage (Nyamagabe/Rural Scenario)

IshemaLink's mobile app supports **offline-first operation**:

1. Shipments created offline get a `sync_id` (client-generated UUID)
2. When connectivity returns, the mobile app retries POST requests
3. The API is **idempotent** on `sync_id` — duplicate syncs return the existing shipment
4. Pending MoMo payments are retried automatically by Celery when Redis reconnects

**For partial outages** (a single zone loses connectivity):
- The system automatically enables maintenance mode if health check failures exceed a threshold
- Drivers in affected areas continue operating with last-known data from the mobile app cache

---

### 4.6 Payment Gateway (MTN MoMo) Outage

If MTN MoMo API is unreachable:
1. `simulate_momo_callback` task will fail with a connection error
2. Celery will retry the callback up to 3 times with exponential backoff
3. The shipment remains in `CONFIRMED` state — it does NOT auto-cancel
4. After 30 minutes, `auto_fail_unpaid_shipments` (Celery beat) marks the shipment as `FAILED` with note "Auto-cancelled: payment timeout"
5. The sender receives an SMS notification to retry

---

## 5. Monitoring & Alerting

### 5.1 Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health/deep/` | DB, Redis, disk — returns 200 if all OK |
| `GET /api/ops/metrics/` | Prometheus metrics |

### 5.2 Grafana Alerts

Configure the following Grafana alert rules:

| Alert | Condition | Action |
|-------|-----------|--------|
| High error rate | `rate(django_http_responses_total{status=~"5.."}[5m]) > 0.05` | PagerDuty → on-call |
| DB down | Health check fails 3 consecutive times | Page on-call, escalate |
| Disk > 85% | `disk_free_gb < 10` | Warn, schedule cleanup |
| Queue backlog | Celery pending tasks > 1000 | Investigate worker health |

### 5.3 Log Monitoring

All logs are structured JSON. To search for errors:
```bash
docker compose logs web | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        log = json.loads(line)
        if log.get('levelname') == 'ERROR':
            print(json.dumps(log, indent=2))
    except: pass
"
```

---

## 6. Contact & Escalation

| Role | Responsibility |
|------|---------------|
| Lead Engineer | Primary DR contact |
| Database Admin | PostgreSQL recovery |
| MINICOM/RURA | Government integration issues |
| AOS/KtRN Support | Data center infrastructure |

**Emergency contacts** (to be filled with actual numbers before go-live):
- On-call engineer: +250 7xx xxx xxx
- AOS data center NOC: +250 7xx xxx xxx

---

## 7. DR Test Schedule

| Test | Frequency | Owner |
|------|-----------|-------|
| Backup verification | Weekly | DevOps |
| Container restart test | Monthly | DevOps |
| Full restore drill | Quarterly | Lead Engineer |
| Failover to secondary | Semi-annually | Lead Engineer |

---

*Last reviewed: February 2026 | Next review: May 2026*
