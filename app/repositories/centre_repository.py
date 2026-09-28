import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.centre_test_offering import CentreTestOffering
from app.models.diagnostic_centre import DiagnosticCentre
from app.models.diagnostic_test import DiagnosticTest


class CentreRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, centre_id: uuid.UUID) -> DiagnosticCentre | None:
        result = await self.session.execute(
            select(DiagnosticCentre).where(DiagnosticCentre.id == centre_id)
        )
        return result.scalar_one_or_none()

    async def create(self, centre: DiagnosticCentre) -> DiagnosticCentre:
        self.session.add(centre)
        await self.session.flush()
        return centre

    async def update(self, centre: DiagnosticCentre) -> DiagnosticCentre:
        await self.session.flush()
        return centre

    async def list_centres(
        self,
        city: str | None = None,
        test_code: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[DiagnosticCentre], int]:
        stmt = select(DiagnosticCentre)
        if is_active is not None:
            stmt = stmt.where(DiagnosticCentre.is_active == is_active)
        if city:
            stmt = stmt.where(func.lower(DiagnosticCentre.city) == city.lower())
        if test_code:
            stmt = (
                stmt.join(CentreTestOffering, CentreTestOffering.centre_id == DiagnosticCentre.id)
                .join(DiagnosticTest, DiagnosticTest.id == CentreTestOffering.test_id)
                .where(
                    func.lower(DiagnosticTest.code) == test_code.lower(),
                    CentreTestOffering.is_available.is_(True),
                )
            )

        # Count query
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = stmt.offset(offset).limit(limit).order_by(DiagnosticCentre.name.asc())
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total
