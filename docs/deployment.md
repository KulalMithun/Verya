# 🚀 Veyra Deployment Guide

This guide covers recommended strategies for deploying **Veyra (v1.0)** across different operational environments:
1. **Standalone Windows Executable (`.exe`)** — Ideal for single-facility on-premise deployments, edge servers, or offline rugged tablets.
2. **Docker Container Stack** — Ideal for cloud, on-prem Kubernetes, or microservices infrastructure with PostgreSQL and Redis.
3. **Traditional Linux WSGI / Gunicorn Deployment** — High-concurrency enterprise Linux server deployment behind Nginx.

---

## 1. Standalone Windows Executable Deployment

Veyra packages its entire stack (Django application, OpenWES engines, built React SPA, static assets, templates, and pre-seeded SQLite database) into a single Windows executable: **`dist\Veyra.exe`**.

### Building the Executable
On your build machine, run:
```cmd
build.bat
```
*(Or `python build.py`)*

### Distribution & Execution
1. Copy `dist\Veyra.exe` to the target server or kiosk.
2. Launch `Veyra.exe`:
   ```cmd
   Veyra.exe
   ```
3. Persistent storage: Veyra automatically maintains all warehouse transactions, sqlite database, and uploaded documents in a `./data` folder created adjacent to `Veyra.exe`.
4. Custom CLI options:
   ```cmd
   Veyra.exe --port 8080 --host 0.0.0.0 --no-browser
   ```

---

## 2. Docker Container Deployment

For containerized cloud environments (AWS ECS, GCP Cloud Run, Azure Container Apps, or local Docker Compose):

### Environment Configuration (`.env`)
```ini
INVENTREE_SECRET_KEY=generate-a-strong-random-key-for-production
INVENTREE_DB_ENGINE=postgresql
INVENTREE_DB_NAME=veyra_db
INVENTREE_DB_USER=veyra_user
INVENTREE_DB_PASSWORD=strong-database-password
INVENTREE_DB_HOST=postgres
INVENTREE_DB_PORT=5432
INVENTREE_CACHE_HOST=redis
INVENTREE_CACHE_PORT=6379
INVENTREE_SITE_URL=https://warehouse.example.com
INVENTREE_DEBUG=False
```

### Docker Compose Stack (`docker-compose.prod.yml`)
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: veyra_db
      POSTGRES_USER: veyra_user
      POSTGRES_PASSWORD: strong-database-password
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redisdata:/data

  veyra-server:
    build: .
    restart: unless-stopped
    env_file: .env
    depends_on:
      - postgres
      - redis
    volumes:
      - media:/home/inventree/data/media
    ports:
      - "8000:8000"
    command: gunicorn -w 4 -b 0.0.0.0:8000 InvenTree.wsgi:application

volumes:
  pgdata:
  redisdata:
  media:
```

Launch the stack:
```bash
docker compose -f docker-compose.prod.yml up -d
```

---

## 3. Production Linux Server (WSGI + Gunicorn + Nginx)

### System Requirements
- OS: Ubuntu 22.04 LTS / 24.04 LTS / Debian 12 / RHEL 9
- Python 3.11, 3.12, or 3.13
- PostgreSQL 14+
- Nginx reverse proxy with SSL termination

### Application Setup
1. Clone the repository and navigate to root:
   ```bash
   git clone <repo-url> /opt/veyra
   cd /opt/veyra
   ```
2. Create and activate virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r src/backend/requirements.txt
   ```
3. Initialize configuration:
   ```bash
   cp config/config.yaml config/config.prod.yaml
   ```
4. Run migrations and collect static assets:
   ```bash
   python src/backend/InvenTree/manage.py migrate --noinput
   python src/backend/InvenTree/manage.py collectstatic --noinput
   ```

### Systemd Service (`/etc/systemd/system/veyra.service`)
```ini
[Unit]
Description=Veyra Warehouse Execution System WSGI Service
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/veyra/src/backend/InvenTree
Environment="PATH=/opt/veyra/.venv/bin"
Environment="DJANGO_SETTINGS_MODULE=InvenTree.settings"
ExecStart=/opt/veyra/.venv/bin/gunicorn \
          --workers 4 \
          --threads 2 \
          --bind 127.0.0.1:8000 \
          --timeout 120 \
          InvenTree.wsgi:application

[Install]
WantedBy=multi-user.target
```

### Nginx Configuration (`/etc/nginx/sites-available/veyra.conf`)
```nginx
server {
    listen 80;
    server_name warehouse.yourcompany.com;

    client_max_body_size 50M;

    location /static/ {
        alias /opt/veyra/data/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location /media/ {
        alias /opt/veyra/data/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now veyra
sudo systemctl restart nginx
```

---

## 4. Deploying to Render (Cloud Demo & Production)

Veyra includes native, zero-configuration support for deploying directly to [Render](https://render.com/).

### Method A: 1-Click Blueprint (Recommended)
1. Push this repository to your GitHub or GitLab account.
2. In your Render Dashboard, click **New +** -> **Blueprint**.
3. Select your repository. Render will automatically detect [`render.yaml`](file:///c:/Users/MITHUN/Documents/Projects/Veyra/render.yaml).
4. Click **Apply**. Render will automatically build the container, attach persistent storage, run migrations, seed client demo accounts, and launch the service!

### Method B: Manual Web Service (Docker)
1. In Render Dashboard, click **New +** -> **Web Service**.
2. Connect your Git repository.
3. Select **Docker** as the runtime.
4. Set Environment Variables:
   - `PORT`: `10000`
   - `INVENTREE_DEBUG`: `False`
5. (Optional) Add a Persistent Disk mounted at `/home/inventree/data` (10 GB).
6. Click **Deploy Web Service**.

### Method C: Manual Web Service (Native Python)
1. In Render Dashboard, click **New +** -> **Web Service**.
2. Select **Python** as the runtime.
3. Set:
   - **Build Command**: `chmod +x render_build.sh && ./render_build.sh`
   - **Start Command**: `chmod +x render_start.sh && ./render_start.sh`
4. Deploy.

---

## 5. Administrator Access & Persistence

When Veyra starts for the first time, it initializes a brand new, clean database with no dummy records. 

| Username | Default Password | Role & Access Level | Description |
| :--- | :--- | :--- | :--- |
| **`admin`** | `admin123` | **Full Superuser** | Complete administrative control over system & warehouse operations |

> [!NOTE]
> Database records are persisted in the configured persistent disk volume (`/home/inventree/data` on Docker/Render or external PostgreSQL). Whenever you restart or deploy, your existing data is fully preserved.

