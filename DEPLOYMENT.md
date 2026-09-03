# TrustDNA Production Deployment Guide

This guide details how to deploy TrustDNA in high-availability production environments using Docker Compose, Kubernetes, or major cloud platforms (AWS, Render, Railway, Fly.io, DigitalOcean).

---

## 🏛️ Production Architecture Overview

```
                                 INTERNET / CLIENT APPS
                                           │
                        ┌──────────────────▼──────────────────┐
                        │        Nginx Gateway / CDN         │
                        │    (Port 80 / 443 SSL Caching)     │
                        └─────────┬─────────────────┬────────┘
                                  │                 │
              /v1/trustdna.js & UI│                 │ /api/v1/* Reverse Proxy
                                  │                 │
                        ┌─────────▼──────┐   ┌──────▼────────────────┐
                        │ Static Assets  │   │ TrustDNA API Cluster  │
                        │ (HTML/CSS/JS)  │   │ (Gunicorn + 4 Workers)│
                        └────────────────┘   └──────┬──────────┬─────┘
                                                    │          │
                                       PostgreSQL 16│          │Redis 7
                                     (Persistent DB)│          │(Velocity)
                                             ┌──────▼────┐ ┌───▼───────┐
                                             │ Postgres  │ │   Redis   │
                                             │  Volume   │ │  Volume   │
                                             └───────────┘ └───────────┘
```

---

## 🚀 Option 1: 1-Click Launch with Docker Compose (Recommended)

### 1. Clone & Configure Environment
```bash
git clone https://github.com/DamaMichaelYohanna/trustDNA.git
cd trustDNA

# Copy production environment template
cp .env.example .env

# Edit .env with your production secrets
nano .env
```

### 2. Build and Start Multi-Container Stack
```bash
docker compose up -d --build
```

### 3. Verify Container Health
```bash
docker compose ps

# Inspect API health endpoint
curl http://localhost/api/v1/health
```

Expected Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "engine": "TrustDNA Heuristic Rule Engine (Stage 2 Multi-Tenant)",
  "velocity_store": "Distributed Redis",
  "active_tenants": 1
}
```

---

## ☁️ Option 2: Cloud Platform Deployments

### A. Render.com
1. Create a new **Web Service** linked to your TrustDNA repository.
2. Select **Docker** environment (Render automatically reads `Dockerfile`).
3. Add a **Managed PostgreSQL** and **Managed Redis** instance from the Render dashboard.
4. Set Environment Variables in Render:
   - `DATABASE_URL`: Set to Render Postgres Internal Connection String.
   - `REDIS_URL`: Set to Render Redis Internal Connection String.
   - `TOKEN_SECRET`: A secure 32+ character hex string.

### B. Railway.app
1. Click **New Project** $\rightarrow$ **Deploy from GitHub repo**.
2. Add a **PostgreSQL** and **Redis** database plugin.
3. Railway will inject `DATABASE_URL` and `REDIS_URL` automatically.
4. Expose port `8000`.

### C. Fly.io
1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Launch app: `fly launch`
3. Attach Postgres & Redis:
   ```bash
   fly postgres create --name trustdna-db
   fly postgres attach trustdna-db
   fly redis create --name trustdna-redis
   ```
4. Deploy: `fly deploy`

---

## 🔒 SSL / TLS Configuration (Let's Encrypt / Certbot)

If deploying directly to a Linux Virtual Machine (AWS EC2, DigitalOcean Droplet, Ubuntu Server):

```bash
# 1. Install Certbot
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx

# 2. Issue Certificate for your domain
sudo certbot --nginx -d trustdna.yourdomain.com
```

---

## 🛡️ Database Backups & Maintenance

### PostgreSQL Automated Backup (Cron)
```bash
# Nightly backup script
docker exec -t trustdna-postgres pg_dump -U postgres trustdna | gzip > /backups/trustdna_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restore Database
```bash
gunzip < /backups/trustdna_backup.sql.gz | docker exec -i trustdna-postgres psql -U postgres -d trustdna
```

---

## 📊 Observability & Health Probes

| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `/api/v1/health` | `GET` | Container liveness & readiness check |
| `/api/v1/audit/recent` | `GET` | Global audit trail inspector |
| `/docs` | `GET` | Interactive OpenAPI documentation |
