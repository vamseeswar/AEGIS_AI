# ============================================================
# AEGIS AI — Backend Production Dockerfile for Cloud & Hugging Face Spaces
# 100% Free-Tier Compatible (Port 7860 default / $PORT dynamic)
# ============================================================

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app" \
    APP_ENV="production" \
    PORT=7860

WORKDIR /app

# Install system dependencies including PostgreSQL client libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    libpq5 \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create standard non-root user (UID 1000 for Hugging Face Spaces)
RUN useradd -m -u 1000 user && \
    mkdir -p /app/storage /app/logs && \
    chown -R user:user /app

COPY --chown=user:user backend /app/backend
COPY --chown=user:user ml /app/ml

USER user

EXPOSE 7860

# Run uvicorn on port 7860 (Hugging Face default) with 2 workers for concurrency
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 2 --log-level info"]
