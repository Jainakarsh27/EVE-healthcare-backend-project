from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin, get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserResponse
from app.utils.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List all users (Admin only)",
    description="Retrieve paginated list of system users. Requires ADMIN role.",
)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    params = PaginationParams(page=page, page_size=page_size)
    repo = UserRepository(db)
    items, total = await repo.list_users(offset=params.offset, limit=params.page_size)
    responses = [UserResponse.model_validate(u) for u in items]
    return PaginatedResponse.create(responses, total, params)
