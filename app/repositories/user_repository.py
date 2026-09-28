import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user

    async def update(self, user: User) -> User:
        await self.session.flush()
        return user

    async def list_users(self, offset: int = 0, limit: int = 20) -> tuple[Sequence[User], int]:
        count_stmt = select(func.count()).select_from(User)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = select(User).offset(offset).limit(limit).order_by(User.created_at.desc())
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total
