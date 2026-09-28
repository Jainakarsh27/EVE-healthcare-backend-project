import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin, get_db
from app.models.user import User
from app.schemas.test import TestCreate, TestResponse, TestUpdate
from app.services.test_service import TestService
from app.utils.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/tests", tags=["Diagnostic Tests"])


@router.get(
    "",
    response_model=PaginatedResponse[TestResponse],
    status_code=status.HTTP_200_OK,
    summary="List diagnostic tests",
    description="Retrieve catalog of diagnostic tests with category and availability filtering.",
)
async def list_tests(
    category: str | None = Query(None, description="Filter by test category e.g. HAEMATOLOGY"),
    is_active: bool | None = Query(True, description="Filter active/inactive tests"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    params = PaginationParams(page=page, page_size=page_size)
    service = TestService(db)
    return await service.list_tests(category=category, is_active=is_active, params=params)


@router.get(
    "/{test_id}",
    response_model=TestResponse,
    status_code=status.HTTP_200_OK,
    summary="Get diagnostic test by ID",
    description="Retrieve details of a specific diagnostic test by its ID.",
)
async def get_test(test_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = TestService(db)
    return await service.get_test(test_id)


@router.post(
    "",
    response_model=TestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create diagnostic test (Admin)",
    description="Add a new diagnostic test to the global catalog. Requires ADMIN role.",
)
async def create_test(
    test_in: TestCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    service = TestService(db)
    return await service.create_test(test_in)


@router.patch(
    "/{test_id}",
    response_model=TestResponse,
    status_code=status.HTTP_200_OK,
    summary="Update diagnostic test (Admin)",
    description="Update details of a diagnostic test in the catalog. Requires ADMIN role.",
)
async def update_test(
    test_id: uuid.UUID,
    test_in: TestUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    service = TestService(db)
    return await service.update_test(test_id, test_in)


@router.delete(
    "/{test_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate diagnostic test (Admin)",
    description="Deactivate a diagnostic test (soft delete). Requires ADMIN role.",
)
async def delete_test(
    test_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    service = TestService(db)
    await service.delete_test(test_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
