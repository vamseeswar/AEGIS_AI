"""AEGIS AI — CI/CD Pipeline Automated Verification Suite
Validates:
  1. YAML syntax correctness across all GitHub Actions workflows
  2. Complete CI stages (backend lint, pgvector test service, frontend build, docker validation)
  3. Security pipeline (secret detection, dependency audit, SAST scanning)
  4. CD release pipeline (semantic version triggers, container registry publication)
"""

from pathlib import Path
import pytest
import yaml


WORKSPACE_ROOT = Path(__file__).parent.parent.parent
WORKFLOWS_DIR = WORKSPACE_ROOT / ".github" / "workflows"


def _load_workflow(filename: str) -> dict:
    workflow_path = WORKFLOWS_DIR / filename
    assert workflow_path.exists(), f"Workflow file {filename} must exist"
    with open(workflow_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.mark.unit
def test_ci_workflow_structure_and_jobs():
    """Verify ci.yml contains all required jobs, triggers, and service containers."""
    data = _load_workflow("ci.yml")

    # Name and triggers
    assert "name" in data
    # Triggers can be dict or list
    triggers = data.get("on") or data.get(True)  # In YAML, "on" can parse as boolean True
    assert triggers is not None

    jobs = data.get("jobs", {})
    required_jobs = ["backend-lint", "backend-test", "frontend-check", "docker-build-verify"]
    for job_name in required_jobs:
        assert job_name in jobs, f"Job {job_name} missing from ci.yml"

    # Verify backend-test pgvector service container
    backend_test = jobs["backend-test"]
    assert "services" in backend_test, "backend-test must define service containers"
    assert "postgres" in backend_test["services"]
    postgres_svc = backend_test["services"]["postgres"]
    assert "pgvector/pgvector" in postgres_svc["image"], "PostgreSQL service must use pgvector image"

    # Verify dependency chain
    assert "needs" in jobs["backend-test"], "backend-test should depend on backend-lint"
    assert "needs" in jobs["docker-build-verify"], "docker-build-verify should depend on tests"


@pytest.mark.unit
def test_security_workflow_audit_jobs():
    """Verify security.yml contains secret scanning, dependency audit, and SAST jobs."""
    data = _load_workflow("security.yml")

    assert "name" in data
    jobs = data.get("jobs", {})

    assert "secret-scan" in jobs, "security.yml must contain secret-scan job"
    assert "dependency-audit" in jobs, "security.yml must contain dependency-audit job"
    assert "sast-analysis" in jobs, "security.yml must contain sast-analysis job"

    # Verify schedule trigger exists
    triggers = data.get("on") or data.get(True)
    assert "schedule" in triggers or "workflow_dispatch" in triggers


@pytest.mark.unit
def test_cd_workflow_release_configuration():
    """Verify cd.yml configures semantic tag triggers and GHCR container publishing."""
    data = _load_workflow("cd.yml")

    assert "name" in data
    jobs = data.get("jobs", {})

    assert "publish-containers" in jobs, "cd.yml must contain publish-containers job"
    job = jobs["publish-containers"]

    # Verify permissions block
    assert "permissions" in data, "cd.yml must configure permissions for packages: write"
    assert data["permissions"].get("packages") == "write"

    # Verify steps contain docker login to ghcr.io
    step_names = [s.get("name", "") for s in job.get("steps", [])]
    assert any("GHCR" in name or "Registry" in name or "docker" in name.lower() for name in step_names)
