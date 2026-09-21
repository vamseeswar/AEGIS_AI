# AEGIS AI — Continuous Integration & Continuous Delivery (CI/CD) Pipeline Guide

This document describes the automated CI/CD pipelines, security scanning gates, and container release workflows configured for the AEGIS AI platform using GitHub Actions.

---

## 1. Pipeline Topology & Workflow Architecture

The CI/CD system consists of three dedicated workflows:

```
                                  GIT PUSH / PR
                                        │
           ┌────────────────────────────┼───────────────────────────┐
           │                            │                           │
           ▼                            ▼                           ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│     ci.yml (CI)       │   │   security.yml (SAST) │   │     cd.yml (CD)       │
│                       │   │                       │   │                       │
│ 1. backend-lint       │   │ 1. secret-scan        │   │ Triggers on:          │
│    (Ruff lint & fmt)  │   │    (Gitleaks)         │   │ - Tagged release      │
│          │            │   │          │            │   │   (v*.*.*)            │
│          ▼            │   │          ▼            │   │ - Manual dispatch     │
│ 2. backend-test       │   │ 2. dependency-audit   │   │                       │
│    (PostgreSQL+vector,│   │    (pip-audit, npm)   │   │ 1. Build & Push       │
│     pytest, coverage) │   │          │            │   │    Backend to GHCR    │
│          │            │   │          ▼            │   │ 2. Build & Push       │
│          ▼            │   │ 3. sast-analysis      │   │    Frontend to GHCR   │
│ 3. frontend-check     │   │    (Bandit SAST)      │   └───────────────────────┘
│    (ESLint, Next.js)  │   └───────────────────────┘
│          │            │
│          ▼            │
│ 4. docker-build-verify│
│    (Compose validate, │
│     Docker Buildx)    │
└───────────────────────┘
```

---

## 2. Workflows Specification

### 1. Continuous Integration (`.github/workflows/ci.yml`)
- **Triggers**: Pushes and Pull Requests targeting `main`, `master`, and `develop`.
- **Concurrency**: Cancels stale in-progress runs for the same branch or PR to optimize build resources.
- **Jobs**:
  1. **`backend-lint`**: Enforces PEP 8, import sorting, and code formatting rules using Ruff.
  2. **`backend-test`**: Boots a dedicated `pgvector/pgvector:pg16` service container with health checks, installs dependencies, and runs the complete pytest test suite with coverage tracking (`coverage.xml` artifact).
  3. **`frontend-check`**: Validates TypeScript types, runs ESLint, and compiles the Next.js production standalone bundle.
  4. **`docker-build-verify`**: Validates `docker compose config` syntax and compiles both backend and frontend Docker containers with Docker Buildx.

### 2. Automated Security & Audit (`.github/workflows/security.yml`)
- **Triggers**: Pull requests to main branches, weekly scheduled cron run (`0 4 * * 1`), and manual dispatch.
- **Jobs**:
  1. **`secret-scan`**: Scans git commit history for accidental API key, private key, or credential leaks using Gitleaks.
  2. **`dependency-audit`**: Checks known CVE databases for Python (`pip-audit`) and Node.js (`npm audit`) dependencies.
  3. **`sast-analysis`**: Runs Bandit static analysis on the Python codebase to detect potential security flaws (e.g. injection, weak hashing, debug settings).

### 3. Continuous Delivery & Container Release (`.github/workflows/cd.yml`)
- **Triggers**: Semantic version tags (e.g. `v1.0.0`) and manual workflow dispatch.
- **Permissions**: Automatic authentication to GitHub Container Registry (`ghcr.io`) via `GITHUB_TOKEN`.
- **Artifacts**:
  - `ghcr.io/<org>/backend:<tag>`
  - `ghcr.io/<org>/frontend:<tag>`

---

## 3. GitHub Secrets & Variables Configuration

When setting up a self-hosted or production deployment, configure the following secrets in **Settings > Secrets and variables > Actions**:

| Secret / Variable Name | Purpose | Default / Example Value |
| :--- | :--- | :--- |
| `DATABASE_URL` | Production PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `JWT_SECRET_KEY` | Production JWT signing secret | 64-character random string |
| `GEMINI_API_KEY` | Google Gemini 1.5 Pro / Flash API Key | `AIzaSy...` |
| `NEXT_PUBLIC_API_URL` | Public API endpoint for web client | `https://api.aegis-ai.example.com/api/v1` |

---

## 4. Recommended Branch Protection Rules

To maintain high code quality and enterprise security standards, configure the following branch protection rules for `main`:

1. **Require pull request reviews before merging**: Minimum 1 approved review.
2. **Require status checks to pass before merging**:
   - `backend-lint`
   - `backend-test`
   - `frontend-check`
   - `docker-build-verify`
3. **Require linear history**: Squash or rebase merges to maintain a clean git log.
4. **Include administrators**: Enforce rules on all team members.
