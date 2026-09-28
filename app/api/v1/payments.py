import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.payment_service import PaymentService
from app.utils.enums import UserRole

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate simulated payment for booking",
    description=(
        "Simulate payment gateway processing for a booking. Payment amount is extracted directly from the booking record."
    ),
)
async def process_payment(
    payment_in: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    is_admin = current_user.role == UserRole.ADMIN
    service = PaymentService(db)
    return await service.create_payment_simulation(
        current_user_id=current_user.id,
        payment_in=payment_in,
        is_admin=is_admin,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get payment details by ID",
    description="Retrieve payment transaction record details.",
)
async def get_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    is_admin = current_user.role == UserRole.ADMIN
    service = PaymentService(db)
    return await service.get_payment_by_id(
        payment_id=payment_id, current_user_id=current_user.id, is_admin=is_admin
    )
