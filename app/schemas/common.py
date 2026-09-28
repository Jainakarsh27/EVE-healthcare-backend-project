from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Unique error code identifier")
    message: str = Field(..., description="Human-readable error message")
    request_id: str | None = Field(None, description="Correlation request ID")
    details: dict[str, Any] | None = Field(None, description="Additional context or validation errors")


class ErrorResponse(BaseModel):
    success: bool = Field(False, description="Always false for error responses")
    error: ErrorDetail


class SuccessResponse(BaseModel):
    success: bool = Field(True, description="Always true for success responses")
    message: str = Field(..., description="Success message")
    data: dict[str, Any] | None = None
