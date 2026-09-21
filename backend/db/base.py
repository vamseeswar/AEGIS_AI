"""AEGIS AI — SQLAlchemy Declarative Base and Model Mixins
Provides UUID primary keys, automatic UTC timestamps, and tenant isolation mixins.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Returns current UTC timestamp with timezone awareness."""
    return datetime.now(UTC)


def generate_uuid() -> str:
    """Generates a UUID4 string identifier."""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Base class for all AEGIS AI SQLAlchemy models."""
    pass


class TimestampMixin:
    """Provides created_at and updated_at datetime tracking."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class TenantScopedMixin(TimestampMixin):
    """Enforces strict server-side organization_id isolation on tenant-owned resources."""
    organization_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
