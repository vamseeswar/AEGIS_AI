"""AEGIS AI — Docker & Container Orchestration Automated Verification Suite
Validates:
  1. Multi-stage Dockerfile structural rules (builder/runner stages, non-root users, healthchecks)
  2. docker-compose.yml service topology (db with pgvector, backend, frontend, healthcheck conditions)
  3. Security ignore rules (.dockerignore files excluding sensitive tokens and virtual environments)
  4. Environment parameterization (.env.docker and .env.docker.example matching database URLs)
"""

from pathlib import Path
import pytest


WORKSPACE_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.unit
def test_backend_dockerfile_multi_stage_structure():
    """Verify backend Dockerfile implements secure multi-stage builds with non-root user."""
    dockerfile_path = WORKSPACE_ROOT / "backend" / "Dockerfile"
    assert dockerfile_path.exists(), "backend/Dockerfile must exist"

    content = dockerfile_path.read_text(encoding="utf-8")

    # Multi-stage checks
    assert "AS builder" in content, "Backend Dockerfile must feature a builder stage"
    assert "AS runner" in content, "Backend Dockerfile must feature a runner stage"

    # Security: Non-root user checks
    assert "useradd" in content or "adduser" in content, "Must create dedicated unprivileged user"
    assert "USER aegisuser" in content, "Must drop privileges to aegisuser in runner stage"

    # Healthcheck & network
    assert "HEALTHCHECK" in content, "Must define automated container health check"
    assert "EXPOSE 8000" in content, "Must expose port 8000"
    assert "uvicorn" in content, "Must launch uvicorn ASGI server"


@pytest.mark.unit
def test_frontend_dockerfile_multi_stage_structure():
    """Verify frontend Dockerfile implements Next.js standalone multi-stage builds."""
    dockerfile_path = WORKSPACE_ROOT / "frontend" / "Dockerfile"
    assert dockerfile_path.exists(), "frontend/Dockerfile must exist"

    content = dockerfile_path.read_text(encoding="utf-8")

    # Multi-stage checks
    assert "AS deps" in content, "Frontend Dockerfile must feature deps stage"
    assert "AS builder" in content, "Frontend Dockerfile must feature builder stage"
    assert "AS runner" in content, "Frontend Dockerfile must feature runner stage"

    # Next.js standalone optimizations
    assert ".next/standalone" in content, "Must copy .next/standalone for lightweight image"
    assert "USER nextjs" in content, "Must run under unprivileged nextjs user"

    # Healthcheck & network
    assert "HEALTHCHECK" in content, "Must define automated container health check"
    assert "EXPOSE 3000" in content, "Must expose port 3000"
    assert "server.js" in content, "Must execute node server.js"


@pytest.mark.unit
def test_docker_compose_topology_and_health_gates():
    """Verify docker-compose.yml defines all 3 services with health check dependencies."""
    compose_path = WORKSPACE_ROOT / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist"

    content = compose_path.read_text(encoding="utf-8")

    # Required services
    assert "db:" in content, "Compose must define db service"
    assert "backend:" in content, "Compose must define backend service"
    assert "frontend:" in content, "Compose must define frontend service"

    # pgvector database specification
    assert "pgvector/pgvector:pg16" in content, "db service must use pgvector PostgreSQL 16 image"

    # Dependency gates
    assert "condition: service_healthy" in content, "Must enforce healthy dependency conditions"

    # Port mappings
    assert '"5432:5432"' in content or "'5432:5432'" in content or "- 5432:5432" in content
    assert '"8000:8000"' in content or "'8000:8000'" in content or "- 8000:8000" in content
    assert '"3000:3000"' in content or "'3000:3000'" in content or "- 3000:3000" in content

    # Volumes and networks
    assert "pgdata:" in content, "Must define persistent pgdata volume"
    assert "aegis-storage:" in content, "Must define persistent storage volume"
    assert "aegis-network:" in content, "Must define isolated bridge network"


@pytest.mark.unit
def test_dockerignore_security_exclusions():
    """Verify .dockerignore exclusions prevent credential and artifact leaks."""
    root_ignore = WORKSPACE_ROOT / ".dockerignore"
    frontend_ignore = WORKSPACE_ROOT / "frontend" / ".dockerignore"

    assert root_ignore.exists(), "Root .dockerignore must exist"
    assert frontend_ignore.exists(), "Frontend .dockerignore must exist"

    root_text = root_ignore.read_text(encoding="utf-8")
    assert "__pycache__" in root_text
    assert ".pytest_cache" in root_text
    assert ".env" in root_text

    frontend_text = frontend_ignore.read_text(encoding="utf-8")
    assert "node_modules" in frontend_text
    assert ".next" in frontend_text


@pytest.mark.unit
def test_docker_environment_parity():
    """Verify .env.docker and .env.docker.example have synchronized essential keys."""
    env_docker = WORKSPACE_ROOT / ".env.docker"
    env_example = WORKSPACE_ROOT / ".env.docker.example"

    assert env_docker.exists(), ".env.docker must exist"
    assert env_example.exists(), ".env.docker.example must exist"

    docker_text = env_docker.read_text(encoding="utf-8")
    example_text = env_example.read_text(encoding="utf-8")

    essential_keys = [
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "DATABASE_URL",
        "JWT_SECRET_KEY",
        "NEXT_PUBLIC_API_URL",
        "RATE_LIMIT_ENABLED",
    ]

    for key in essential_keys:
        assert f"{key}=" in docker_text, f"{key} missing in .env.docker"
        assert f"{key}=" in example_text, f"{key} missing in .env.docker.example"
