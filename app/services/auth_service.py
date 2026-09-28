from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserResponse
from app.utils.enums import UserRole


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def signup(self, user_in: UserCreate) -> UserResponse:
        existing_user = await self.user_repo.get_by_email(user_in.email)
        if existing_user:
            raise ConflictError(
                message=f"User with email '{user_in.email}' already exists",
                code="EMAIL_ALREADY_EXISTS",
            )

        hashed_pwd = hash_password(user_in.password)
        new_user = User(
            email=user_in.email.lower(),
            password_hash=hashed_pwd,
            full_name=user_in.full_name,
            phone=user_in.phone,
            role=user_in.role or UserRole.USER,
            is_active=True,
        )

        user = await self.user_repo.create(new_user)
        await self.session.commit()
        return UserResponse.model_validate(user)

    async def login(self, login_in: LoginRequest) -> Token:
        user = await self.user_repo.get_by_email(login_in.email)
        if not user or not verify_password(login_in.password, user.password_hash):
            raise UnauthorizedError(
                message="Invalid email or password",
                code="INVALID_CREDENTIALS",
            )

        if not user.is_active:
            raise ForbiddenError(
                message="User account is deactivated",
                code="USER_INACTIVE",
            )

        token_str = create_access_token(
            subject=str(user.id),
            role=user.role.value,
            email=user.email,
        )

        user_resp = UserResponse.model_validate(user)
        return Token(
            access_token=token_str,
            token_type="bearer",
            expires_in=60 * 60,  # 1 hour in seconds
            user=user_resp,
        )
