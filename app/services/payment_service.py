import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ForbiddenError,
    InvalidStateTransitionError,
    NotFoundError,
)
from app.models.booking_status_history import BookingStatusHistory
from app.models.payment import Payment
from app.repositories.booking_repository import BookingRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.utils.enums import BookingStatus, PaymentMethod, PaymentStatus


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.booking_repo = BookingRepository(session)

    async def create_payment_simulation(
        self,
        current_user_id: uuid.UUID,
        payment_in: PaymentCreate,
        is_admin: bool = False,
    ) -> PaymentResponse:
        # 1. Fetch booking with FOR UPDATE lock
        booking = await self.booking_repo.get_by_id_with_lock(payment_in.booking_id)
        if not booking:
            raise NotFoundError(message="Booking not found", code="BOOKING_NOT_FOUND")

        # 2. Authorization check
        if not is_admin and booking.user_id != current_user_id:
            raise ForbiddenError(
                message="You are not authorized to pay for this booking",
                code="FORBIDDEN_PAYMENT_ACCESS",
            )

        # 3. State validation: booking must be PENDING
        if booking.status != BookingStatus.PENDING:
            if booking.status == BookingStatus.CONFIRMED:
                raise InvalidStateTransitionError(
                    message="Booking has already been confirmed", code="BOOKING_ALREADY_CONFIRMED"
                )
            elif booking.status == BookingStatus.CANCELLED:
                raise InvalidStateTransitionError(
                    message="Cannot pay for a cancelled booking", code="BOOKING_ALREADY_CANCELLED"
                )
            else:
                raise InvalidStateTransitionError(
                    message=f"Booking is in invalid state '{booking.status.value}' for payment",
                    code="INVALID_BOOKING_STATE",
                )

        # 4. Check for existing payment
        existing_payment = await self.payment_repo.get_by_booking_id(booking.id)
        if existing_payment and existing_payment.status == PaymentStatus.SUCCESS:
            return PaymentResponse.model_validate(existing_payment)

        # 5. Simulate payment outcome deterministically
        provider_payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        is_success = payment_in.payment_method != PaymentMethod.MOCK_FAILURE
        simulated_payment_status = (
            PaymentStatus.SUCCESS if is_success else PaymentStatus.FAILED
        )

        payment = Payment(
            booking_id=booking.id,
            provider_payment_id=provider_payment_id,
            amount=booking.amount,
            currency=booking.currency,
            status=simulated_payment_status,
            payment_method=payment_in.payment_method.value,
            failure_reason=None if is_success else "Simulated payment rejection",
        )
        created_payment = await self.payment_repo.create(payment)

        # 6. Update booking status transactionally
        old_status = booking.status.value
        if is_success:
            booking.status = BookingStatus.CONFIRMED
            new_status = BookingStatus.CONFIRMED.value
            reason = f"Payment {provider_payment_id} succeeded"
        else:
            booking.status = BookingStatus.FAILED
            new_status = BookingStatus.FAILED.value
            reason = f"Payment {provider_payment_id} failed"

        history = BookingStatusHistory(
            booking_id=booking.id,
            previous_status=old_status,
            new_status=new_status,
            reason=reason,
            changed_by=current_user_id,
        )
        await self.booking_repo.add_status_history(history)
        await self.booking_repo.update(booking)

        await self.session.commit()
        return PaymentResponse.model_validate(created_payment)

    async def get_payment_by_id(
        self, payment_id: uuid.UUID, current_user_id: uuid.UUID, is_admin: bool = False
    ) -> PaymentResponse:
        payment = await self.payment_repo.get_by_id(payment_id)
        if not payment:
            raise NotFoundError(message="Payment record not found", code="PAYMENT_NOT_FOUND")

        if not is_admin and payment.booking.user_id != current_user_id:
            raise ForbiddenError(
                message="You are not authorized to view this payment", code="FORBIDDEN_PAYMENT_ACCESS"
            )

        return PaymentResponse.model_validate(payment)
