"""Hierarchical error classes for HistoriAI API."""
from __future__ import annotations

from typing import Any


class HistoriAIError(Exception):
    """Base exception for all HistoriAI errors."""

    code: str = "HISTORIAI_ERROR"

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        public_message: str | None = None,
    ):
        self.message = message
        self.details = details or {}
        self.public_message = public_message or message
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.public_message,
            "details": self.details,
        }


# ─── Auth Errors ────────────────────────────────────────────────────────────────


class AuthenticationError(HistoriAIError):
    """Authentication failed."""

    code = "AUTH_ERROR"

    def __init__(self, message: str = "Authentication failed", details: dict | None = None):
        super().__init__(
            message=message,
            details=details or {},
            public_message="Xác thực thất bại. Vui lòng đăng nhập lại.",
        )


class InvalidTokenError(AuthenticationError):
    """Token is invalid or malformed."""

    code = "AUTH_INVALID_TOKEN"

    def __init__(self, details: dict | None = None):
        super().__init__(
            message="Invalid or malformed token",
            details=details or {},
        )


class TokenExpiredError(AuthenticationError):
    """Access token has expired."""

    code = "AUTH_TOKEN_EXPIRED"

    def __init__(self, details: dict | None = None):
        super().__init__(
            message="Access token has expired",
            details=details or {},
        )


class RefreshTokenExpiredError(AuthenticationError):
    """Refresh token has expired."""

    code = "AUTH_REFRESH_TOKEN_EXPIRED"

    def __init__(self, details: dict | None = None):
        super().__init__(
            message="Refresh token has expired",
            details=details or {},
            public_message="Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
        )


# ─── Resource Errors ───────────────────────────────────────────────────────────


class ResourceNotFoundError(HistoriAIError):
    """Base class for resource not found errors."""

    code = "RESOURCE_NOT_FOUND"


class DocumentNotFoundError(ResourceNotFoundError):
    """Document not found."""

    code = "RESOURCE_DOCUMENT_NOT_FOUND"

    def __init__(self, doc_id: str | None = None):
        super().__init__(
            message=f"Document not found: {doc_id}" if doc_id else "Document not found",
            details={"resource": "document", "id": doc_id} if doc_id else {"resource": "document"},
            public_message="Tài liệu không tìm thấy.",
        )


class ProjectNotFoundError(ResourceNotFoundError):
    """Project not found."""

    code = "RESOURCE_PROJECT_NOT_FOUND"

    def __init__(self, project_id: str | None = None):
        super().__init__(
            message=f"Project not found: {project_id}" if project_id else "Project not found",
            details={"resource": "project", "id": project_id} if project_id else {"resource": "project"},
            public_message="Dự án không tìm thấy.",
        )


class SessionNotFoundError(ResourceNotFoundError):
    """Session not found."""

    code = "RESOURCE_SESSION_NOT_FOUND"

    def __init__(self, session_id: str | None = None):
        super().__init__(
            message=f"Session not found: {session_id}" if session_id else "Session not found",
            details={"resource": "session", "id": session_id} if session_id else {"resource": "session"},
            public_message="Phiên làm việc không tìm thấy.",
        )


class UserNotFoundError(ResourceNotFoundError):
    """User not found."""

    code = "RESOURCE_USER_NOT_FOUND"

    def __init__(self, user_id: str | None = None):
        super().__init__(
            message=f"User not found: {user_id}" if user_id else "User not found",
            details={"resource": "user", "id": user_id} if user_id else {"resource": "user"},
            public_message="Người dùng không tìm thấy.",
        )


# ─── Ingest Errors ──────────────────────────────────────────────────────────────


class IngestError(HistoriAIError):
    """Base class for ingestion errors."""

    code = "INGEST_ERROR"


class IngestURLError(IngestError):
    """URL ingestion failed."""

    code = "INGEST_URL_ERROR"

    def __init__(self, url: str | None = None, details: dict | None = None):
        super().__init__(
            message=f"URL ingestion failed: {url}" if url else "URL ingestion failed",
            details={"url": url, **(details or {})},
            public_message="Không thể tải nội dung từ URL. Vui lòng kiểm tra lại đường dẫn.",
        )


class IngestFileError(IngestError):
    """File ingestion failed."""

    code = "INGEST_FILE_ERROR"

    def __init__(self, filename: str | None = None, details: dict | None = None):
        super().__init__(
            message=f"File ingestion failed: {filename}" if filename else "File ingestion failed",
            details={"filename": filename, **(details or {})},
            public_message="Không thể xử lý tệp. Vui lòng kiểm tra định dạng và thử lại.",
        )


class IngestRateLimitError(IngestError):
    """Ingestion rate limit exceeded."""

    code = "INGEST_RATE_LIMIT"

    def __init__(self, retry_after: int | None = None, details: dict | None = None):
        super().__init__(
            message="Ingestion rate limit exceeded",
            details={"retry_after_seconds": retry_after, **(details or {})},
            public_message="Đã vượt giới hạn tốc độ nhập liệu. Vui lòng chờ và thử lại.",
        )


# ─── RAG Errors ────────────────────────────────────────────────────────────────


class RetrievalError(HistoriAIError):
    """Base class for retrieval errors."""

    code = "RAG_RETRIEVAL_ERROR"


class SynthesisError(HistoriAIError):
    """Response synthesis failed."""

    code = "RAG_SYNTHESIS_ERROR"

    def __init__(self, details: dict | None = None):
        super().__init__(
            message="Response synthesis failed",
            details=details or {},
            public_message="Không thể tổng hợp câu trả lời. Vui lòng thử lại.",
        )


