"""Unit Tests for Phase 2: Database Layer, SQLAlchemy Models, and Seeding."""

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.db.base import Base
from backend.db.init_db import (
    PLATFORM_PERMISSIONS,
    ROLE_PERMISSIONS_MAP,
    seed_default_organization_and_admin,
    seed_roles_and_permissions,
)
from backend.models import (
    AgentRun,
    AgentStep,
    Approval,
    AuditLog,
    Conversation,
    Document,
    DocumentChunk,
    Evaluation,
    KnowledgeBase,
    KnowledgeBaseDocument,
    Memory,
    Message,
    MLModel,
    MLPrediction,
    OrganizationMember,
    Permission,
    Report,
    RolePermission,
    ToolCall,
    UsageEvent,
)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Creates a temporary in-memory async SQLite database session for unit testing."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_roles_and_permissions_seeding(db_session: AsyncSession):
    """Verify that all 18 platform permissions and 4 roles are correctly seeded and linked."""
    roles_map = await seed_roles_and_permissions(db_session)
    await db_session.commit()

    assert len(roles_map) == 4
    assert set(roles_map.keys()) == {"ADMIN", "MANAGER", "MEMBER", "VIEWER"}

    # Verify all 18 permissions exist
    perm_result = await db_session.execute(select(Permission))
    all_perms = perm_result.scalars().all()
    assert len(all_perms) == len(PLATFORM_PERMISSIONS)

    # Verify Admin role has all permissions
    admin_role = roles_map["ADMIN"]
    rp_result = await db_session.execute(
        select(RolePermission).where(RolePermission.role_id == admin_role.id)
    )
    admin_rps = rp_result.scalars().all()
    assert len(admin_rps) == len(PLATFORM_PERMISSIONS)

    # Verify Viewer role has restricted permissions
    viewer_role = roles_map["VIEWER"]
    viewer_rp_result = await db_session.execute(
        select(RolePermission).where(RolePermission.role_id == viewer_role.id)
    )
    viewer_rps = viewer_rp_result.scalars().all()
    assert len(viewer_rps) == len(ROLE_PERMISSIONS_MAP["VIEWER"])


@pytest.mark.asyncio
async def test_default_organization_and_admin_seeding(db_session: AsyncSession):
    """Verify that the default organization and administrator account are properly created."""
    roles_map = await seed_roles_and_permissions(db_session)
    org, admin_user = await seed_default_organization_and_admin(db_session, roles_map)
    await db_session.commit()

    assert org.slug == "aegis-corp"
    assert org.plan == "enterprise"
    assert admin_user.email == "admin@aegis.ai"
    assert admin_user.is_superuser is True

    # Check organization membership
    stmt = select(OrganizationMember).where(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.user_id == admin_user.id,
    )
    member_result = await db_session.execute(stmt)
    membership = member_result.scalar_one()
    assert membership.role_id == roles_map["ADMIN"].id


