import uuid

import jwt
from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPayload
from app.utils.enums import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_token_payload(token: str | None = Depends(oauth2_scheme)) -> TokenPayload:
    if not token:
        raise UnauthorizedError(message="Not authenticated", code="UNAUTHORIZED")
    try:
        payload_dict = decode_access_token(token)
        sub = payload_dict.get("sub")
        if not sub:
            raise UnauthorizedError(message="Invalid token claims", code="INVALID_TOKEN")
        return TokenPayload(
            sub=uuid.UUID(sub),
            email=payload_dict.get("email"),
            role=UserRole(payload_dict.get("role")),
            exp=payload_dict.get("exp"),
        )
    except (jwt.PyJWTError, ValueError):
        raise UnauthorizedError(message="Invalid or expired access token", code="INVALID_TOKEN")


async def get_current_user(
    payload: TokenPayload = Depends(get_token_payload),
    session: AsyncSession = Depends(get_db),
) -> User:
    repo = UserRepository(session)
    if not payload.sub:
        raise UnauthorizedError(message="Invalid token subject", code="INVALID_TOKEN")

    user = await repo.get_by_id(payload.sub)
    if not user:
        raise UnauthorizedError(message="User no longer exists", code="USER_NOT_FOUND")
    if not user.is_active:
        raise ForbiddenError(message="User account is deactivated", code="USER_INACTIVE")

    return user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError(
            message="Admin privileges required to perform this action",
            code="ADMIN_REQUIRED",
        )
    return current_user


def get_idempotency_key(
    idempotency_key: str | None = Header(None, alias="Idempotency-Key")
) -> str | None:
    if idempotency_key and len(idempotency_key.strip()) > 0:
        return idempotency_key.strip()
    return None
