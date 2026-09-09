# ======================================================================
# Veyra - Cloud Production Dockerfile (Render, Fly.io, AWS, VPS)
# ======================================================================

# --- Stage 1: Build React SPA Frontend ---
FROM node:20-slim AS frontend_builder

WORKDIR /build/src/frontend
COPY src/frontend/package*.json ./
RUN npm install --legacy-peer-deps

COPY src/frontend/ ./
RUN npm run build


# --- Stage 2: Python Backend & Gunicorn Server ---
FROM python:3.12-slim AS runner

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    INVENTREE_DOCKER="true" \
    INVENTREE_HOME="/home/inventree" \
    INVENTREE_DATA_DIR="/home/inventree/data" \
    INVENTREE_STATIC_ROOT="/home/inventree/data/static" \
    INVENTREE_MEDIA_ROOT="/home/inventree/data/media" \
    INVENTREE_BACKUP_DIR="/home/inventree/data/backup" \
    INVENTREE_PLUGIN_DIR="/home/inventree/data/plugins" \
    INVENTREE_PLUGIN_FILE="/home/inventree/data/plugins.txt" \
    INVENTREE_SITE_URL="http://localhost:10000" \
    INVENTREE_TRUSTED_ORIGINS="http://localhost:10000,http://127.0.0.1:10000" \
    INVENTREE_SECRET_KEY="veyra-insecure-build-secret-key-change-me" \
    PORT=10000

# Install system dependencies (including database clients, fonts, graphics libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    git \
    gettext \
    libpango-1.0-0 \
    libcairo2 \
    poppler-utils \
    fonts-freefont-ttf \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${INVENTREE_HOME}

# Copy and install python dependencies
COPY src/backend/requirements.in ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.in gunicorn psycopg2-binary

# Copy full application code
COPY . .

# Copy compiled React frontend bundle from Stage 1
COPY --from=frontend_builder /build/src/backend/InvenTree/web/static/web ./src/backend/InvenTree/web/static/web

# Ensure scripts have execution permissions, directories are initialized, and pre-collect static assets at build time
RUN chmod +x ./render_start.sh ./render_build.sh && \
    mkdir -p ${INVENTREE_DATA_DIR}/static ${INVENTREE_DATA_DIR}/media ${INVENTREE_DATA_DIR}/backup ${INVENTREE_DATA_DIR}/plugins /home/inventree/contrib/template_data/static && \
    INVENTREE_STATIC_ROOT="/home/inventree/contrib/template_data/static" \
    INVENTREE_DB_ENGINE="sqlite3" \
    INVENTREE_DB_NAME="/tmp/build.sqlite3" \
    python src/backend/InvenTree/manage.py collectstatic --no-input && \
    rm -rf /tmp/build.sqlite3 /home/inventree/data/*

EXPOSE ${PORT}

CMD ["./render_start.sh"]
