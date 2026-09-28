import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash password securely using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password in constant-time."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    role: str,
    email: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token with claims."""
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "email": email,
        "role": role,
        "exp": expire,
        "iat": now,
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.PyJWTError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise jwt.PyJWTError(f"Invalid token: {str(e)}")


def generate_webhook_signature(payload: bytes, secret: str) -> str:
    """Generate HMAC SHA256 signature for webhook verification."""
    mac = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256)
    return mac.hexdigest()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC SHA256 signature in constant time."""
    expected_signature = generate_webhook_signature(payload, secret)
    return hmac.compare_digest(expected_signature.lower(), signature.lower())