class EmbeddingError(RetrievalError):
    """Embedding generation failed."""

    code = "RAG_EMBEDDING_ERROR"

    def __init__(self, details: dict | None = None):
        super().__init__(
            message="Embedding generation failed",
            details=details or {},
            public_message="Không thể tạo vector embedding. Vui lòng thử lại.",
        )


class RerankerError(RetrievalError):
    """Reranking failed."""

    code = "RAG_RERANKER_ERROR"

    def __init__(self, details: dict | None = None):
        super().__init__(
            message="Reranking failed",
            details=details or {},
            public_message="Không thể sắp xếp lại kết quả tìm kiếm. Vui lòng thử lại.",
        )


# ─── Security Errors ────────────────────────────────────────────────────────────


class SecurityError(HistoriAIError):
    """Base class for security errors."""

    code = "SECURITY_ERROR"


class RateLimitExceededError(SecurityError):
    """Rate limit exceeded."""

    code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, retry_after: int | None = None, details: dict | None = None):
        super().__init__(
            message="Rate limit exceeded",
            details={"retry_after_seconds": retry_after, **(details or {})},
            public_message="Đã vượt giới hạn yêu cầu. Vui lòng chờ và thử lại.",
        )


class PermissionDeniedError(SecurityError):
    """Permission denied."""

    code = "SECURITY_PERMISSION_DENIED"

    def __init__(self, action: str | None = None, details: dict | None = None):
        super().__init__(
            message=f"Permission denied: {action}" if action else "Permission denied",
            details={"action": action, **(details or {})},
            public_message="Bạn không có quyền thực hiện thao tác này.",
        )


class InputValidationError(SecurityError):
    """Input validation failed."""

    code = "SECURITY_INPUT_VALIDATION"

    def __init__(self, message: str, field: str | None = None, details: dict | None = None):
        super().__init__(
            message=f"Input validation failed: {message}",
            details={"field": field, "message": message, **(details or {})},
            public_message=f"Lỗi xác thực dữ liệu: {message}",
        )


# ─── Infrastructure Errors ──────────────────────────────────────────────────────


class InfrastructureError(HistoriAIError):
    """Base class for infrastructure errors."""

    code = "INFRA_ERROR"


class CacheError(InfrastructureError):
    """Cache operation failed."""

    code = "INFRA_CACHE_ERROR"

    def __init__(self, operation: str | None = None, details: dict | None = None):
        super().__init__(
            message=f"Cache operation failed: {operation}" if operation else "Cache operation failed",
            details={"operation": operation, **(details or {})},
            public_message="Bộ nhớ đệm tạm thời không khả dụng. Thao tác sẽ tiếp tục mà không có cache.",
        )


class DatabaseError(InfrastructureError):
    """Database operation failed."""

    code = "INFRA_DATABASE_ERROR"

    def __init__(self, operation: str | None = None, details: dict | None = None):
        super().__init__(
            message=f"Database operation failed: {operation}" if operation else "Database operation failed",
            details={"operation": operation, **(details or {})},
            public_message="Cơ sở dữ liệu tạm thời không khả dụng. Vui lòng thử lại sau.",
        )


class ExternalServiceError(InfrastructureError):
    """External service call failed."""

    code = "INFRA_EXTERNAL_SERVICE_ERROR"

    def __init__(self, service: str, details: dict | None = None):
        super().__init__(
            message=f"External service failed: {service}",
            details={"service": service, **(details or {})},
            public_message=f"Dịch vụ bên ngoài đang tạm thời không khả dụng. Vui lòng thử lại sau.",
        )


# ─── Error Status Map ──────────────────────────────────────────────────────────


ERROR_STATUS_MAP: dict[str, int] = {
    # Auth errors → 401
    "AUTH_ERROR": 401,
    "AUTH_INVALID_TOKEN": 401,
    "AUTH_TOKEN_EXPIRED": 401,
    "AUTH_REFRESH_TOKEN_EXPIRED": 401,
    # Resource errors → 404
    "RESOURCE_NOT_FOUND": 404,
    "RESOURCE_DOCUMENT_NOT_FOUND": 404,
    "RESOURCE_PROJECT_NOT_FOUND": 404,
    "RESOURCE_SESSION_NOT_FOUND": 404,
    "RESOURCE_USER_NOT_FOUND": 404,
    # Ingest errors → 422/429
    "INGEST_ERROR": 422,
    "INGEST_URL_ERROR": 422,
    "INGEST_FILE_ERROR": 422,
    "INGEST_RATE_LIMIT": 429,
    # RAG errors → 503
    "RAG_RETRIEVAL_ERROR": 503,
    "RAG_EMBEDDING_ERROR": 503,
    "RAG_RERANKER_ERROR": 503,
    "RAG_SYNTHESIS_ERROR": 502,
    # Security errors → 429/403/400
    "RATE_LIMIT_EXCEEDED": 429,
    "SECURITY_ERROR": 403,
    "SECURITY_PERMISSION_DENIED": 403,
    "SECURITY_INPUT_VALIDATION": 400,
    # Infrastructure errors → 503
    "INFRA_ERROR": 503,
    "INFRA_CACHE_ERROR": 503,
    "INFRA_DATABASE_ERROR": 503,
    "INFRA_EXTERNAL_SERVICE_ERROR": 503,
    # Base
    "HISTORIAI_ERROR": 500,
}


def error_to_status(error: HistoriAIError) -> int:
    """Get HTTP status code for an error."""
    return ERROR_STATUS_MAP.get(error.code, 500)