@pytest.mark.asyncio
async def test_complete_relational_domain_models(db_session: AsyncSession):
    """Verify instantiation, saving, and querying across all core operational models."""
    roles_map = await seed_roles_and_permissions(db_session)
    org, user = await seed_default_organization_and_admin(db_session, roles_map)

    # 1. Chat & Conversations
    conv = Conversation(organization_id=org.id, user_id=user.id, title="Q3 Analysis Chat")
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        organization_id=org.id,
        conversation_id=conv.id,
        user_id=user.id,
        role="user",
        content="Analyze sales dip in EMEA",
        metadata_json={"client": "web"},
    )
    db_session.add(msg)

    # 2. Knowledge Base & Documents
    kb = KnowledgeBase(organization_id=org.id, name="Corporate Reports", chunk_size=500)
    db_session.add(kb)
    await db_session.flush()

    doc = Document(
        organization_id=org.id,
        user_id=user.id,
        title="Q3 Sales Report",
        filename="sales_q3.pdf",
        file_type="PDF",
        mime_type="application/pdf",
        file_size_bytes=1048576,
        storage_path=f"storage/{org.id}/documents/sales_q3.pdf",
        status="INDEXED",
    )
    db_session.add(doc)
    await db_session.flush()

    kb_doc = KnowledgeBaseDocument(
        organization_id=org.id,
        knowledge_base_id=kb.id,
        document_id=doc.id,
    )
    db_session.add(kb_doc)

    chunk = DocumentChunk(
        organization_id=org.id,
        document_id=doc.id,
        knowledge_base_id=kb.id,
        chunk_index=0,
        page_number=1,
        content="Revenue dropped 12% in EMEA due to supply delays.",
        embedding_vector=[0.12, -0.45, 0.88],
    )
    db_session.add(chunk)

    # 3. Agent Execution & Approvals
    run = AgentRun(
        organization_id=org.id,
        user_id=user.id,
        conversation_id=conv.id,
        workflow_name="sales_investigation",
        request_prompt="Investigate Q3 drop and prepare report",
        status="WAITING_APPROVAL",
        plan_json={"steps": ["sql_analysis", "ml_forecast", "generate_report"]},
    )
    db_session.add(run)
    await db_session.flush()

    step = AgentStep(
        organization_id=org.id,
        agent_run_id=run.id,
        step_number=1,
        agent_name="SQLAnalystAgent",
        input_state={"query": "SELECT sum(amount) FROM sales"},
        duration_ms=250.5,
    )
    db_session.add(step)

    tool = ToolCall(
        organization_id=org.id,
        agent_run_id=run.id,
        tool_name="query_database",
        is_sensitive=False,
        status="SUCCESS",
        execution_time_ms=45.2,
    )
    db_session.add(tool)

    approval = Approval(
        organization_id=org.id,
        agent_run_id=run.id,
        requested_by_agent="ReportGenerationAgent",
        action_name="publish_executive_report",
        action_payload={"report_title": "Q3 Executive Summary", "recipients": ["ceo@aegis.ai"]},
        reason="Publishing executive report requires human authorization",
        status="PENDING",
    )
    db_session.add(approval)

    # 4. Analytics & Machine Learning
    ml_model = MLModel(
        organization_id=org.id,
        name="Quarterly_Revenue_Forecaster",
        model_type="FORECASTING",
        version="1.0.0",
        metrics_json={"MAE": 1240.50, "RMSE": 1820.00, "MAPE": 0.045},
        trained_at=org.created_at,
    )
    db_session.add(ml_model)
    await db_session.flush()

    prediction = MLPrediction(
        organization_id=org.id,
        ml_model_id=ml_model.id,
        prediction_type="FORECAST",
        input_data={"quarter": "Q4", "target_year": 2026},
        prediction_results={"predicted_revenue": 4500000.0, "confidence_lower": 4200000.0},
        confidence_score=0.92,
    )
    db_session.add(prediction)

    report = Report(
        organization_id=org.id,
        user_id=user.id,
        agent_run_id=run.id,
        title="Q3 Comprehensive Sales Audit",
        content_markdown="# Executive Summary\nRevenue declined in EMEA...",
    )
    db_session.add(report)

    mem = Memory(
        organization_id=org.id,
        user_id=user.id,
        conversation_id=conv.id,
        key="preferred_currency",
        value="EUR",
    )
    db_session.add(mem)

    # 5. Governance & Observability
    evaluation = Evaluation(
        organization_id=org.id,
        eval_type="RAG",
        metric_name="context_precision",
        score=0.94,
        dataset_name="sales_evaluation_set_v1",
    )
    db_session.add(evaluation)

    usage = UsageEvent(
        organization_id=org.id,
        user_id=user.id,
        event_type="LLM_CALL",
        provider="gemini",
        model_name="gemini-1.5-flash",
        prompt_tokens=520,
        completion_tokens=180,
        total_tokens=700,
        estimated_cost_usd=0.00014,
    )
    db_session.add(usage)

    audit = AuditLog(
        organization_id=org.id,
        user_id=user.id,
        action="APPROVAL_REQUESTED",
        resource_type="Approval",
        resource_id=approval.id,
        status="SUCCESS",
    )
    db_session.add(audit)

    await db_session.commit()

    # Query verification
    queried_run = await db_session.get(AgentRun, run.id)
    assert queried_run is not None
    assert queried_run.workflow_name == "sales_investigation"
    assert queried_run.status == "WAITING_APPROVAL"

    queried_chunk = await db_session.get(DocumentChunk, chunk.id)
    assert queried_chunk is not None
    assert queried_chunk.embedding_vector == [0.12, -0.45, 0.88]

    queried_model = await db_session.get(MLModel, ml_model.id)
    assert queried_model is not None
    assert queried_model.metrics_json["MAPE"] == 0.045
