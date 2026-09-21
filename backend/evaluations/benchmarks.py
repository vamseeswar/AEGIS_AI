"""AEGIS AI — Curated Synthetic Evaluation Benchmarks
Standardized test suites for testing RAG precision/recall/faithfulness,
agent tool selection accuracy, and SQL AST safety compliance.
"""

from typing import Any

# 1. RAG Grounding & Retrieval Benchmark (Curated Enterprise Test Cases)
RAG_BENCHMARK_CASES: list[dict[str, Any]] = [
    {
        "id": "rag-001",
        "question": "What is the maximum allowed query execution timeout for SQL Analyst agent execution?",
        "ground_truth_statements": [
            "The maximum allowed query execution timeout is 5000 milliseconds.",
            "Queries exceeding timeout are automatically canceled to enforce AST safety.",
        ],
        "retrieved_contexts": [
            "SQL Analyst Agent enforces strict AST safety checks. Queries have a hard timeout limit of 5000 milliseconds.",
            "Queries exceeding timeout are automatically canceled to protect database connection pools.",
        ],
        "generated_answer": "The maximum allowed query execution timeout is 5000 milliseconds, and queries exceeding timeout are automatically canceled to enforce safety.",
    },
    {
        "id": "rag-002",
        "question": "Which machine learning models are supported for forward time series revenue projections?",
        "ground_truth_statements": [
            "AEGIS AI supports Ridge, Random Forest Regressor, and XGBoost Regressor for forecasting.",
            "Models produce 95 percent confidence intervals and holdout metrics including MAE and RMSE.",
        ],
        "retrieved_contexts": [
            "The ML Forecasting engine provides Ridge, Random Forest Regressor, and XGBoost Regressor algorithms.",
            "Each trained model generates recursive forecasts with ninety-five percent confidence interval bands and MAE RMSE metrics.",
        ],
        "generated_answer": "AEGIS AI supports Ridge, Random Forest Regressor, and XGBoost Regressor for forward time series revenue forecasting and projections with ninety-five percent confidence intervals.",
    },
    {
        "id": "rag-003",
        "question": "What are the four tiers of Role-Based Access Control in the platform?",
        "ground_truth_statements": [
            "The four RBAC tiers are ADMIN, MANAGER, MEMBER, and VIEWER.",
            "ADMIN possesses all permissions including tenant settings and user invitation.",
        ],
        "retrieved_contexts": [
            "Multi-tenant authorization is governed by 4 hierarchical roles: ADMIN, MANAGER, MEMBER, and VIEWER.",
            "ADMIN possesses all permissions including tenant settings and user management.",
        ],
        "generated_answer": "The platform enforces four tiers of Role-Based Access Control: ADMIN, MANAGER, MEMBER, and VIEWER.",
    },
    {
        "id": "rag-004",
        "question": "How does the platform prevent SQL injection attacks in the analytics engine?",
        "ground_truth_statements": [
            "The platform parses queries into an Abstract Syntax Tree using sqlparse.",
            "Any statement that is not a read-only SELECT or contains DDL or DML is blocked with SQLSafetyViolationError.",
        ],
        "retrieved_contexts": [
            "SQL Analyst uses AST analysis via sqlparse to inspect tokens. Only SELECT statements are permitted.",
            "DML and DDL operations such as DROP, DELETE, TRUNCATE, and ALTER are strictly forbidden with SQLSafetyViolationError.",
        ],
        "generated_answer": "The platform prevents SQL injection attacks in the analytics engine by parsing queries into an Abstract Syntax Tree using sqlparse, strictly permitting only read-only SELECT statements while rejecting forbidden DDL and DML operations.",
    },
    {
        "id": "rag-005",
        "question": "What criteria trigger Human-in-the-Loop authorization tickets?",
        "ground_truth_statements": [
            "Sensitive actions like wire transfers, vector index reindexing, or tenant audit exports require approval.",
            "Tickets are persisted in PENDING status until an authorized user approves or rejects them.",
        ],
        "retrieved_contexts": [
            "High-risk sensitive tool invocations like wire transfers, indexing changes, or audit exports generate approval tickets.",
            "Tickets remain in PENDING status until authorized users approve or reject them.",
        ],
        "generated_answer": "Sensitive tool operations like wire transfers and audit exports generate PENDING approval tickets that require human authorization before proceeding.",
    },
]

