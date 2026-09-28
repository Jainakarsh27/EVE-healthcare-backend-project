import uuid

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserResponse
from app.utils.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenPayload(BaseModel):
    sub: uuid.UUID | None = None
    email: str | None = None
    role: UserRole | None = None
    exp: int | None = None
