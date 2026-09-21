"""AEGIS AI — Database Initialization and Default Seeding
Creates database tables and populates default roles, permissions, seed organization, and admin user.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import get_password_hash
from backend.db.base import Base
from backend.db.session import async_session_maker, engine
from backend.models import (
    Organization,
    OrganizationMember,
    Permission,
    Role,
    RolePermission,
    User,
)

# Standard RBAC Permissions from Spec
PLATFORM_PERMISSIONS = [
    ("documents.read", "View and download indexed documents"),
    ("documents.upload", "Upload new files to knowledge bases"),
    ("documents.delete", "Delete documents from knowledge bases"),
    ("knowledgebase.read", "View knowledge base schemas and statistics"),
    ("knowledgebase.manage", "Create, update, and configure knowledge bases"),
    ("chat.execute", "Send messages and interact with AI chat"),
    ("agents.execute", "Execute multi-agent autonomous workflows"),
    ("tools.execute", "Invoke registered MCP tools directly"),
    ("database.query", "Execute natural language to SQL queries"),
    ("reports.create", "Generate executive reports in Markdown and PDF"),
    ("reports.download", "Download compiled reports"),
    ("analytics.view", "View descriptive analytics, trends, and charts"),
    ("ml.execute", "Train forecasting models and run anomaly detection"),
    ("evaluations.view", "View RAG and agent evaluation benchmark scores"),
    ("users.manage", "Invite, update, and manage team members"),
    ("organization.manage", "Configure organization settings and plans"),
    ("audit.view", "Inspect security audit logs and usage events"),
    ("system.admin", "Perform administrative platform operations"),
]

ROLE_PERMISSIONS_MAP = {
    "ADMIN": [p[0] for p in PLATFORM_PERMISSIONS],  # All 18 permissions
    "MANAGER": [
        "documents.read",
        "documents.upload",
        "documents.delete",
        "knowledgebase.read",
        "knowledgebase.manage",
        "chat.execute",
        "agents.execute",
        "tools.execute",
        "database.query",
        "reports.create",
        "reports.download",
        "analytics.view",
        "ml.execute",
        "evaluations.view",
        "users.manage",
        "audit.view",
    ],
    "MEMBER": [
        "documents.read",
        "documents.upload",
        "knowledgebase.read",
        "chat.execute",
        "agents.execute",
        "tools.execute",
        "database.query",
        "reports.create",
        "reports.download",
        "analytics.view",
        "ml.execute",
    ],
    "VIEWER": [
        "documents.read",
        "knowledgebase.read",
        "reports.download",
        "analytics.view",
        "evaluations.view",
    ],
}


async def seed_roles_and_permissions(session: AsyncSession) -> dict[str, Role]:
    """Seeds default permissions and roles into the database."""
    # 1. Seed Permissions
    permissions_map: dict[str, Permission] = {}
    for name, desc in PLATFORM_PERMISSIONS:
        stmt = select(Permission).where(Permission.name == name)
        result = await session.execute(stmt)
        perm = result.scalar_one_or_none()
        if not perm:
            perm = Permission(name=name, description=desc)
            session.add(perm)
            await session.flush()
        permissions_map[name] = perm

    # 2. Seed Roles and Link Permissions
    roles_map: dict[str, Role] = {}
    for role_name, perm_names in ROLE_PERMISSIONS_MAP.items():
        stmt = select(Role).where(Role.name == role_name)
        result = await session.execute(stmt)
        role = result.scalar_one_or_none()
        if not role:
            role = Role(name=role_name, description=f"Default {role_name} platform role")
            session.add(role)
            await session.flush()

        roles_map[role_name] = role

        # Link role permissions
        for p_name in perm_names:
            perm_obj = permissions_map.get(p_name)
            if perm_obj:
                rp_stmt = select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == perm_obj.id,
                )
                rp_result = await session.execute(rp_stmt)
                if not rp_result.scalar_one_or_none():
                    rp = RolePermission(role_id=role.id, permission_id=perm_obj.id)
                    session.add(rp)

    await session.flush()
    return roles_map


async def seed_default_organization_and_admin(
    session: AsyncSession, roles_map: dict[str, Role]
) -> tuple[Organization, User]:
    """Seeds default demo organization and admin user."""
    # Seed Organization
    org_stmt = select(Organization).where(Organization.slug == "aegis-corp")
    org_result = await session.execute(org_stmt)
    org = org_result.scalar_one_or_none()
    if not org:
        org = Organization(
            name="AEGIS Global Operations",
            slug="aegis-corp",
            plan="enterprise",
            is_active=True,
        )
        session.add(org)
        await session.flush()

    # Seed Admin User
    user_stmt = select(User).where(User.email == "admin@aegis.ai")
    user_result = await session.execute(user_stmt)
    admin_user = user_result.scalar_one_or_none()
    if not admin_user:
        admin_user = User(
            email="admin@aegis.ai",
            full_name="System Administrator",
            hashed_password=get_password_hash("Admin123!"),
            is_active=True,
            is_superuser=True,
        )
        session.add(admin_user)
        await session.flush()

    # Assign Admin to Org
    admin_role = roles_map["ADMIN"]
    member_stmt = select(OrganizationMember).where(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.user_id == admin_user.id,
    )
    member_result = await session.execute(member_stmt)
    member = member_result.scalar_one_or_none()
    if not member:
        member = OrganizationMember(
            organization_id=org.id,
            user_id=admin_user.id,
            role_id=admin_role.id,
            is_active=True,
        )
        session.add(member)
        await session.flush()

    return org, admin_user


async def seed_demo_documents(session: AsyncSession, org: Organization, admin_user: User) -> None:
    """Seeds default demo documents matching enterprise blueprint for immediate RAG retrieval."""
    import io
    from backend.db.base import generate_uuid
    from backend.models.document import Document, KnowledgeBase, KnowledgeBaseDocument
    from backend.storage import get_storage_provider

    stmt = select(Document).where(Document.organization_id == org.id)
    res = await session.execute(stmt)
    if res.scalars().first():
        return

    kb_stmt = select(KnowledgeBase).where(KnowledgeBase.organization_id == org.id)
    kb_res = await session.execute(kb_stmt)
    kb = kb_res.scalars().first()
    if not kb:
        kb = KnowledgeBase(
            organization_id=org.id,
            name="Default Knowledge Base",
            description="Tenant enterprise operations and governance documents",
            embedding_model="all-MiniLM-L6-v2",
        )
        session.add(kb)
        await session.flush()

    storage = get_storage_provider()

    # 1. PDF
    pdf_buf = io.BytesIO()
    try:
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(pdf_buf)
        c.drawString(100, 750, "AEGIS Global Operations - Q3 Enterprise Financial Report")
        c.drawString(100, 720, "1. Executive Summary: Q3 Total Revenue reached $48.2M with 34% YoY expansion.")
        c.drawString(100, 700, "2. Operating Margins: GAAP operating margin increased to 28.5%.")
        c.drawString(100, 680, "3. R&D Capitalization: Multi-agent LangGraph platform R&D expanded.")
        c.drawString(100, 660, "4. Cash Flow: Free cash flow generation totaled $14.1M.")
        c.showPage()
        c.save()
        pdf_bytes = pdf_buf.getvalue()
    except Exception:
        pdf_bytes = b"%PDF-1.4 Minimal PDF Q3 Enterprise Financial Report"

    # 2. DOCX
    docx_buf = io.BytesIO()
    try:
        import docx
        doc_file = docx.Document()
        doc_file.add_heading("AEGIS Security Architecture Specification v1", 0)
        doc_file.add_paragraph("Tenant Isolation: Strict row-level security and isolated storage directories.")
        doc_file.add_paragraph("AST SQL Guardrails: All write/DDL queries are parsed and rejected by AST safety rules.")
        doc_file.add_paragraph("Role-Based Access Control: Granular permissions for Admin, Manager, Member, Viewer.")
        doc_file.save(docx_buf)
        docx_bytes = docx_buf.getvalue()
    except Exception:
        docx_bytes = b"PK\x03\x04 Minimal DOCX AEGIS Security Architecture"

    # 3. CSV
    csv_bytes = (
        b"tenant_id,churn_risk,monthly_spend,engagement_score,support_tickets\n"
        b"ORG-001,0.04,12500,92,1\n"
        b"ORG-002,0.18,8400,64,4\n"
        b"ORG-003,0.72,3200,28,12\n"
        b"ORG-004,0.09,19000,88,2\n"
    )

    # 4. TXT
    txt_bytes = (
        b"Autonomous Agent Operational Guidelines v2.4\n\n"
        b"1. Agents must operate within assigned MCP tool execution policies.\n"
        b"2. LangGraph state transitions are checkpointed for high-availability resume.\n"
        b"3. HITL approval is mandatory for financial transfers and database migrations.\n"
    )

    demos = [
        ("Q3_Enterprise_Financial_Report.pdf", "Q3 Enterprise Financial Report", "PDF", "application/pdf", pdf_bytes, "INDEXED", 48, 4200000),
        ("AEGIS_Security_Architecture_v1.docx", "AEGIS Security Architecture v1", "DOCX", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", docx_bytes, "INDEXED", 32, 1540000),
        ("Customer_Churn_Telemetry_2024.csv", "Customer Churn Telemetry 2024", "CSV", "text/csv", csv_bytes, "INDEXED", 14, 890000),
        ("Autonomous_Agent_Guidelines.txt", "Autonomous Agent Guidelines", "TXT", "text/plain", txt_bytes, "PARSING", 6, 145000),
    ]

    for filename, title, ftype, mime, content, status, chunks_count, file_size in demos:
        d_id = generate_uuid()
        s_path = await storage.save_file(org.id, d_id, filename, content)
        doc = Document(
            id=d_id,
            organization_id=org.id,
            user_id=admin_user.id,
            title=title,
            filename=filename,
            file_type=ftype,
            mime_type=mime,
            file_size_bytes=file_size,
            storage_path=s_path,
            status=status,
            doc_metadata={"original_filename": filename, "chunks_count": chunks_count},
        )
        session.add(doc)
        await session.flush()

        link = KnowledgeBaseDocument(
            organization_id=org.id,
            knowledge_base_id=kb.id,
            document_id=doc.id,
        )
        session.add(link)


async def initialize_database() -> None:
    """Entrypoint to create all tables and run default seeds."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        roles_map = await seed_roles_and_permissions(session)
        org, admin_user = await seed_default_organization_and_admin(session, roles_map)
        await seed_demo_documents(session, org, admin_user)
        await session.commit()
    print("[*] Database schema initialized and seeded successfully.")


if __name__ == "__main__":
    asyncio.run(initialize_database())
