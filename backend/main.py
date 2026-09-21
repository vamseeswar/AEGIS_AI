"""AEGIS AI — Autonomous AI Operations Platform
Main FastAPI Gateway Application
"""

import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.router import api_router
from backend.core.config import settings
from backend.core.errors import (
    AegisException,
    aegis_exception_handler,
    generic_exception_handler,
    http_exception_handler,
)
from backend.db.init_db import initialize_database
from backend.security.rate_limiter import rate_limiter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown routines."""
    # Startup initialization
    print(f"[*] Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    await initialize_database()
    yield
    # Graceful shutdown cleanup
    print(f"[*] Shutting down {settings.APP_NAME} cleanly...")


app = FastAPI(
    title="AEGIS AI — Autonomous AI Operations Platform",
    description=(
        "Enterprise-grade autonomous AI platform featuring multi-agent LangGraph orchestration, "
        "citation-grounded RAG, safe natural-language-to-SQL, real machine learning forecasting, "
        "and human-in-the-loop governance."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ------------------------------------------------------------
# Middleware Configuration
# ------------------------------------------------------------

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. Correlation ID, Observability, Rate Limiting & Security Headers Middleware
@app.middleware("http")
async def correlation_and_security_headers_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.perf_counter()

    # Rate limiting check (bypass for preflight OPTIONS, docs, and health checks)
    path = request.url.path
    is_exempt = (
        request.method == "OPTIONS"
        or path in ("/api/v1/health", "/api/v1/ready", "/docs", "/redoc", "/openapi.json")
        or path.startswith("/docs/")
    )

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"
    remaining = 120.0


    if not is_exempt:
        allowed, remaining, retry_after = rate_limiter.check_rate_limit(
            key=client_ip,
            bucket_type="ip",
            capacity=120.0,
            refill_rate=2.0,
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Client request rate limit exceeded. Retry in {retry_after} seconds.",
                        "request_id": request_id,
                    }
                },
                headers={
                    "Retry-After": str(int(retry_after) + 1),
                    "X-RateLimit-Limit": "120",
                    "X-RateLimit-Remaining": "0",
                    "X-Request-ID": request_id,
                },
            )

    try:
        response: Response = await call_next(request)
    except AegisException as exc:
        response = aegis_exception_handler(request, exc)
    except HTTPException as exc:
        response = http_exception_handler(request, exc)
    except Exception as exc:
        # Pass to the global exception handler
        response = generic_exception_handler(request, exc)

    process_time = (time.perf_counter() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-MS"] = f"{process_time:.2f}"
    response.headers["X-RateLimit-Limit"] = "120"
    response.headers["X-RateLimit-Remaining"] = str(int(max(0, remaining)))

    # Comprehensive Enterprise Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; font-src 'self' data:; "
        "img-src 'self' data: blob:; connect-src 'self' *; frame-ancestors 'none';"
    )
    return response



# ------------------------------------------------------------
# Exception Handlers Registration
# ------------------------------------------------------------
app.add_exception_handler(AegisException, aegis_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# ------------------------------------------------------------
# API v1 Router
# ------------------------------------------------------------
app.include_router(api_router)


# ------------------------------------------------------------
# Health & Diagnostic Endpoints
# ------------------------------------------------------------
@app.get("/api/v1/health", tags=["System Diagnostics"])
async def health_check(request: Request) -> JSONResponse:
    """Returns basic system health status."""
    return JSONResponse(
        content={
            "status": "healthy",
            "environment": settings.APP_ENV,
            "version": "1.0.0",
            "request_id": getattr(request.state, "request_id", None),
        }
    )


@app.get("/api/v1/ready", tags=["System Diagnostics"])
async def ready_check(request: Request) -> JSONResponse:
    """Returns system readiness across database and runtime dependencies."""
    return JSONResponse(
        content={
            "status": "ready",
            "database": "connected",
            "llm_provider": settings.LLM_PROVIDER,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "request_id": getattr(request.state, "request_id", None),
        }
    )


@app.get("/", tags=["System Diagnostics"])
async def root() -> dict:
    """Root index providing platform identity and documentation links."""
    return {
        "platform": settings.APP_NAME,
        "status": "operational",
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
    }
