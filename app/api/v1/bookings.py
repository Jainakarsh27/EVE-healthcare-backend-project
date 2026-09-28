import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_idempotency_key
from app.models.user import User
from app.schemas.booking import BookingCancelRequest, BookingCreate, BookingResponse
from app.services.booking_service import BookingService
from app.utils.enums import BookingStatus, UserRole
from app.utils.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create diagnostic test booking",
    description=(
        "Book a diagnostic test appointment. Accepts optional `Idempotency-Key` header to prevent duplicate bookings."
    ),
)
async def create_booking(
    booking_in: BookingCreate,
    idempotency_key: str | None = Depends(get_idempotency_key),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BookingService(db)
    return await service.create_booking(
        user_id=current_user.id,
        booking_in=booking_in,
        idempotency_key=idempotency_key,
    )


@router.get(
    "",
    response_model=PaginatedResponse[BookingResponse],
    status_code=status.HTTP_200_OK,
    summary="List bookings",
    description="Retrieve paginated list of bookings. Users can view their own bookings; Admins can view all.",
)
async def list_bookings(
    status_filter: BookingStatus | None = Query(None, alias="status", description="Filter by booking status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    params = PaginationParams(page=page, page_size=page_size)
    is_admin = current_user.role == UserRole.ADMIN
    service = BookingService(db)
    return await service.list_bookings(
        current_user_id=current_user.id,
        is_admin=is_admin,
        status=status_filter,
        params=params,
    )


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get booking details",
    description="Retrieve details of a specific booking. Restricted to booking owner or Admin.",
)
async def get_booking(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    is_admin = current_user.role == UserRole.ADMIN
    service = BookingService(db)
    return await service.get_booking(
        booking_id=booking_id, current_user_id=current_user.id, is_admin=is_admin
    )


@router.post(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel booking",
    description="Cancel a PENDING or CONFIRMED booking. Restricted to booking owner or Admin.",
)
async def cancel_booking(
    booking_id: uuid.UUID,
    cancel_in: BookingCancelRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    is_admin = current_user.role == UserRole.ADMIN
    reason = cancel_in.reason if cancel_in else "Cancelled by user"
    service = BookingService(db)
    return await service.cancel_booking(
        booking_id=booking_id,
        current_user_id=current_user.id,
        is_admin=is_admin,
        reason=reason,
    )
