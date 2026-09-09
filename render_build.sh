#!/usr/bin/env bash
# ======================================================================
# Veyra - Render Cloud Native Build Script
# ======================================================================
set -e

echo "======================================================================"
echo "          VEYRA - Building for Render Web Service                     "
echo "======================================================================"

echo "[*] Upgrading pip, setuptools, and wheel..."
python -m pip install --upgrade pip setuptools wheel

echo "[*] Installing backend dependencies..."
pip install -r src/backend/requirements.in
pip install gunicorn psycopg2-binary

# If npm is available in the build environment, build the frontend
if command -v npm &> /dev/null; then
    echo "[*] Building React SPA frontend with npm..."
    cd src/frontend
    npm install --legacy-peer-deps
    npm run build
    cd ../..
    echo "[*] Frontend assets built successfully."
else
    echo "[*] Node/npm not present in environment. Relying on pre-built assets."
fi

# Ensure data and static directories exist
mkdir -p data/static data/media data/backup

echo "[*] Collecting static files..."
python src/backend/InvenTree/manage.py collectstatic --no-input

echo "======================================================================"
echo "          RENDER BUILD COMPLETED SUCCESSFULLY                         "
echo "======================================================================"
