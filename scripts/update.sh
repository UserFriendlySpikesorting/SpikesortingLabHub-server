#!/usr/bin/env bash
# Applies every kind of change in one go: DB migrations, frontend build, static files.
# Safe to run any time, whether or not anything changed.
# Usage:  ./scripts/update.sh
set -euo pipefail

cd "$(dirname "$0")/.."   # project root (where manage.py lives)

if [ -f venv/bin/activate ]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

echo "==> 1/3 Database migrations"
python manage.py migrate

echo "==> 2/3 Frontend build (my-app -> labhub/templates)"
(
    cd my-app
    [ -d node_modules ] || npm ci
    npm run build
)

echo "==> 3/3 Collect static files"
python manage.py collectstatic --noinput

echo
echo "Done. Restart the server, then hard-refresh the browser (Cmd+Shift+R)."
