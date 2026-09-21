# AEGIS AI — Container Orchestration & Docker Deployment Guide

This guide details the containerization architecture, multi-stage Docker builds, health checks, storage persistence, and Docker Compose orchestration for the AEGIS AI enterprise platform.

---

## 1. Architecture Overview

AEGIS AI is orchestrated using a three-tier container topology connected over an isolated bridge network (`aegis-network`):

```
                        ┌────────────────────────┐
                        │   Browser / Client     │
                        └───────────┬────────────┘
                                    │
                         HTTP/WS    │ Port 3000
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  aegis-network (Docker Bridge)                                         │
│                                                                        │
│  ┌────────────────────────┐              ┌──────────────────────────┐  │
│  │     aegis-frontend     │  REST/SSE    │      aegis-backend       │  │
│  │   (Next.js Standalone) │─────────────▶│    (FastAPI ASGI)        │  │
│  │   Node 20-alpine       │  Port 8000   │    Python 3.11-slim      │  │
│  │   Non-root: nextjs     │              │    Non-root: aegisuser   │  │
│  └────────────────────────┘              └─────────────┬────────────┘  │
│                                                        │               │
│                                                        │ SQL / pgvector│
│                                                        │ Port 5432     │
│                                                        ▼               │
│                                          ┌──────────────────────────┐  │
│                                          │         aegis-db         │  │
│                                          │  (PostgreSQL 16+pgvector)│  │
│                                          │  Volume: pgdata          │  │
│                                          └──────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Multi-Stage Dockerfile Designs

### Backend: `backend/Dockerfile`
- **Base Image**: `python:3.11-slim`
- **Build Stage (`builder`)**: Installs compiler tools (`gcc`, `g++`, `libpq-dev`), builds C-extensions (`asyncpg`, `pgvector`, `scikit-learn`), and caches wheels inside `/opt/venv`.
- **Runtime Stage (`runner`)**:
  - Drops build toolchains to minimize image attack surface and vulnerability count.
  - Copies clean `/opt/venv` from builder.
  - Runs under unprivileged user `aegisuser` (UID 10001, GID 10001).
  - Health check: `curl -f http://localhost:8000/api/v1/health`.
  - ASGI Server: `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2`.

### Frontend: `frontend/Dockerfile`
- **Base Image**: `node:20-alpine`
- **Dependencies Stage (`deps`)**: Caches npm packages using `npm ci` with `package-lock.json`.
- **Build Stage (`builder`)**: Executes Next.js production compilation with `output: "standalone"` enabled.
- **Runtime Stage (`runner`)**:
  - Copies only `.next/standalone`, `.next/static`, and `public/`.
  - Runs under unprivileged user `nextjs` (UID 1001, GID 1001).
  - Shrinks runtime image from >1.2GB down to ~150MB.
  - Health check: `wget -qO- http://localhost:3000/`.
  - Server: `node server.js`.

---

## 3. Quickstart & Deployment Commands

### Production Deployment
```bash
# 1. Inspect or customize environment configuration
cp .env.docker.example .env.docker

# 2. Build and launch all services in detached mode
docker compose up -d --build

# 3. Monitor live health and container status
docker compose ps

# 4. View unified logs across services
docker compose logs -f
```

### Local Development with Hot-Reloading
```bash
# Launch with development volume overrides (hot reload backend and frontend)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Stopping Containers
```bash
# Stop containers without losing database volume data
docker compose down

# Stop and wipe database data (clean slate)
docker compose down -v
```

---

## 4. Service Health Checks & Dependencies

| Service | Container Name | Port | Health Check Probe | Dependency Gate |
| :--- | :--- | :--- | :--- | :--- |
| **db** | `aegis-db` | 5432 | `pg_isready -U aegis -d aegis_ai` | None |
| **backend** | `aegis-backend` | 8000 | `curl -f http://localhost:8000/api/v1/health` | `db: service_healthy` |
| **frontend** | `aegis-frontend` | 3000 | `wget -qO- http://localhost:3000/` | `backend: service_healthy` |

---

## 5. Storage Persistence

- **`pgdata`**: Named volume mounted to `/var/lib/postgresql/data` for persistent relational tables, vector embeddings, and audit logs.
- **`aegis-storage`**: Named volume mounted to `/app/storage` for uploaded documents, chunk extractions, and compiled executive PDF reports.
