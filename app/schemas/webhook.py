from decimal import Decimal

from pydantic import BaseModel, Field

from app.utils.enums import PaymentStatus


class WebhookPayload(BaseModel):
    event_id: str = Field(..., min_length=1, description="Unique payment provider event ID")
    event_type: str = Field(..., description="Event type, e.g., payment.updated")
    provider_payment_id: str = Field(..., description="Provider payment reference ID")
    status: PaymentStatus = Field(..., description="Payment status (SUCCESS or FAILED)")
    amount: Decimal = Field(..., gt=0, description="Payment transaction amount")
    currency: str = Field(default="INR", description="Currency string")


class WebhookResponse(BaseModel):
    status: str = Field(..., description="'processed', 'already_processed', or 'rejected'")
    event_id: str
    message: str
    details: dict | None = None