# 2. Agent Tool Selection & Argument Accuracy Benchmark
AGENT_BENCHMARK_CASES: list[dict[str, Any]] = [
    {
        "id": "agent-001",
        "task_prompt": "Query the total sales count from the database for last month.",
        "expected_lead_agent": "sql_agent",
        "expected_tool": "query_database",
        "required_arguments": ["query"],
        "predicted_tool": "query_database",
        "predicted_arguments": {"query": "SELECT COUNT(*) FROM sales WHERE date >= '2026-08-01'"},
        "step_statuses": ["SUCCESS", "SUCCESS", "SUCCESS"],
    },
    {
        "id": "agent-002",
        "task_prompt": "Forecast next quarter's customer churn using trained machine learning models.",
        "expected_lead_agent": "ml_agent",
        "expected_tool": "run_forecast",
        "required_arguments": ["model_id", "steps"],
        "predicted_tool": "run_forecast",
        "predicted_arguments": {"model_id": "model-churn-v1", "steps": 90},
        "step_statuses": ["SUCCESS", "SUCCESS", "SUCCESS"],
    },
    {
        "id": "agent-003",
        "task_prompt": "Scan enterprise knowledge bases to explain our vendor data privacy policy.",
        "expected_lead_agent": "rag_agent",
        "expected_tool": "search_documents",
        "required_arguments": ["query"],
        "predicted_tool": "search_documents",
        "predicted_arguments": {"query": "vendor data privacy policy guidelines"},
        "step_statuses": ["SUCCESS", "SUCCESS"],
    },
    {
        "id": "agent-004",
        "task_prompt": "Profile customer transaction CSV file to compute descriptive statistics and correlations.",
        "expected_lead_agent": "data_agent",
        "expected_tool": "analyze_csv",
        "required_arguments": ["csv_content"],
        "predicted_tool": "analyze_csv",
        "predicted_arguments": {"csv_content": "id,amount,score\n1,100,0.9\n2,200,0.8"},
        "step_statuses": ["SUCCESS", "SUCCESS", "SUCCESS"],
    },
    {
        "id": "agent-005",
        "task_prompt": "Compile operational telemetry findings into a publication-grade PDF report.",
        "expected_lead_agent": "report_agent",
        "expected_tool": "generate_report",
        "required_arguments": ["title", "content_markdown"],
        "predicted_tool": "generate_report",
        "predicted_arguments": {
            "title": "Quarterly Operations Synthesis",
            "content_markdown": "# Operations Synthesis\nAll SLA benchmarks nominal.",
        },
        "step_statuses": ["SUCCESS", "SUCCESS"],
    },
]

# 3. SQL Safety Compliance Benchmark
SQL_BENCHMARK_CASES: list[dict[str, Any]] = [
    {
        "id": "sql-001",
        "query": "SELECT id, full_name, email FROM users LIMIT 50;",
        "expected_safe": True,
    },
    {
        "id": "sql-002",
        "query": "DROP TABLE users;",
        "expected_safe": False,
    },
    {
        "id": "sql-003",
        "query": "SELECT organization_id, COUNT(*) FROM audit_logs GROUP BY organization_id LIMIT 100;",
        "expected_safe": True,
    },
    {
        "id": "sql-004",
        "query": "UPDATE roles SET name = 'SUPERADMIN' WHERE id = '1';",
        "expected_safe": False,
    },
    {
        "id": "sql-005",
        "query": "SELECT 1; TRUNCATE TABLE usage_events;",
        "expected_safe": False,
    },
]
