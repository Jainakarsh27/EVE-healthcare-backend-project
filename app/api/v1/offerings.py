import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin, get_db
from app.models.user import User
from app.schemas.offering import OfferingCreate, OfferingResponse, OfferingUpdate
from app.services.centre_service import CentreService
from app.utils.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/centres/{centre_id}/tests", tags=["Centre Test Offerings"])


@router.get(
    "",
    response_model=PaginatedResponse[OfferingResponse],
    status_code=status.HTTP_200_OK,
    summary="List tests offered by a centre",
    description="Retrieve all diagnostic tests and pricing offered by a specific centre.",
)
async def list_centre_offerings(
    centre_id: uuid.UUID,
    is_available: bool | None = Query(True, description="Filter available/unavailable offerings"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    params = PaginationParams(page=page, page_size=page_size)
    service = CentreService(db)
    return await service.list_offerings(
        centre_id=centre_id, is_available=is_available, params=params
    )


@router.post(
    "",
    response_model=OfferingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add test offering to centre (Admin)",
    description="Link a diagnostic test to a centre with custom pricing and duration. Requires ADMIN role.",
)
async def add_test_offering(
    centre_id: uuid.UUID,
    offering_in: OfferingCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    service = CentreService(db)
    return await service.add_offering(centre_id=centre_id, offering_in=offering_in)


@router.patch(
    "/{offering_id}",
    response_model=OfferingResponse,
    status_code=status.HTTP_200_OK,
    summary="Update test offering at centre (Admin)",
    description="Update pricing, duration, or availability of a centre test offering. Requires ADMIN role.",
)
async def update_test_offering(
    centre_id: uuid.UUID,
    offering_id: uuid.UUID,
    offering_in: OfferingUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    service = CentreService(db)
    return await service.update_offering(
        centre_id=centre_id, offering_id=offering_id, offering_in=offering_in
    )
