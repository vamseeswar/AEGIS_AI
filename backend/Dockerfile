# ============================================================
# AEGIS AI — Backend Production Dockerfile (Multi-Stage)
# Optimized for Python 3.11, asyncpg, pgvector, and security.
# ============================================================

# Stage 1: Build & Dependency Wheel Compilation
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build dependencies for C-extensions (asyncpg, pgvector, scikit-learn)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install pinned requirements
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# Stage 2: Hardened Minimal Production Runtime
FROM python:3.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    APP_ENV="production"

# Install minimal runtime dependencies (libpq for postgres client, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Security: Create unprivileged system group and user
RUN groupadd -g 10001 aegisgroup && \
    useradd -u 10001 -g aegisgroup -m -s /bin/bash aegisuser

# Copy virtualenv from builder stage
COPY --from=builder --chown=aegisuser:aegisgroup /opt/venv /opt/venv

WORKDIR /app

# Prepare storage, logs, and cache directories with proper ownership
RUN mkdir -p /app/storage /app/logs && \
    chown -R aegisuser:aegisgroup /app

# Copy application source code
COPY --chown=aegisuser:aegisgroup backend /app/backend
COPY --chown=aegisuser:aegisgroup ml /app/ml

# Drop privileges to non-root user
USER aegisuser

# Network exposition
EXPOSE 8000

# Automated container healthcheck
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Launch production ASGI server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--log-level", "info"]
