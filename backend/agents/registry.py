"""AEGIS AI — Agent Registry & Catalog
Defines the fleet of 8 specialized autonomous agents with their system instructions and capabilities.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentDefinition:
    id: str
    name: str
    role: str
    icon: str
    description: str
    capabilities: list[str]
    system_prompt: str
    default_tools: list[str] = field(default_factory=list)


AGENT_FLEET: dict[str, AgentDefinition] = {
    "supervisor": AgentDefinition(
        id="supervisor",
        name="Supervisor Agent",
        role="Orchestration & Planning",
        icon="Network",
        description="Analyzes complex operational directives, generates multi-stage execution plans, delegates subtasks to specialized agents, and synthesizes final executive briefings.",
        capabilities=[
            "Goal decomposition and DAG planning",
            "Dynamic agent routing and delegation",
            "Error detection and recovery",
            "Multi-agent output synthesis",
        ],
        system_prompt=(
            "You are the AEGIS Supervisor Agent. Your role is to break down complex operational "
            "tasks into structured steps, route to specialized domain agents, and synthesize "
            "comprehensive, executive-ready conclusions."
        ),
        default_tools=["plan_task", "synthesize_results"],
    ),
    "rag_agent": AgentDefinition(
        id="rag_agent",
        name="RAG Research Agent",
        role="Knowledge & Citations",
        icon="BookOpen",
        description="Searches tenant-scoped vector knowledge bases, retrieves high-similarity document chunks, formats XML context, and validates source citations.",
        capabilities=[
            "Semantic cosine search across documents",
            "Context grounding with page attribution",
            "Verifiable citation extraction",
            "Document excerpt synthesis",
        ],
        system_prompt=(
            "You are the AEGIS RAG Research Agent. You retrieve and ground factual information "
            "from tenant documentation, providing exact citations and page references."
        ),
        default_tools=["search_documents", "get_document_excerpt"],
    ),
    "sql_agent": AgentDefinition(
        id="sql_agent",
        name="SQL Analyst Agent",
        role="Relational Database Querying",
        icon="Database",
        description="Inspects schema, translates natural language into secure read-only SQL, applies AST safety validations (SELECT-only), and formats tabular query results.",
        capabilities=[
            "Schema extraction and table profiling",
            "Natural language to SQL compilation",
            "Strict AST query safety validation (read-only)",
            "Query performance optimization",
        ],
        system_prompt=(
            "You are the AEGIS SQL Analyst Agent. You translate business questions into optimized, "
            "strictly read-only SQL queries with AST safety guards."
        ),
        default_tools=["inspect_schema", "execute_safe_sql"],
    ),
    "data_agent": AgentDefinition(
        id="data_agent",
        name="Data Analytics Agent",
        role="Statistical Analysis & Profiling",
        icon="BarChart3",
        description="Performs in-memory data analytics on tabular and CSV records, computing distribution metrics, correlation matrices, aggregations, and formatting Recharts data series.",
        capabilities=[
            "Statistical summary profiling (mean, median, stdev)",
            "Correlation and trend analysis",
            "Grouped aggregations and percentile cuts",
            "Recharts visualization payload generation",
        ],
        system_prompt=(
            "You are the AEGIS Data Analytics Agent. You compute rigorous statistical summaries "
            "and produce chart-ready data points for enterprise decision making."
        ),
        default_tools=["profile_data", "compute_correlations", "generate_chart_data"],
    ),
    "ml_agent": AgentDefinition(
        id="ml_agent",
        name="ML Forecasting Agent",
        role="Predictive Machine Learning",
        icon="TrendingUp",
        description="Executes time-series revenue and metric forecasts using scikit-learn models (Ridge, Random Forest) and calculates unsupervised anomaly scores with Isolation Forest.",
        capabilities=[
            "Automated lag feature engineering",
            "Time-series forecasting with MAE/RMSE error metrics",
            "Isolation Forest anomaly detection",
            "Risk scoring and confidence intervals",
        ],
        system_prompt=(
            "You are the AEGIS ML Forecasting Agent. You train regressors on operational time-series, "
            "forecast future trajectories, and flag anomalies."
        ),
        default_tools=["train_forecast_model", "detect_anomalies", "evaluate_ml_metrics"],
    ),
    "doc_intel_agent": AgentDefinition(
        id="doc_intel_agent",
        name="Document Intelligence Agent",
        role="Unstructured Extraction",
        icon="FileSearch",
        description="Extracts key entities, contract clauses, SLA terms, metadata, and tables from complex documents (PDFs, Word documents, JSON structures).",
        capabilities=[
            "Named entity and metadata extraction",
            "Contract clause and SLA compliance review",
            "Cross-document entity reconciliation",
            "Document structure parsing",
        ],
        system_prompt=(
            "You are the AEGIS Document Intelligence Agent. You extract structured insights, "
            "compliance terms, and entities from unstructured files."
        ),
        default_tools=["extract_entities", "review_compliance_clauses"],
    ),
    "validation_agent": AgentDefinition(
        id="validation_agent",
        name="Validation & Quality Agent",
        role="Grounding & Quality Assurance",
        icon="ShieldCheck",
        description="Validates agent outputs against ground-truth retrieved contexts, checks for hallucinated statements, verifies citation accuracy, and assesses faithfulness.",
        capabilities=[
            "Grounding and faithfulness validation",
            "Hallucination detection and flag scoring",
            "Citation verification",
            "Quality assurance scoring (0-100%)",
        ],
        system_prompt=(
            "You are the AEGIS Validation Agent. You rigorously review claims against source evidence "
            "and compute verification quality scores."
        ),
        default_tools=["check_hallucinations", "verify_grounding"],
    ),
    "report_agent": AgentDefinition(
        id="report_agent",
        name="Report Generation Agent",
        role="Executive Synthesis & Export",
        icon="FileText",
        description="Assembles multi-agent execution findings, analytical tables, charts, and citations into structured executive reports formatted in Markdown and downloadable PDF.",
        capabilities=[
            "Executive summary synthesis",
            "Multi-section report authoring",
            "Chart and table inclusion",
            "Reportlab PDF compilation and Markdown export",
        ],
        system_prompt=(
            "You are the AEGIS Report Generation Agent. You transform raw multi-agent outputs into "
            "polished, C-level executive briefings and reports."
        ),
        default_tools=["compile_markdown_report", "generate_pdf_report"],
    ),
}


def list_available_agents() -> list[dict[str, Any]]:
    """Returns serialized list of all available agents for API endpoints and UI."""
    return [
        {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "icon": agent.icon,
            "description": agent.description,
            "capabilities": agent.capabilities,
            "default_tools": agent.default_tools,
        }
        for agent in AGENT_FLEET.values()
    ]


def get_agent_definition(agent_id: str) -> AgentDefinition | None:
    """Retrieves an agent definition by identifier."""
    return AGENT_FLEET.get(agent_id.lower())
