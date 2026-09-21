"""AEGIS AI — All Database Models Export
Ensures all 23 database models are registered with SQLAlchemy declarative metadata.
"""

from backend.db.base import Base
from backend.models.agent import (
    AgentRun,
    AgentStep,
    Approval,
    ToolCall,
)
from backend.models.analytics import (
    Memory,
    MLModel,
    MLPrediction,
    Report,
)
from backend.models.chat import (
    Conversation,
    Message,
)
from backend.models.document import (
    Document,
    DocumentChunk,
    KnowledgeBase,
    KnowledgeBaseDocument,
)
from backend.models.governance import (
    AuditLog,
    Evaluation,
    UsageEvent,
)
from backend.models.identity import (
    Organization,
    OrganizationMember,
    Permission,
    Role,
    RolePermission,
    User,
)

__all__ = [
    "Base",
    # Identity & RBAC
    "Organization",
    "User",
    "Role",
    "Permission",
    "RolePermission",
    "OrganizationMember",
    # Chat & Conversations
    "Conversation",
    "Message",
    # Documents & Knowledge Bases
    "KnowledgeBase",
    "Document",
    "KnowledgeBaseDocument",
    "DocumentChunk",
    # Agent Runtime
    "AgentRun",
    "AgentStep",
    "ToolCall",
    "Approval",
    # Analytics & ML
    "Report",
    "MLModel",
    "MLPrediction",
    "Memory",
    # Governance & Observability
    "Evaluation",
    "UsageEvent",
    "AuditLog",
]
