"""AEGIS AI — Standardized Error Handling Module
Provides base API exceptions and formatted error responses according to the platform spec:
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable message",
        "request_id": "..."
    }
}
"""

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class AegisException(Exception):
    """Base exception for all AEGIS domain errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(AegisException):
    def __init__(self, message: str = "Invalid credentials or token expired"):
        super().__init__(
            code="AUTHENTICATION_FAILED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class PermissionDeniedError(AegisException):
    def __init__(self, message: str = "You do not have permission to execute this action"):
        super().__init__(
            code="PERMISSION_DENIED",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class TenantIsolationError(AegisException):
    def __init__(self, message: str = "Cross-tenant access prohibited"):
        super().__init__(
            code="TENANT_ISOLATION_VIOLATION",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ResourceNotFoundError(AegisException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=f"{resource} '{identifier}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class SQLSafetyViolationError(AegisException):
    def __init__(self, reason: str):
        super().__init__(
            code="SQL_SAFETY_VIOLATION",
            message=f"SQL query rejected for security reasons: {reason}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class ToolExecutionError(AegisException):
    def __init__(self, tool_name: str, reason: str):
        super().__init__(
            code="TOOL_EXECUTION_FAILED",
            message=f"Tool '{tool_name}' execution failed: {reason}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class ApprovalRequiredError(AegisException):
    def __init__(self, approval_id: str, action_name: str):
        super().__init__(
            code="HUMAN_APPROVAL_REQUIRED",
            message=f"Action '{action_name}' requires human approval before proceeding.",
            status_code=status.HTTP_202_ACCEPTED,
            details={"approval_id": approval_id, "action": action_name},
        )


def aegis_exception_handler(request: Request, exc: AegisException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown-request-id")
    response_content = {
        "error": {
            "code": exc.code,
            "message": exc.message,
            "request_id": request_id,
        }
    }
    if exc.details:
        response_content["error"]["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=response_content)


def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown-request-id")
    code_map = {
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
    }
    code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    message = str(exc.detail) if exc.detail else "An HTTP error occurred"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
    )


def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown-request-id")
    # Never expose stack traces or raw internal exception representations to the client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred. Please contact system support.",
                "request_id": request_id,
            }
        },
    )
