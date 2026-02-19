#!/bin/bash
# IshemaLink Automated Backup Script
# Schedule: cron job — runs daily at 02:00 EAT
# Crontab:  0 2 * * * /app/docker/backup.sh >> /var/log/ishemalink/backup.log 2>&1
#
# Backups are uploaded to MinIO (S3-compatible, on-premises — data sovereignty)

set -euo pipefail

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/tmp/ishemalink_backups"
BACKUP_FILE="ishemalink_${TIMESTAMP}.dump"
MINIO_BUCKET="${MINIO_BUCKET:-ishemalink-backups}"
RETENTION_DAYS=30

echo "[$(date -Iseconds)] Starting backup..."

mkdir -p "$BACKUP_DIR"

# PostgreSQL dump (custom format — compressed, parallel-restore capable)
PGPASSWORD="$DB_PASSWORD" pg_dump \
    --host="$DB_HOST" \
    --port="${DB_PORT:-5432}" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --format=custom \
    --compress=9 \
    --file="${BACKUP_DIR}/${BACKUP_FILE}"

echo "[$(date -Iseconds)] DB dump complete: ${BACKUP_FILE} ($(du -sh "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1))"

# Upload to MinIO (S3-compatible on-premises storage)
mc alias set minio "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"
mc cp "${BACKUP_DIR}/${BACKUP_FILE}" "minio/${MINIO_BUCKET}/${BACKUP_FILE}"

echo "[$(date -Iseconds)] Uploaded to MinIO: ${MINIO_BUCKET}/${BACKUP_FILE}"

# Verify the backup is readable
PGPASSWORD="$DB_PASSWORD" pg_restore \
    --list "${BACKUP_DIR}/${BACKUP_FILE}" > /dev/null

echo "[$(date -Iseconds)] Backup verified successfully."

# Cleanup local temp file
rm -f "${BACKUP_DIR}/${BACKUP_FILE}"

# Prune remote backups older than RETENTION_DAYS
mc find "minio/${MINIO_BUCKET}" --older-than "${RETENTION_DAYS}d24h" --exec "mc rm {}"

echo "[$(date -Iseconds)] Backup complete. Retention: ${RETENTION_DAYS} days."
