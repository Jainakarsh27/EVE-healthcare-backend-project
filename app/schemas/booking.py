import uuid
from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.centre import CentreResponse
from app.schemas.test import TestResponse
from app.schemas.user import UserResponse
from app.utils.enums import BookingStatus


class BookingCreate(BaseModel):
    centre_id: uuid.UUID
    offering_id: uuid.UUID
    appointment_at: datetime = Field(..., description="ISO 8601 timezone-aware appointment date & time")

    @field_validator("appointment_at")
    @classmethod
    def validate_future_datetime(cls, v: datetime) -> datetime:
        now = datetime.now(UTC)
        if v.tzinfo is None:
            # Assume UTC if naive, but warn/set tz
            v = v.replace(tzinfo=UTC)
        if v <= now:
            raise ValueError("Appointment date/time must be in the future")
        return v


class BookingStatusHistoryResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    previous_status: str | None = None
    new_status: str
    reason: str | None = None
    changed_by: uuid.UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookingResponse(BaseModel):
    id: uuid.UUID
    booking_reference: str
    user_id: uuid.UUID
    centre_id: uuid.UUID
    test_id: uuid.UUID
    offering_id: uuid.UUID
    appointment_at: datetime
    amount: Decimal
    currency: str
    status: BookingStatus
    idempotency_key: str | None = None
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None = None

    user: UserResponse | None = None
    centre: CentreResponse | None = None
    test: TestResponse | None = None
    status_history: list[BookingStatusHistoryResponse] | None = None

    model_config = ConfigDict(from_attributes=True)


class BookingCancelRequest(BaseModel):
    reason: str | None = Field("Cancelled by user", max_length=255)
