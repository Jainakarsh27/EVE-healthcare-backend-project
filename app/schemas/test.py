import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TestBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50, description="Unique test code like CBC, LIPID_PROFILE")
    description: str | None = None
    category: str = Field(..., min_length=2, max_length=100)
    preparation_instructions: str | None = None


class TestCreate(TestBase):
    is_active: bool = True


class TestUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    code: str | None = Field(None, min_length=2, max_length=50)
    description: str | None = None
    category: str | None = Field(None, min_length=2, max_length=100)
    preparation_instructions: str | None = None
    is_active: bool | None = None


class TestResponse(TestBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
