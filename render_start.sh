#!/usr/bin/env bash
# ======================================================================
# Veyra - Render Cloud Startup Script
# ======================================================================
set -e

echo "======================================================================"
echo "          VEYRA - Open Warehouse Execution System                     "
echo "                 Render Cloud Startup Sequence                        "
echo "======================================================================"

PORT="${PORT:-10000}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

# Persistent or local data directory
DATA_DIR="${INVENTREE_DATA_DIR:-$APP_DIR/data}"
mkdir -p "$DATA_DIR/static" "$DATA_DIR/media" "$DATA_DIR/backup" "$DATA_DIR/plugins"

# Ensure config file exists
if [ ! -f "$DATA_DIR/config.yaml" ]; then
    if [ -f "$APP_DIR/config/config.yaml" ]; then
        echo "[*] Copying initial config from config/config.yaml"
        cp "$APP_DIR/config/config.yaml" "$DATA_DIR/config.yaml"
    elif [ -f "$APP_DIR/src/backend/InvenTree/config_template.yaml" ]; then
        echo "[*] Copying initial config from template"
        cp "$APP_DIR/src/backend/InvenTree/config_template.yaml" "$DATA_DIR/config.yaml"
    fi
fi

export INVENTREE_STATIC_ROOT="${DATA_DIR}/static"
export INVENTREE_MEDIA_ROOT="${DATA_DIR}/media"
export INVENTREE_BACKUP_DIR="${DATA_DIR}/backup"
export INVENTREE_PLUGIN_DIR="${DATA_DIR}/plugins"
export INVENTREE_PLUGIN_FILE="${DATA_DIR}/plugins.txt"
export INVENTREE_CONFIG_FILE="${DATA_DIR}/config.yaml"

# Render URL & Hostname Auto-Configuration
if [ -n "$RENDER_EXTERNAL_URL" ]; then
    echo "[*] Render External URL detected: $RENDER_EXTERNAL_URL"
    export INVENTREE_SITE_URL="$RENDER_EXTERNAL_URL"
    export INVENTREE_TRUSTED_ORIGINS="$RENDER_EXTERNAL_URL,http://localhost:$PORT,http://127.0.0.1:$PORT"
    export INVENTREE_ALLOWED_HOSTS="${RENDER_EXTERNAL_HOSTNAME:-*},localhost,127.0.0.1"
elif [ -n "$RENDER_EXTERNAL_HOSTNAME" ]; then
    echo "[*] Render External Hostname detected: $RENDER_EXTERNAL_HOSTNAME"
    export INVENTREE_SITE_URL="https://${RENDER_EXTERNAL_HOSTNAME}"
    export INVENTREE_TRUSTED_ORIGINS="https://${RENDER_EXTERNAL_HOSTNAME},http://localhost:$PORT,http://127.0.0.1:$PORT"
    export INVENTREE_ALLOWED_HOSTS="${RENDER_EXTERNAL_HOSTNAME},localhost,127.0.0.1"
else
    export INVENTREE_SITE_URL="${INVENTREE_SITE_URL:-http://localhost:$PORT}"
    export INVENTREE_TRUSTED_ORIGINS="${INVENTREE_TRUSTED_ORIGINS:-http://localhost:$PORT,http://127.0.0.1:$PORT,https://*.onrender.com}"
    export INVENTREE_ALLOWED_HOSTS="${INVENTREE_ALLOWED_HOSTS:-*.onrender.com,localhost,127.0.0.1}"
fi

# Database Auto-Detection (PostgreSQL vs SQLite)
if [ -n "$DATABASE_URL" ]; then
    echo "[*] Production PostgreSQL DATABASE_URL detected. Configuring database parameters..."
    eval "$(python3 - << 'EOF'
import os, urllib.parse
db_url = os.environ.get('DATABASE_URL', '')
if db_url.startswith('postgres://') or db_url.startswith('postgresql://'):
    parsed = urllib.parse.urlparse(db_url)
    print("export INVENTREE_DB_ENGINE='postgresql'")
    print(f"export INVENTREE_DB_NAME='{parsed.path.lstrip('/')}'")
    print(f"export INVENTREE_DB_USER='{parsed.username or ''}'")
    print(f"export INVENTREE_DB_PASSWORD='{parsed.password or ''}'")
    print(f"export INVENTREE_DB_HOST='{parsed.hostname or ''}'")
    print(f"export INVENTREE_DB_PORT='{str(parsed.port or 5432)}'")
EOF
)"
else
    echo "[*] Using persistent SQLite database at: $DATA_DIR/inventree.sqlite3"
    export INVENTREE_DB_ENGINE="sqlite3"
    export INVENTREE_DB_NAME="$DATA_DIR/inventree.sqlite3"
fi

# 1. Run database migrations
echo "[*] Running database migrations..."
python src/backend/InvenTree/manage.py migrate --no-input

# 2. Collect static files
echo "[*] Collecting static files..."
python src/backend/InvenTree/manage.py collectstatic --no-input

# 3. Seed OpenWES demo data and client evaluation user accounts
echo "[*] Ensuring OpenWES demo data and client accounts are seeded..."
python src/backend/InvenTree/manage.py seed_openwes_demo || true
python src/backend/InvenTree/manage.py seed_demo_users

echo "======================================================================"
echo "[*] Starting Veyra Gunicorn server on 0.0.0.0:$PORT..."
echo "======================================================================"

exec gunicorn --chdir src/backend/InvenTree \
    -c src/backend/InvenTree/gunicorn.conf.py \
    InvenTree.wsgi:application \
    -b "0.0.0.0:$PORT" \
    --workers 2 \
    --timeout 120
