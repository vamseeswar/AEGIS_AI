"""AEGIS AI — Executive Report Management Service
Handles persistence, PDF artifact compilation, filesystem storage, and tenant isolation
for multi-modal executive intelligence reports.
"""

import logging
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.errors import ResourceNotFoundError
from backend.models.analytics import Report
from backend.models.governance import AuditLog
from backend.models.identity import Organization, User
from backend.services.pdf_generator import generate_executive_pdf

logger = logging.getLogger("aegis.reports")


def _get_reports_storage_dir(organization_id: str) -> Path:
    """Returns directory path for tenant's PDF report artifacts."""
    base_dir = Path(settings.LOCAL_STORAGE_PATH) / organization_id / "reports"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


async def create_report(
    *,
    db: AsyncSession,
    organization_id: str,
    user_id: str,
    title: str,
    summary: str | None,
    content_markdown: str,
    format: str = "PDF",
    agent_run_id: str | None = None,
    charts_data: list[dict[str, Any]] | None = None,
    metrics_data: dict[str, Any] | None = None,
) -> Report:
    """Compiles markdown into an executive report, optionally renders a PDF, and persists to DB."""
    # Look up org name and user name for report metadata branding
    org_res = await db.execute(select(Organization).where(Organization.id == organization_id))
    org = org_res.scalar_one_or_none()
    org_name = org.name if org else "Enterprise Organization"

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    author_name = user.full_name if user else "AEGIS AI Platform"

    report = Report(
        organization_id=organization_id,
        user_id=user_id,
        agent_run_id=agent_run_id,
        title=title,
        summary=summary,
        format=format.upper(),
        content_markdown=content_markdown,
        charts_data=charts_data,
        metrics_data=metrics_data,
    )
    db.add(report)
    await db.flush()  # Generate report.id

    # If PDF format requested, generate and store the PDF artifact
    pdf_path_str: str | None = None
    if format.upper() in ("PDF", "BOTH"):
        pdf_bytes = generate_executive_pdf(
            title=title,
            summary=summary,
            content_markdown=content_markdown,
            metrics=metrics_data,
            organization_name=org_name,
            author_name=author_name,
        )
        reports_dir = _get_reports_storage_dir(organization_id)
        pdf_file = reports_dir / f"{report.id}.pdf"
        pdf_file.write_bytes(pdf_bytes)
        pdf_path_str = str(pdf_file)
        report.pdf_storage_path = pdf_path_str
        logger.info(f"Generated PDF artifact for report {report.id} at {pdf_path_str}")

    # Audit log
    audit = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action="REPORT_GENERATED",
        resource_type="report",
        resource_id=report.id,
        status="SUCCESS",
        details_json={
            "title": title,
            "format": format.upper(),
            "has_pdf": pdf_path_str is not None,
            "metrics_count": len(metrics_data) if metrics_data else 0,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(report)
    return report


async def list_reports(
    *,
    db: AsyncSession,
    organization_id: str,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Lists all reports for a tenant with pagination."""
    stmt = (
        select(Report)
        .where(Report.organization_id == organization_id)
        .order_by(Report.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    reports = result.scalars().all()

    count_stmt = select(func.count(Report.id)).where(Report.organization_id == organization_id)
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    return {"reports": list(reports), "total": total}


async def get_report(
    *,
    db: AsyncSession,
    report_id: str,
    organization_id: str,
) -> Report:
    """Retrieves a single report with tenant isolation enforcement."""
    stmt = select(Report).where(
        Report.id == report_id,
        Report.organization_id == organization_id,
    )
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()
    if not report:
        raise ResourceNotFoundError("Report", report_id)
    return report


async def get_report_pdf_bytes(
    *,
    db: AsyncSession,
    report_id: str,
    organization_id: str,
    requesting_user_id: str,
) -> tuple[bytes, str]:
    """Returns raw PDF bytes and filename for download, logging an audit record."""
    report = await get_report(db=db, report_id=report_id, organization_id=organization_id)

    if not report.pdf_storage_path or not Path(report.pdf_storage_path).exists():
        # Auto-regenerate if missing
        org_res = await db.execute(select(Organization).where(Organization.id == organization_id))
        org = org_res.scalar_one_or_none()
        org_name = org.name if org else "Enterprise Organization"

        user_res = await db.execute(select(User).where(User.id == report.user_id))
        user = user_res.scalar_one_or_none()
        author_name = user.full_name if user else "AEGIS AI Platform"

        pdf_bytes = generate_executive_pdf(
            title=report.title,
            summary=report.summary,
            content_markdown=report.content_markdown,
            metrics=report.metrics_data,
            organization_name=org_name,
            author_name=author_name,
        )
        reports_dir = _get_reports_storage_dir(organization_id)
        pdf_file = reports_dir / f"{report.id}.pdf"
        pdf_file.write_bytes(pdf_bytes)
        report.pdf_storage_path = str(pdf_file)
        await db.commit()
    else:
        pdf_bytes = Path(report.pdf_storage_path).read_bytes()

    filename = f"{report.title.lower().replace(' ', '_')[:40]}_{report.id[:8]}.pdf"

    audit = AuditLog(
        organization_id=organization_id,
        user_id=requesting_user_id,
        action="REPORT_DOWNLOADED",
        resource_type="report",
        resource_id=report.id,
        status="SUCCESS",
        details_json={"filename": filename},
    )
    db.add(audit)
    await db.commit()

    return pdf_bytes, filename


async def delete_report(
    *,
    db: AsyncSession,
    report_id: str,
    organization_id: str,
) -> bool:
    """Deletes a report and associated PDF artifact."""
    report = await get_report(db=db, report_id=report_id, organization_id=organization_id)

    if report.pdf_storage_path and Path(report.pdf_storage_path).exists():
        try:
            Path(report.pdf_storage_path).unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to delete PDF file on disk: {e}")

    await db.delete(report)
    await db.commit()
    logger.info(f"Deleted report {report_id} for org {organization_id}")
    return True
