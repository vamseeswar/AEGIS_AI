# AEGIS AI — Architecture Specification
**Autonomous AI Operations Platform**
*Document Version: 1.0.0 | Production Architecture*

---

## 1. Executive Architecture Overview

**AEGIS AI** is an enterprise-grade autonomous AI operations platform built for structured business intelligence, unstructured document research (RAG), multi-agent orchestration, predictive machine learning, and human-governed automation.

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
        |                     |                       |                       |                     |
        +---------------------+-----------------------+-----------------------+---------------------+
                                                      |
                                                      v
                                      +-------------------------------+
                                      |       MCP / Tool Engine       |
                                      | - Strict Permission Gates     |
                                      | - Audit Logging & Rate Limits |
                                      | - Human Approval Interceptors |
                                      +-------------------------------+
```

---

## 2. Component Architecture

### 2.1 Frontend Portal (`frontend/`)
* **Framework**: Next.js 14 (App Router) + React 18 / TypeScript strict mode.
* **Styling & UI**: Tailwind CSS, Radix UI primitives, Lucide Icons, Recharts for data visualization.
* **State & Data Fetching**: TanStack Query v5 with optimistic UI updates and real-time SSE event consumption.
* **Design Philosophy**: Sleek dark/light enterprise cyber-operations aesthetic, status badges, interactive workflow DAG step visualizers, streaming markdown cards with citations, human-approval popups, and instant CSV analytics.

### 2.2 Backend Application Engine (`backend/`)
* **Framework**: FastAPI (async ASGI) on Python 3.11+.
* **Validation & Settings**: Pydantic v2 & `pydantic-settings`.
* **Database Layer**: SQLAlchemy 2.0 (asyncio) + Alembic migrations. Supports PostgreSQL with `pgvector` for production and zero-dependency local fallback.
* **Multi-Tenancy Engine**: Strict server-side `organization_id` scoping on every database query, vector filter, file path, and agent execution thread.
* **Authentication & RBAC**: OAuth2 / JWT access & refresh tokens, bcrypt password hashing, 4-tier roles (`ADMIN`, `MANAGER`, `MEMBER`, `VIEWER`), and 18 granular permission flags.

### 2.3 Agent Orchestrator (`backend/agents/`)
Built with **LangGraph** to deliver structured, deterministic, auditable multi-agent workflows:
1. **Supervisor Agent**: Deconstructs user intent, generates execution plans, assigns sub-agent steps, aggregates findings, and synthesizes final responses.
2. **RAG Research Agent**: Performs vector retrieval against ingested enterprise documents, validates citation ground truth, and filters untrusted prompt injection patterns.
3. **SQL Analyst Agent**: Inspects database schemas, converts natural language into secure read-only SQL queries, enforces AST-level safety (forbids DDL/DML, requires row limits and timeouts), and analyzes query results.
4. **Data Analytics Agent**: Ingests CSV/structured data, performs statistical profiling, distribution calculations, correlations, and trend analysis in a secure in-process execution sandbox.
5. **ML Forecasting & Anomaly Agent**: Trains and applies scikit-learn / XGBoost time-series regression models and Isolation Forests for automated anomaly detection.
6. **Document Intelligence Agent**: Extracts structured schemas (Invoices, Contracts, Financial statements) using Pydantic schema validation.
7. **Validation Agent**: Evaluates agent outputs for hallucination, ensures citations match source excerpts, and verifies numerical integrity.
8. **Report Generation Agent**: Formats multi-modal outputs into comprehensive Markdown and downloadable executive PDF reports.

### 2.4 Human-in-the-Loop (HITL) Subsystem (`backend/agents/` & `backend/tools/`)
* For sensitive tool invocations (`send_email`, `modify_record`, `create_ticket`), the LangGraph state machine enters an `INTERRUPT` state.
* An approval ticket is persisted in the database with payload preview, requester details, risk score, and expiration.
* Frontend receives a real-time notification; designated managers/admins can inspect the exact payload and click **Approve** or **Reject**.
* Workflow resumes seamlessly upon approval or branches into safe cancellation upon rejection.

### 2.5 RAG & Retrieval Engine (`backend/rag/`)
* **File Ingestion**: PDF, DOCX, TXT, CSV, JSON with MIME and magic-byte validation.
* **Chunking**: Recursive character chunking with configurable overlap and metadata enrichment (page, line, headers).
* **Embeddings**: Dual-mode abstraction supporting Google Gemini embeddings, OpenAI-compatible embeddings, or local `sentence-transformers` embeddings (`all-MiniLM-L6-v2`) with zero external API dependencies.
* **Vector Index**: PostgreSQL `pgvector` IVFFlat / HNSW vector indexes with tenant-isolated filtering:
  $$\text{Filter: } \text{organization\_id} = \text{tenant\_id} \land \text{knowledge\_base\_id} = \text{kb\_id}$$
* **Citation Grounding**: Strict attribution engine; responses map directly to verified chunk IDs and source page numbers. Hallucinations are actively detected and flagged.

### 2.6 Real Machine Learning Engine (`ml/`)
* **Revenue & Metric Forecasting**: Automated preprocessing, lag feature creation, rolling window statistics, and Ridge / Random Forest / XGBoost regressors. Calculates real MAE, RMSE, and MAPE metrics on holdout test partitions.
* **Operational Anomaly Detection**: Isolation Forest and rolling z-score analysis to flag outlier transactions, revenue drops, and volume spikes with explainability scores.
* **Model Registry & Tracking**: Persists model metadata, hyperparameters, feature names, training timestamps, and performance metrics in the `ml_models` database table.

---

## 3. Security & Multi-Tenancy Architecture

| Security Domain | Architectural Mechanism |
| :--- | :--- |
| **Tenant Isolation** | All queries enforce `WHERE organization_id = current_user.org_id`. Storage paths are isolated (`/storage/{org_id}/...`). Vector queries strictly filter on `org_id`. |
| **SQL Safety** | SQL parser validates abstract syntax trees (ASTs). Explicitly blocks `DROP`, `ALTER`, `DELETE`, `UPDATE`, `INSERT`, `EXEC`, `UNION ALL` injections. Imposes read-only transactions, 5-second query timeouts, and `LIMIT 100` caps. |
| **Prompt Injection Defense** | All retrieved document chunks and external data inputs are treated as untrusted strings wrapped in isolation delimiters (`<untrusted_document_context>`). LLM system prompts strictly instruct never to execute commands embedded within documents. |
| **Tool Execution Safety** | Tools are strictly gated by user role and permission scopes. Sensitive mutations trigger mandatory Human-in-the-Loop approval. |
| **Audit Logging** | Every authentication attempt, agent step, tool call, SQL execution, approval decision, and file download is written to an immutable `audit_logs` table with timestamp, IP, and user context. |

---

## 4. Observability & Evaluation

* **Health & Metrics Endpoints**: `/api/v1/health`, `/api/v1/ready`, and `/api/v1/metrics`.
* **Evaluation Framework**:
  * **RAG Evaluation**: Context Precision, Context Recall, Answer Faithfulness, and Latency benchmarks.
  * **Agent Evaluation**: Task Success Rate, Tool Selection Accuracy, Planning Efficiency, and Execution Duration.
* **Synthetic Benchmark Datasets**: Deterministic evaluation sets for sales analysis, policy queries, and invoice extraction.

---

## 5. Free-Tier & Production Deployment Architecture

* **Local Development**: Fully runnable with `docker compose up` or natively with Python virtualenv and Next.js dev server.
* **Free-Tier Cloud Ready**: Designed for deployment on Render, Railway, or Fly.io with managed free-tier PostgreSQL (Supabase / Neon / Render Postgres).
* **Zero-Cost Operation**: Uses Gemini Free API Tier or local sentence-transformers + open-source ML models with no GPU requirement.
