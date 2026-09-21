#!/usr/bin/env bash
# ============================================================
# AEGIS AI — Cloud Deployment & Container Entrypoint Script
# Handles database readiness checks, migrations, and memory-conscious ASGI startup.
# ============================================================

set -e

echo "============================================================"
echo " Starting AEGIS AI Cloud Runtime"
echo " Environment: ${APP_ENV:-production}"
echo " Port:        ${PORT:-8000}"
echo " Workers:     ${WORKERS:-1}"
echo "============================================================"

# Optional wait-for-database check when using external PostgreSQL
if [[ "${DATABASE_URL}" == *"postgres"* ]]; then
    echo "[*] Verifying PostgreSQL database connectivity..."
    python - << 'EOF'
import os
import sys
import time
from urllib.parse import urlparse

db_url = os.getenv("DATABASE_URL", "")
if "postgres" in db_url:
    print(f"[*] Checking database connection parameters...")
    # Quick socket/ping check can be done via asyncpg or sqlalchemy
    try:
        from backend.core.config import settings
        from sqlalchemy import create_engine, text
        sync_url = settings.DATABASE_URL_SYNC
        engine = create_engine(sync_url, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        print("[+] PostgreSQL database is online and reachable!")
    except Exception as exc:
        print(f"[!] Warning: Initial database check notice: {exc}")
        print("[*] Proceeding with startup sequence...")
EOF
fi

# Run database migrations
echo "[*] Running database schema migrations (Alembic)..."
alembic upgrade head || {
    echo "[!] Alembic upgrade head exited with status $?. Continuing with startup..."
}

# Run seed and initialization routines
echo "[*] Verifying system default roles, permissions, and admin user..."
python -c "
import asyncio
from backend.db.init_db import initialize_database
asyncio.run(initialize_database())
print('[+] Database initialization and seeding complete.')
"

# Launch ASGI server with dynamic port and memory-conscious worker configuration
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-1}"
LOG_LEVEL="${LOG_LEVEL:-info}"

echo "[*] Launching uvicorn on 0.0.0.0:${PORT} with ${WORKERS} worker(s)..."
exec uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --workers "${WORKERS}" \
    --log-level "${LOG_LEVEL}"
