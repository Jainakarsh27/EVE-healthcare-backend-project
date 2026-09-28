from typing import Any

from fastapi import status


class AppException(Exception):
    """Base application exception with error code, HTTP status, and message."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", code: str = "NOT_FOUND"):
        super().__init__(message=message, code=code, status_code=status.HTTP_404_NOT_FOUND)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Could not validate credentials", code: str = "UNAUTHORIZED"):
        super().__init__(message=message, code=code, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Access forbidden", code: str = "FORBIDDEN"):
        super().__init__(message=message, code=code, status_code=status.HTTP_403_FORBIDDEN)


class ConflictError(AppException):
    def __init__(self, message: str = "Resource conflict", code: str = "CONFLICT"):
        super().__init__(message=message, code=code, status_code=status.HTTP_409_CONFLICT)


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", code: str = "VALIDATION_ERROR"):
        super().__init__(message=message, code=code, status_code=status.HTTP_400_BAD_REQUEST)


class InvalidStateTransitionError(AppException):
    def __init__(
        self, message: str = "Invalid status transition", code: str = "INVALID_STATE_TRANSITION"
    ):
        super().__init__(message=message, code=code, status_code=status.HTTP_400_BAD_REQUEST)


class InvalidWebhookSignatureError(AppException):
    def __init__(
        self, message: str = "Invalid webhook signature", code: str = "INVALID_WEBHOOK_SIGNATURE"
    ):
        super().__init__(message=message, code=code, status_code=status.HTTP_401_UNAUTHORIZED)


class InvalidWebhookAmountError(AppException):
    def __init__(
        self, message: str = "Webhook payment amount mismatch", code: str = "INVALID_WEBHOOK_AMOUNT"
    ):
        super().__init__(message=message, code=code, status_code=status.HTTP_400_BAD_REQUEST)


class DuplicateWebhookEventError(AppException):
    def __init__(
        self, message: str = "Webhook event already processed", code: str = "DUPLICATE_WEBHOOK_EVENT"
    ):
        # We can handle duplicate webhooks idempotently with HTTP 200 or 409
        super().__init__(message=message, code=code, status_code=status.HTTP_200_OK)
