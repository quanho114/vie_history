"""Custom exception hierarchy for precise error handling."""

from typing import Any

from fastapi import HTTPException, status


class HistoriAIException(Exception):
    """Base exception for all HistoriAI errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        public_message: str | None = None,
    ):
        self.message = message
        self.details = details or {}
        self.public_message = public_message or "An internal error occurred."
        super().__init__(self.message)


# ─── Retrieval Errors ─────────────────────────────────────────────────────────


class RetrievalError(HistoriAIException):
    """Base class for retrieval-related errors."""

    pass


class VectorSearchUnavailableError(RetrievalError):
    """Qdrant vector search is unavailable."""

    def __init__(self, details: dict | None = None):
        super().__init__(
            message="Vector search engine unavailable",
            details=details,
            public_message="Tìm kiếm vector đang tạm thời không khả dụng. Vui lòng thử lại sau.",
        )


class BM25IndexError(RetrievalError):
    """BM25 indexing/search error."""

    def __init__(self, details: dict | None = None):
        super().__init__(
            message="BM25 search engine error",
            details=details,
            public_message="Tìm kiếm từ khóa đang tạm thời không khả dụng.",
        )


class EmbeddingModelError(RetrievalError):
    """Embedding model loading or inference error."""

    def __init__(self, model_name: str, details: dict | None = None):
        super().__init__(
            message=f"Embedding model error: {model_name}",
            details={"model": model_name, **(details or {})},
            public_message="Mô hình embedding đang gặp sự cố.",
        )


# ─── LLM Errors ───────────────────────────────────────────────────────────────


class LLMError(HistoriAIException):
    """Base class for LLM-related errors."""

    pass


class LLMAPIKeyMissingError(LLMError):
    """No LLM API key configured."""

    def __init__(self, provider: str):
        super().__init__(
            message=f"No API key configured for {provider}",
            details={"provider": provider},
            public_message="Vui lòng cấu hình API key LLM trong phần Cài đặt.",
        )


class APIKeyMissingError(HistoriAIException):
    """Custom exception raised when an LLM API Key is missing or invalid."""

    def __init__(self, provider: str = ""):
        super().__init__(
            message="API_KEY_MISSING: Không tìm thấy cấu hình mô hình ngôn ngữ.",
            public_message="Không tìm thấy cấu hình mô hình ngôn ngữ.\n\nVui lòng thêm API Key trong phần Cài đặt trước khi sử dụng chức năng hỏi đáp nâng cao của HistoriAI.",
            details={"provider": provider},
        )



class LLMRateLimitError(LLMError):
    """LLM provider rate limit exceeded."""

    def __init__(self, provider: str, retry_after_s: float | None = None):
        super().__init__(
            message=f"Rate limit exceeded for {provider}",
            details={"provider": provider, "retry_after_s": retry_after_s},
            public_message="Đã vượt giới hạn yêu cầu. Vui lòng chờ và thử lại.",
        )


class LLMCircuitBreakerOpenError(LLMError):
    """Circuit breaker is open — LLM calls blocked."""

    def __init__(self, service: str, timeout_s: float):
        super().__init__(
            message=f"Circuit breaker open for {service}",
            details={"service": service, "timeout_s": timeout_s},
            public_message="Dịch vụ AI đang tạm thời quá tải. Vui lòng thử lại sau vài phút.",
        )


# ─── Document Errors ──────────────────────────────────────────────────────────


class DocumentError(HistoriAIException):
    """Base class for document errors."""

    pass


class DocumentNotFoundError(DocumentError):
    """Document not found."""

    def __init__(self, doc_id: str):
        super().__init__(
            message=f"Document not found: {doc_id}",
            details={"document_id": doc_id},
            public_message="Tài liệu không tìm thấy.",
        )


class DocumentApprovalRequiredError(DocumentError):
    """Document pending admin approval."""

    def __init__(self, doc_id: str):
        super().__init__(
            message=f"Document requires approval: {doc_id}",
            details={"document_id": doc_id},
            public_message="Tài liệu này đang chờ kiểm duyệt và chưa được phê duyệt.",
        )


# ─── Service Errors ───────────────────────────────────────────────────────────


class ServiceUnavailableError(HistoriAIException):
    """External service (Qdrant, Elasticsearch, Neo4j) is unavailable."""

    def __init__(self, service: str, details: dict | None = None):
        super().__init__(
            message=f"Service unavailable: {service}",
            details={"service": service, **(details or {})},
            public_message=f"Dịch vụ {service} đang tạm thời không khả dụng. Vui lòng thử lại sau.",
        )


# ─── Authentication Errors ───────────────────────────────────────────────────


class AuthenticationError(HistoriAIException):
    """Authentication failed."""

    def __init__(self, details: dict | None = None):
        super().__init__(
            message="Authentication failed",
            details=details or {},
            public_message="Xác thực thất bại. Vui lòng đăng nhập lại.",
        )


# ─── Rate Limit Errors ────────────────────────────────────────────────────────


class RateLimitExceededError(HistoriAIException):
    """Rate limit exceeded for a user/IP."""

    def __init__(self, retry_after_s: int | None = None, details: dict | None = None):
        super().__init__(
            message="Rate limit exceeded",
            details={"retry_after_s": retry_after_s, **(details or {})},
            public_message="Đã vượt giới hạn yêu cầu. Vui lòng chờ và thử lại.",
        )


# ─── Validation Errors ───────────────────────────────────────────────────────


class ValidationError(HistoriAIException):
    """Input validation failed."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message,
            details=details or {},
            public_message=f"Lỗi xác thực dữ liệu: {message}",
        )


# ─── Circuit Breaker Errors ──────────────────────────────────────────────────


class CircuitBreakerOpenError(HistoriAIException):
    """Circuit breaker is open for an external service."""

    def __init__(self, service: str, timeout_s: float):
        super().__init__(
            message=f"Circuit breaker open for {service}",
            details={"service": service, "timeout_s": timeout_s},
            public_message=f"Dịch vụ {service} đang tạm thời quá tải. Vui lòng thử lại sau vài phút.",
        )


# ─── HTTP Exception Factory ──────────────────────────────────────────────────


def histori_to_http(exc: HistoriAIException) -> HTTPException:
    """Map domain exceptions to HTTP responses."""
    mapping = {
        RetrievalError: (status.HTTP_503_SERVICE_UNAVAILABLE, "Service Unavailable"),
        LLMError: (status.HTTP_502_BAD_GATEWAY, "Bad Gateway"),
        DocumentError: (status.HTTP_404_NOT_FOUND, "Not Found"),
        ServiceUnavailableError: (status.HTTP_503_SERVICE_UNAVAILABLE, "Service Unavailable"),
        AuthenticationError: (status.HTTP_401_UNAUTHORIZED, "Unauthorized"),
        RateLimitExceededError: (status.HTTP_429_TOO_MANY_REQUESTS, "Too Many Requests"),
        ValidationError: (status.HTTP_400_BAD_REQUEST, "Bad Request"),
        CircuitBreakerOpenError: (status.HTTP_503_SERVICE_UNAVAILABLE, "Service Unavailable"),
        HistoriAIException: (status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal Error"),
    }

    for exc_type, (code, phrase) in mapping.items():
        if isinstance(exc, exc_type):
            return HTTPException(
                status_code=code,
                detail={
                    "message": exc.public_message,
                    "error_id": exc.details.get("error_id"),
                },
            )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"message": exc.public_message},
    )
