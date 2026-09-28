import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.centre_test_offering import CentreTestOffering
from app.models.diagnostic_centre import DiagnosticCentre
from app.repositories.centre_repository import CentreRepository
from app.repositories.offering_repository import OfferingRepository
from app.repositories.test_repository import TestRepository
from app.schemas.centre import CentreCreate, CentreResponse, CentreUpdate
from app.schemas.offering import OfferingCreate, OfferingResponse, OfferingUpdate
from app.utils.pagination import PaginatedResponse, PaginationParams


class CentreService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.centre_repo = CentreRepository(session)
        self.test_repo = TestRepository(session)
        self.offering_repo = OfferingRepository(session)

    async def create_centre(self, centre_in: CentreCreate) -> CentreResponse:
        centre = DiagnosticCentre(
            name=centre_in.name,
            address=centre_in.address,
            city=centre_in.city,
            state=centre_in.state,
            pincode=centre_in.pincode,
            latitude=centre_in.latitude,
            longitude=centre_in.longitude,
            is_active=centre_in.is_active,
        )
        created = await self.centre_repo.create(centre)
        await self.session.commit()
        return CentreResponse.model_validate(created)

    async def get_centre(self, centre_id: uuid.UUID) -> CentreResponse:
        centre = await self.centre_repo.get_by_id(centre_id)
        if not centre:
            raise NotFoundError(message="Diagnostic centre not found", code="CENTRE_NOT_FOUND")
        return CentreResponse.model_validate(centre)

    async def update_centre(
        self, centre_id: uuid.UUID, centre_in: CentreUpdate
    ) -> CentreResponse:
        centre = await self.centre_repo.get_by_id(centre_id)
        if not centre:
            raise NotFoundError(message="Diagnostic centre not found", code="CENTRE_NOT_FOUND")

        update_data = centre_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(centre, field, value)

        updated = await self.centre_repo.update(centre)
        await self.session.commit()
        return CentreResponse.model_validate(updated)

    async def delete_centre(self, centre_id: uuid.UUID) -> None:
        """Deactivate centre (soft delete to preserve historical bookings)."""
        centre = await self.centre_repo.get_by_id(centre_id)
        if not centre:
            raise NotFoundError(message="Diagnostic centre not found", code="CENTRE_NOT_FOUND")
        centre.is_active = False
        await self.centre_repo.update(centre)
        await self.session.commit()

    async def list_centres(
        self,
        city: str | None = None,
        test_code: str | None = None,
        is_active: bool | None = None,
        params: PaginationParams | None = None,
    ) -> PaginatedResponse[CentreResponse]:
        params = params or PaginationParams()
        items, total = await self.centre_repo.list_centres(
            city=city,
            test_code=test_code,
            is_active=is_active,
            offset=params.offset,
            limit=params.page_size,
        )
        centre_responses = [CentreResponse.model_validate(item) for item in items]
        return PaginatedResponse.create(centre_responses, total, params)

    # Centre Test Offerings Logic
    async def add_offering(
        self, centre_id: uuid.UUID, offering_in: OfferingCreate
    ) -> OfferingResponse:
        centre = await self.centre_repo.get_by_id(centre_id)
        if not centre:
            raise NotFoundError(message="Diagnostic centre not found", code="CENTRE_NOT_FOUND")

        test = await self.test_repo.get_by_id(offering_in.test_id)
        if not test:
            raise NotFoundError(message="Diagnostic test not found", code="TEST_NOT_FOUND")

        existing = await self.offering_repo.get_by_centre_and_test(centre_id, offering_in.test_id)
        if existing:
            raise ConflictError(
                message="This test is already offered by the diagnostic centre",
                code="OFFERING_ALREADY_EXISTS",
            )

        offering = CentreTestOffering(
            centre_id=centre_id,
            test_id=offering_in.test_id,
            price=offering_in.price,
            duration_minutes=offering_in.duration_minutes,
            is_available=offering_in.is_available,
        )
        created = await self.offering_repo.create(offering)
        await self.session.commit()
        fetched = await self.offering_repo.get_by_id(created.id)
        return OfferingResponse.model_validate(fetched)

    async def list_offerings(
        self,
        centre_id: uuid.UUID,
        is_available: bool | None = None,
        params: PaginationParams | None = None,
    ) -> PaginatedResponse[OfferingResponse]:
        centre = await self.centre_repo.get_by_id(centre_id)
        if not centre:
            raise NotFoundError(message="Diagnostic centre not found", code="CENTRE_NOT_FOUND")

        params = params or PaginationParams()
        items, total = await self.offering_repo.list_by_centre(
            centre_id=centre_id,
            is_available=is_available,
            offset=params.offset,
            limit=params.page_size,
        )
        responses = [OfferingResponse.model_validate(item) for item in items]
        return PaginatedResponse.create(responses, total, params)

    async def update_offering(
        self, centre_id: uuid.UUID, offering_id: uuid.UUID, offering_in: OfferingUpdate
    ) -> OfferingResponse:
        offering = await self.offering_repo.get_by_id(offering_id)
        if not offering or offering.centre_id != centre_id:
            raise NotFoundError(message="Test offering not found", code="OFFERING_NOT_FOUND")

        update_data = offering_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(offering, field, value)

        updated = await self.offering_repo.update(offering)
        await self.session.commit()
        refetched = await self.offering_repo.get_by_id(updated.id)
        return OfferingResponse.model_validate(refetched)
