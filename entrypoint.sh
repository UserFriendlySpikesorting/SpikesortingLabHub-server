#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
info() { echo "$1"; }


# =============================================================================
# 1. Check the database directory (mounted from persistentdata on the host)
# =============================================================================
DB_PATH="${DATABASE_PATH:-/app/django_db/db.sqlite3}"
DB_DIR="$(dirname "$DB_PATH")"

# mkdir -p "$DB_DIR"

if [ -f "$DB_PATH" ]; then
    ok "SQLite database exists: $DB_PATH"
else
    warn "SQLite database not found: $DB_PATH"
    info "Creating SQLite DB via Django migrations..."

    python manage.py migrate --noinput

    ok "SQLite database created and migrations applied."
fi

# =============================================================================
# 2. Generate SSL certificate if not already present
# =============================================================================
# mkdir -p /app/secrets

if [ -f "/app/secrets/cert.crt" ] && [ -f "/app/secrets/cert.key" ]; then
    ok "SSL certificates already exist — leaving untouched."
else
    echo "Generating self-signed TLS certificate into /app/secrets/..."

    SERVER_HOST=$(hostname -f 2>/dev/null || hostname)
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    [ -z "$SERVER_IP" ] && SERVER_IP="127.0.0.1"

    openssl req -x509 -newkey rsa:4096 \
        -keyout /app/secrets/cert.key \
        -out    /app/secrets/cert.crt \
        -days   365 -nodes \
        -subj   "/CN=${SERVER_HOST}" \
        -addext "subjectAltName=DNS:${SERVER_HOST},IP:${SERVER_IP},DNS:localhost,IP:127.0.0.1"

    ok "Certificate created (CN=${SERVER_HOST}, IP=${SERVER_IP})"
fi

# =============================================================================
# 3. Collect static files — needs DJANGO_SECRET_KEY from the environment.
# =============================================================================
python manage.py collectstatic --noinput

# =============================================================================
# 4. Run database migrations — safe to run repeatedly.
# =============================================================================
python manage.py migrate --noinput

# =============================================================================
# 5. Hand off to the main process (Gunicorn).
# =============================================================================
exec "$@"
