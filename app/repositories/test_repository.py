import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagnostic_test import DiagnosticTest


class TestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, test_id: uuid.UUID) -> DiagnosticTest | None:
        result = await self.session.execute(
            select(DiagnosticTest).where(DiagnosticTest.id == test_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> DiagnosticTest | None:
        result = await self.session.execute(
            select(DiagnosticTest).where(func.lower(DiagnosticTest.code) == code.lower())
        )
        return result.scalar_one_or_none()

    async def create(self, test: DiagnosticTest) -> DiagnosticTest:
        self.session.add(test)
        await self.session.flush()
        return test

    async def update(self, test: DiagnosticTest) -> DiagnosticTest:
        await self.session.flush()
        return test

    async def list_tests(
        self,
        category: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[DiagnosticTest], int]:
        stmt = select(DiagnosticTest)
        if is_active is not None:
            stmt = stmt.where(DiagnosticTest.is_active == is_active)
        if category:
            stmt = stmt.where(func.lower(DiagnosticTest.category) == category.lower())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = stmt.offset(offset).limit(limit).order_by(DiagnosticTest.name.asc())
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total
