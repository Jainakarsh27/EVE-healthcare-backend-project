import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin, get_db
from app.models.user import User
from app.schemas.centre import CentreCreate, CentreResponse, CentreUpdate
from app.services.centre_service import CentreService
from app.utils.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/centres", tags=["Diagnostic Centres"])


@router.get(
    "",
    response_model=PaginatedResponse[CentreResponse],
    status_code=status.HTTP_200_OK,
    summary="List diagnostic centres",
    description="Retrieve diagnostic centres with optional filtering by city, test_code, and active status.",
)
async def list_centres(
    city: str | None = Query(None, description="Filter by city name"),
    test_code: str | None = Query(None, description="Filter centres offering test code e.g. CBC"),
    is_active: bool | None = Query(True, description="Filter active/inactive centres"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    params = PaginationParams(page=page, page_size=page_size)
    service = CentreService(db)
    return await service.list_centres(
        city=city, test_code=test_code, is_active=is_active, params=params
    )


@router.get(
    "/{centre_id}",
    response_model=CentreResponse,
    status_code=status.HTTP_200_OK,
    summary="Get diagnostic centre by ID",
    description="Retrieve details of a specific diagnostic centre.",
)
async def get_centre(centre_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = CentreService(db)
    return await service.get_centre(centre_id)


@router.post(
    "",
    response_model=CentreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create diagnostic centre (Admin)",
    description="Create a new diagnostic centre. Requires ADMIN role.",
)
async def create_centre(
    centre_in: CentreCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    service = CentreService(db)
    return await service.create_centre(centre_in)


@router.patch(
    "/{centre_id}",
    response_model=CentreResponse,
    status_code=status.HTTP_200_OK,
    summary="Update diagnostic centre (Admin)",
    description="Update fields of an existing diagnostic centre. Requires ADMIN role.",
)
async def update_centre(
    centre_id: uuid.UUID,
    centre_in: CentreUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    service = CentreService(db)
    return await service.update_centre(centre_id, centre_in)


@router.delete(
    "/{centre_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate diagnostic centre (Admin)",
    description="Deactivate a diagnostic centre (soft delete). Requires ADMIN role.",
)
async def delete_centre(
    centre_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    service = CentreService(db)
    await service.delete_centre(centre_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
