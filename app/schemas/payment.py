import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    booking_id: uuid.UUID
    payment_method: PaymentMethod = Field(
        default=PaymentMethod.MOCK_SUCCESS,
        description="Payment method (MOCK_SUCCESS, MOCK_FAILURE, CARD, UPI)",
    )


class PaymentResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    provider_payment_id: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    payment_method: str
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
