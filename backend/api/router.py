"""AEGIS AI — API v1 Router Aggregator
Collects all sub-routers under the /api/v1 prefix.
"""

from fastapi import APIRouter

from backend.api.agents import agents_router
from backend.api.analytics import analytics_router
from backend.api.approvals import approvals_router
from backend.api.auth import router as auth_router
from backend.api.chat import chat_router
from backend.api.documents import kb_router
from backend.api.documents import router as documents_router
from backend.api.evaluations import evaluations_router
from backend.api.ml import ml_router
from backend.api.observability import observability_router
from backend.api.rag import router as rag_router
from backend.api.reports import reports_router
from backend.api.security import security_router
from backend.api.tools import tools_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(agents_router)
api_router.include_router(analytics_router)
api_router.include_router(approvals_router)
api_router.include_router(chat_router)
api_router.include_router(documents_router)
api_router.include_router(evaluations_router)
api_router.include_router(kb_router)
api_router.include_router(ml_router)
api_router.include_router(observability_router)
api_router.include_router(rag_router)
api_router.include_router(reports_router)
api_router.include_router(security_router)
api_router.include_router(tools_router)


