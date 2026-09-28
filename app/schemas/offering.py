import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.centre import CentreResponse
from app.schemas.test import TestResponse


class OfferingCreate(BaseModel):
    test_id: uuid.UUID
    price: Decimal = Field(..., gt=0, description="Offering price (must be greater than 0)")
    duration_minutes: int = Field(30, gt=0, description="Test duration in minutes")
    is_available: bool = True


class OfferingUpdate(BaseModel):
    price: Decimal | None = Field(None, gt=0)
    duration_minutes: int | None = Field(None, gt=0)
    is_available: bool | None = None


class OfferingResponse(BaseModel):
    id: uuid.UUID
    centre_id: uuid.UUID
    test_id: uuid.UUID
    price: Decimal
    duration_minutes: int
    is_available: bool
    created_at: datetime
    updated_at: datetime

    # Nested models for detailed representation
    test: TestResponse | None = None
    centre: CentreResponse | None = None

    model_config = ConfigDict(from_attributes=True)
