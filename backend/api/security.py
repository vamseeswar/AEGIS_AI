"""AEGIS AI — Security Policies & Prompt Defense API Router
Endpoints:
  GET  /api/v1/security/policies            - Overview of active enterprise security policies
  POST /api/v1/security/prompt-defense/test - Test XML boundary defense and breakout detection
  GET  /api/v1/security/rate-limits/status  - Check real-time rate limit token bucket status
"""

from fastapi import APIRouter, Depends, Request

from backend.schemas.security import (
    PromptDefenseTestRequest,
    PromptDefenseTestResponse,
    RateLimitStatusResponse,
    SecurityPoliciesResponse,
)
from backend.security.dependencies import CurrentUser, get_current_user
from backend.security.prompt_defense import (
    build_hardened_prompt,
    detect_delimiter_breakout_attempt,
)
from backend.security.rate_limiter import rate_limiter

security_router = APIRouter(prefix="/security", tags=["Security & Hardening"])


@security_router.get(
    "/policies",
    response_model=SecurityPoliciesResponse,
    summary="Active enterprise security posture & hardening policies",
)
async def get_security_policies() -> SecurityPoliciesResponse:
    """Returns overview of rate limiting, security headers, XML boundaries, and file defenses."""
    return SecurityPoliciesResponse(
        rate_limiting={
            "enabled": True,
            "ip_limit_per_minute": 120,
            "tenant_limit_per_minute": 600,
            "algorithm": "Token Bucket with Monotonic Refill",
        },
        security_headers={
            "hsts": "max-age=31536000; includeSubDomains",
            "x_frame_options": "DENY",
            "x_content_type_options": "nosniff",
            "referrer_policy": "strict-origin-when-cross-origin",
            "csp_enforced": True,
        },
        prompt_defense={
            "xml_delimiters_enforced": True,
            "boundary_tags": ["<untrusted_document>", "<untrusted_user_query>", "<system_instructions>"],
            "breakout_detection_active": True,
            "anti_tamper_instructions": True,
        },
        path_traversal_defense={
            "null_byte_rejection": True,
            "windows_device_names_blocked": ["CON", "PRN", "AUX", "NUL", "COM1-9", "LPT1-9"],
            "directory_traversal_confinement": True,
        },
    )


@security_router.post(
    "/prompt-defense/test",
    response_model=PromptDefenseTestResponse,
    summary="Simulate prompt defense XML boundary encapsulation",
)
async def test_prompt_defense(
    payload: PromptDefenseTestRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> PromptDefenseTestResponse:
    """Evaluates user query and context documents for boundary breakout and produces hardened prompt."""
    # Check for forged delimiter breakout
    has_breakout, tags = detect_delimiter_breakout_attempt(payload.user_query)
    for doc in payload.context_documents:
        content = doc.get("content") or doc.get("text") or ""
        doc_breakout, doc_tags = detect_delimiter_breakout_attempt(content)
        if doc_breakout:
            has_breakout = True
            tags.extend(doc_tags)

    hardened = build_hardened_prompt(
        system_instructions=payload.system_instructions,
        untrusted_documents=payload.context_documents,
        user_query=payload.user_query,
    )

    return PromptDefenseTestResponse(
        breakout_detected=has_breakout,
        breakout_tags=list(set(tags)),
        hardened_prompt=hardened,
        is_safe=not has_breakout,
    )


@security_router.get(
    "/rate-limits/status",
    response_model=RateLimitStatusResponse,
    summary="Inspect real-time token bucket rate limit status",
)
async def get_rate_limit_status(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> RateLimitStatusResponse:
    """Returns token quota and refill countdown for caller IP and tenant organization."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    ip_status = rate_limiter.get_status(client_ip, bucket_type="ip", capacity=120.0, refill_rate=2.0)
    tenant_status = rate_limiter.get_status(
        current_user.organization_id, bucket_type="tenant", capacity=600.0, refill_rate=10.0
    )

    return RateLimitStatusResponse(
        client_ip=client_ip,
        ip_status=ip_status,
        tenant_status=tenant_status,
    )
