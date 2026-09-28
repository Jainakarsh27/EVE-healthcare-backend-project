import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.centre_test_offering import CentreTestOffering


class OfferingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, offering_id: uuid.UUID) -> CentreTestOffering | None:
        stmt = (
            select(CentreTestOffering)
            .options(
                selectinload(CentreTestOffering.test),
                selectinload(CentreTestOffering.centre),
            )
            .where(CentreTestOffering.id == offering_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_lock(self, offering_id: uuid.UUID) -> CentreTestOffering | None:
        """Fetch offering with FOR UPDATE lock for transactional consistency."""
        stmt = (
            select(CentreTestOffering)
            .options(
                selectinload(CentreTestOffering.test),
                selectinload(CentreTestOffering.centre),
            )
            .where(CentreTestOffering.id == offering_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_centre_and_test(
        self, centre_id: uuid.UUID, test_id: uuid.UUID
    ) -> CentreTestOffering | None:
        stmt = select(CentreTestOffering).where(
            CentreTestOffering.centre_id == centre_id,
            CentreTestOffering.test_id == test_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, offering: CentreTestOffering) -> CentreTestOffering:
        self.session.add(offering)
        await self.session.flush()
        return offering

    async def update(self, offering: CentreTestOffering) -> CentreTestOffering:
        await self.session.flush()
        return offering

    async def list_by_centre(
        self,
        centre_id: uuid.UUID,
        is_available: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[CentreTestOffering], int]:
        stmt = (
            select(CentreTestOffering)
            .options(selectinload(CentreTestOffering.test))
            .where(CentreTestOffering.centre_id == centre_id)
        )
        if is_available is not None:
            stmt = stmt.where(CentreTestOffering.is_available == is_available)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = stmt.offset(offset).limit(limit).order_by(CentreTestOffering.created_at.desc())
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total
