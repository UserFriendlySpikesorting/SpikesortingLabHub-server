#!/bin/bash
# ============================================================
# SpikesortingLabHub — TrueNAS Pre-Init Script
#
# Runs BEFORE Docker daemon starts. Its only job is to ensure
# all bind-mount directories exist on the ZFS pool so that
# Docker's restart policy can bring up the container cleanly.
#
# Store this file on the NAS at:
#   /mnt/root_data_storage/users/sslh/truenas_init.sh
#
# TrueNAS UI:
#   System → Advanced Settings → Init/Shutdown Scripts → Add
#   Type: Script   When: Pre Init   Timeout: 30
# ============================================================

set -euo pipefail

LOG="/var/log/sslh_init.log"
exec >> "$LOG" 2>&1

echo "=== $(date) SpikesortingLabHub pre-init starting ==="

# ── Required bind-mount directories ───────────────────────────
REQUIRED_DIRS=(
    "/mnt/root_data_storage/users/sslh/trurnasdata"
    "/mnt/root_data_storage/users/sslh/persistentdata"
    "/mnt/root_data_storage/users/sslh/secrets"
    "/mnt/root_data_storage/users/sslh/experiments"
)

for DIR in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$DIR" ]; then
        mkdir "$DIR" && chown -R sslh "$DIR"
    fi
    echo "OK: $DIR"
done
mount -o bind,ro /data /mnt/root_data_storage/users/sslh/trurnasdata
mount -o bind,ro /mnt/root_data_storage/experiments /mnt/root_data_storage/users/sslh/experiments
echo "=== $(date) All directories present — Docker may start ==="
