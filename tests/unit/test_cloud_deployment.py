"""AEGIS AI — Free-Tier Cloud Deployment Automated Verification Suite
Validates:
  1. render.yaml Blueprint syntax, service declarations, databases, and environment parameters
  2. railway.json configuration syntax, Dockerfile builder, and health check settings
  3. Database URL normalizers for cloud PostgreSQL (Neon, Supabase, Render)
  4. Cloud entrypoint scripts and memory-conscious concurrency configurations
  5. Frontend health probe route handler
  6. Cloud deployment documentation completeness
"""

import json
from pathlib import Path
import pytest
import yaml

from backend.core.config import Settings

WORKSPACE_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.unit
def test_render_blueprint_schema_and_services():
    """Verify render.yaml contains valid YAML and declares backend, frontend, and database."""
    blueprint_path = WORKSPACE_ROOT / "render.yaml"
    assert blueprint_path.exists(), "render.yaml must exist in root"

    content = blueprint_path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    assert isinstance(data, dict), "render.yaml must parse as a dictionary"
    assert "services" in data, "render.yaml must define services"
    assert "databases" in data, "render.yaml must define databases"

    # Verify services
    services = {s["name"]: s for s in data["services"]}
    assert "aegis-backend" in services, "Must declare aegis-backend web service"
    assert "aegis-frontend" in services, "Must declare aegis-frontend web service"

    backend = services["aegis-backend"]
    assert backend["type"] == "web"
    assert backend["plan"] == "free"
    assert backend["runtime"] == "docker"
    assert backend["healthCheckPath"] == "/api/v1/health"
    assert "disk" in backend, "Backend must configure persistent disk for document storage"
    assert backend["disk"]["mountPath"] == "/app/storage"

    # Verify backend envVars
    backend_env_keys = [
        item["key"] for item in backend["envVars"] if "key" in item
    ]
    required_keys = [
        "APP_NAME",
        "APP_ENV",
        "PORT",
        "DATABASE_URL",
        "SECRET_KEY",
        "JWT_SECRET",
        "LLM_PROVIDER",
        "CORS_ORIGINS",
        "RATE_LIMIT_ENABLED",
    ]
    for key in required_keys:
        assert key in backend_env_keys, f"Missing {key} in aegis-backend envVars"

    frontend = services["aegis-frontend"]
    assert frontend["type"] == "web"
    assert frontend["plan"] == "free"
    assert frontend["runtime"] == "docker"
    assert frontend["healthCheckPath"] == "/api/health"

    # Verify database
    databases = {d["name"]: d for d in data["databases"]}
    assert "aegis-db" in databases, "Must declare aegis-db"
    db = databases["aegis-db"]
    assert db["plan"] == "free"
    assert db["databaseName"] == "aegis_ai"
    assert db["postgresMajorVersion"] == "16"


@pytest.mark.unit
def test_railway_configuration_schema():
    """Verify railway.json declares valid configuration and healthcheck."""
    railway_path = WORKSPACE_ROOT / "railway.json"
    assert railway_path.exists(), "railway.json must exist in root"

    content = railway_path.read_text(encoding="utf-8")
    data = json.loads(content)

    assert "build" in data, "railway.json must define build block"
    assert data["build"]["builder"] == "DOCKERFILE"
    assert "deploy" in data, "railway.json must define deploy block"
    assert data["deploy"]["healthcheckPath"] == "/api/v1/health"


@pytest.mark.unit
def test_database_url_cloud_normalizers():
    """Verify Settings normalizes postgres://, postgresql://, and sslmode for asyncpg."""
    # 1. Neon connection string with sslmode=require
    neon_url = "postgres://user:secret@ep-cool-fog.us-east-2.aws.neon.tech/neondb?sslmode=require"
    s1 = Settings(DATABASE_URL=neon_url, DATABASE_URL_SYNC=neon_url)
    assert s1.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert "ssl=require" in s1.DATABASE_URL
    assert "sslmode=" not in s1.DATABASE_URL
    assert s1.DATABASE_URL_SYNC.startswith("postgresql://")

    # 2. Standard postgresql:// scheme
    pg_url = "postgresql://aegisuser:pass123@dpg-abc-a.oregon-postgres.render.com/aegis_ai"
    s2 = Settings(DATABASE_URL=pg_url, DATABASE_URL_SYNC=pg_url)
    assert s2.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert s2.DATABASE_URL_SYNC.startswith("postgresql://")

    # 3. Connection pooling defaults
    assert s2.DB_POOL_SIZE == 5
    assert s2.DB_MAX_OVERFLOW == 2
    assert s2.DB_POOL_TIMEOUT == 30


@pytest.mark.unit
def test_cloud_scripts_and_frontend_health():
    """Verify cloud entrypoint scripts and frontend health route handler exist."""
    start_cloud = WORKSPACE_ROOT / "scripts" / "start_cloud.sh"
    deploy_cloud = WORKSPACE_ROOT / "scripts" / "deploy_cloud.sh"
    frontend_health = WORKSPACE_ROOT / "frontend" / "src" / "app" / "api" / "health" / "route.ts"

    assert start_cloud.exists(), "scripts/start_cloud.sh must exist"
    assert deploy_cloud.exists(), "scripts/deploy_cloud.sh must exist"
    assert frontend_health.exists(), "frontend/src/app/api/health/route.ts must exist"

    start_content = start_cloud.read_text(encoding="utf-8")
    assert "alembic upgrade head" in start_content
    assert "initialize_database" in start_content
    assert "exec uvicorn" in start_content
    assert "${PORT:-8000}" in start_content

    route_content = frontend_health.read_text(encoding="utf-8")
    assert "export async function GET" in route_content
    assert "aegis-frontend" in route_content


@pytest.mark.unit
def test_deployment_documentation_completeness():
    """Verify docs/deployment-free-tier.md contains diagrams, guides, and checklists."""
    doc_path = WORKSPACE_ROOT / "docs" / "deployment-free-tier.md"
    assert doc_path.exists(), "docs/deployment-free-tier.md must exist"

    doc_text = doc_path.read_text(encoding="utf-8")
    assert "flowchart TD" in doc_text, "Must include Mermaid cloud architecture diagram"
    assert "Neon.tech" in doc_text, "Must document Neon.tech serverless postgres"
    assert "render.yaml" in doc_text, "Must document Render blueprint"
    assert "UptimeRobot" in doc_text or "cron-job" in doc_text, "Must document cold-start mitigation"
    assert "512MB RAM" in doc_text, "Must document memory optimization"
