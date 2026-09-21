# AEGIS AI — Autonomous AI Operations Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js 14](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791.svg)](https://www.postgresql.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_AI-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**AEGIS AI** is a production-grade, enterprise-ready Autonomous AI Operations Platform. It integrates structured business intelligence (Natural Language to SQL), unstructured document research (RAG with verified citations), predictive machine learning (forecasting and anomaly detection), multi-agent coordination (LangGraph), and human-in-the-loop governance into a unified, secure, multi-tenant SaaS application.

---

## 🏛️ System Architecture

```
                                  +---------------------------------------+
                                  |         Next.js 14 Web Portal         |
                                  |   (TypeScript, Tailwind, Radix UI)    |
                                  +-------------------+-------------------+
                                                      |
                                                      | HTTP / SSE (Streaming)
                                                      v
                                  +---------------------------------------+
                                  |       FastAPI Core Gateway API        |
                                  |  (Pydantic v2, Async Auth, RBAC, OIDC)|
                                  +-------------------+-------------------+
                                                      |
                    +---------------------------------+---------------------------------+
                    |                                 |                                 |
                    v                                 v                                 v
    +-------------------------------+ +-------------------------------+ +-------------------------------+
    |       Security & Identity     | |     LangGraph Orchestrator    | |     Data & Vector Storage     |
    |  - Multi-tenant Context       | |  - StateGraph Supervisor      | |  - PostgreSQL 16 (Relational) |
    |  - JWT Bearer / Refresh       | |  - Checkpointed State         | |  - pgvector (Vector Index)    |
    |  - Organization Isolation     | |  - Human-in-the-Loop Pauses   | |  - Encrypted Storage (Docs)   |
    |  - Granular RBAC Permissions  | |  - Deterministic Routing      | |  - Audit & Usage Ledger       |
    +-------------------------------+ +---------------+---------------+ +-------------------------------+
                                                      |
        +---------------------+-----------------------+-----------------------+---------------------+
        |                     |                       |                       |                     |
        v                     v                       v                       v                     v
+---------------+     +---------------+       +---------------+       +---------------+     +---------------+
|   RAG Agent   |     |   SQL Agent   |       |   ML Agent    |     | Doc Intel Agent |     | Report Agent  |
| - Hybrid Search|     | - Schema Insp |       | - Forecasting |     | - Pydantic Parse|     | - Markdown/PDF|
| - Citations   |     | - Read-Only   |       | - Anomalies   |     | - Invoices/Contr|     | - Exec Summary|
| - pgvector    |     | - AST Parser  |       | - Isolation F.|     | - Metadata Extr |     | - Audit Trail |
+---------------+     +---------------+       +---------------+       +---------------+     +---------------+
```

---

## 🚀 Key Platform Capabilities

1. **Multi-Tenant Security & Isolation**: Strict server-side `organization_id` scoping across all relational tables, vector spaces, file paths, and agent execution threads.
2. **Deterministic Multi-Agent Workflows**: LangGraph supervisor coordinating specialized agents (RAG, SQL, ML, Doc Intelligence, Validation, Reporting) with checkpointed state.
3. **Enterprise RAG Engine**: Multi-format ingestion (PDF, DOCX, TXT, CSV, JSON), semantic chunking, pgvector search, and strict citation grounding with zero fabricated citations.
4. **Natural Language to Safe SQL**: Schema inspection, query generation, and AST-level safety validation blocking any DDL/DML, with strict query timeouts and row limits.
5. **Real Machine Learning**: Time-series forecasting (XGBoost/scikit-learn) with real test MAE/RMSE calculations and Isolation Forest anomaly detection.
6. **Human-in-the-Loop Governance**: Sensitive operations (e.g., email dispatch, record updates) automatically trigger execution pauses awaiting managerial approval.
7. **Production Observability**: Structured correlation IDs, Prometheus metrics, and complete audit logging.

---

## 📂 Repository Layout

```
aegis-ai/
├── frontend/          # Next.js 14 App Router, TypeScript, Tailwind CSS
├── backend/           # FastAPI 0.111+, SQLAlchemy 2.0 Async, LangGraph, Pydantic v2
├── ml/                # Scikit-learn, XGBoost, anomaly detection & synthetic datasets
├── tests/             # Unit, integration, security, RAG, and agent test suites
├── docs/              # Comprehensive architecture, API, and deployment documentation
├── infrastructure/    # Dockerfiles, Compose specs, and cloud deployment manifests
└── scripts/           # Database seeding, demo data generation, and operational utilities
```

---

## 💻 Quickstart (Local Development)

### 1. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` to access the AEGIS AI portal.
