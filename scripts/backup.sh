#!/usr/bin/env bash
# AuroraElo — Automated PostgreSQL Backup Script
#
# Usage:
#   DATABASE_URL="postgresql://..." ./scripts/backup.sh
#   DATABASE_URL="postgresql://..." BACKUP_DIR="/backups" RETENTION_DAYS=90 ./scripts/backup.sh
#
# Environment Variables:
#   DATABASE_URL      - Required. PostgreSQL connection string.
#   BACKUP_DIR        - Optional. Directory for backups (default: /backups).
#   RETENTION_DAYS    - Optional. Days to retain backups (default: 90).
#   ENCRYPTION_KEY    - Optional. GPG key ID for backup encryption.
#   GCS_BUCKET        - Optional. GCS bucket for offsite backup (e.g., gs://auroraelo-backups).

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-90}"
BACKUP_FILE="auroraelo_${TIMESTAMP}.sql.gz"

echo "[$(date -Iseconds)] Starting backup..."

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# Dump, compress, optionally encrypt
if [[ -n "${ENCRYPTION_KEY:-}" ]]; then
    BACKUP_FILE="${BACKUP_FILE}.gpg"
    pg_dump "${DATABASE_URL}" \
        | gzip \
        | gpg --encrypt --recipient "${ENCRYPTION_KEY}" \
        > "${BACKUP_DIR}/${BACKUP_FILE}"
    echo "[$(date -Iseconds)] Encrypted backup created: ${BACKUP_FILE}"
else
    pg_dump "${DATABASE_URL}" \
        | gzip \
        > "${BACKUP_DIR}/${BACKUP_FILE}"
    echo "[$(date -Iseconds)] Backup created: ${BACKUP_FILE}"
fi

# Calculate and log backup size
BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
echo "[$(date -Iseconds)] Backup size: ${BACKUP_SIZE}"

# Upload to GCS if bucket is configured
if [[ -n "${GCS_BUCKET:-}" ]]; then
    gsutil cp "${BACKUP_DIR}/${BACKUP_FILE}" "${GCS_BUCKET}/${BACKUP_FILE}"
    echo "[$(date -Iseconds)] Uploaded to ${GCS_BUCKET}/${BACKUP_FILE}"
fi

# Rotate old backups (local)
DELETED_COUNT=$(find "${BACKUP_DIR}" -name "auroraelo_*.sql.gz*" -mtime +"${RETENTION_DAYS}" -print -delete | wc -l)
if [[ "${DELETED_COUNT}" -gt 0 ]]; then
    echo "[$(date -Iseconds)] Deleted ${DELETED_COUNT} backups older than ${RETENTION_DAYS} days."
fi

echo "[$(date -Iseconds)] Backup completed successfully: ${BACKUP_FILE}"
