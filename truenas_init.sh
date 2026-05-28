#!/bin/bash
# ============================================================
# SpikesortingLabHub — TrueNAS Post-Init Script
#
# Upload this file to TrueNAS via:
#   System → Advanced Settings → Init/Shutdown Scripts
#   Type: Script   When: Post Init   Timeout: 60
#
# This script runs after every TrueNAS boot.  It waits for
# the ZFS pool to be mounted, then starts the Docker container
# with all bind mounts in place.
# ============================================================

set -euo pipefail

LOG="/var/log/sslh_init.log"
exec >> "$LOG" 2>&1

echo "=== $(date) SpikesortingLabHub init starting ==="

# ── Paths on the NAS ──────────────────────────────────────────
COMPOSE_FILE="/mnt/root_data_storage/users/sslh/docker-compose.yml"
SECRET_FILE="/mnt/root_data_storage/users/sslh/secrets/django_secret.key"

REQUIRED_DIRS=(
    "/mnt/root_data_storage/users/sslh/trurnasdata"
    "/mnt/root_data_storage/users/sslh/persistentdata"
    "/mnt/root_data_storage/users/sslh/secrets"
    "/mnt/root_data_storage/experiments"
)

# ── 1. Wait for ZFS pool to mount (up to 60 s) ───────────────
echo "Waiting for storage pool..."
TIMEOUT=60
ELAPSED=0
until [ -f "$COMPOSE_FILE" ]; do
    if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
        echo "ERROR: Storage pool not mounted after ${TIMEOUT}s — aborting."
        exit 1
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done
echo "Storage pool ready."

# ── 2. Verify required directories exist ─────────────────────
for DIR in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$DIR" ]; then
        echo "ERROR: Required directory missing: $DIR"
        exit 1
    fi
done
echo "All bind-mount directories present."

# ── 3. Load Django secret key ─────────────────────────────────
if [ ! -f "$SECRET_FILE" ]; then
    echo "ERROR: Django secret key not found at $SECRET_FILE"
    echo "  Create it with:  openssl rand -hex 50 > $SECRET_FILE"
    exit 1
fi
export DJANGO_SECRET_KEY
DJANGO_SECRET_KEY="$(cat "$SECRET_FILE")"

# ── 4. Stop any stale container from a previous boot ─────────
docker compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true

# ── 5. Start container in background ─────────────────────────
docker compose -f "$COMPOSE_FILE" up -d

echo "=== $(date) SpikesortingLabHub started successfully ==="
