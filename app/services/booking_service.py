import random
import string
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    InvalidStateTransitionError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import logger
from app.models.booking import Booking
from app.models.booking_status_history import BookingStatusHistory
from app.repositories.booking_repository import BookingRepository
from app.repositories.centre_repository import CentreRepository
from app.repositories.offering_repository import OfferingRepository
from app.repositories.test_repository import TestRepository
from app.repositories.user_repository import UserRepository
from app.schemas.booking import BookingCreate, BookingResponse
from app.utils.enums import BookingStatus
from app.utils.pagination import PaginatedResponse, PaginationParams


def generate_booking_reference() -> str:
    """Generate human readable reference: EVE-YYYYMMDD-XXXXXX."""
    date_str = datetime.now(UTC).strftime("%Y%m%d")
    random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"EVE-{date_str}-{random_str}"


class BookingService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.booking_repo = BookingRepository(session)
        self.centre_repo = CentreRepository(session)
        self.test_repo = TestRepository(session)
        self.offering_repo = OfferingRepository(session)
        self.user_repo = UserRepository(session)

    async def create_booking(
        self,
        user_id: uuid.UUID,
        booking_in: BookingCreate,
        idempotency_key: str | None = None,
    ) -> BookingResponse:
        # 1. Idempotency Check: return existing booking if matching (user_id, idempotency_key)
        if idempotency_key:
            existing_booking = await self.booking_repo.get_by_idempotency_key(
                user_id=user_id, idempotency_key=idempotency_key
            )
            if existing_booking:
                return BookingResponse.model_validate(existing_booking)

        # 2. Validate User exists & active
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise NotFoundError(message="User not found or inactive", code="USER_NOT_FOUND")

        # 3. Validate Centre
        centre = await self.centre_repo.get_by_id(booking_in.centre_id)
        if not centre:
            raise NotFoundError(message="Diagnostic centre not found", code="CENTRE_NOT_FOUND")
        if not centre.is_active:
            raise ValidationError(
                message="Diagnostic centre is currently inactive", code="CENTRE_INACTIVE"
            )

        # 4. Lock offering & validate
        offering = await self.offering_repo.get_by_id_with_lock(booking_in.offering_id)
        if not offering or offering.centre_id != booking_in.centre_id:
            raise NotFoundError(
                message="Test offering not found at specified centre", code="OFFERING_NOT_FOUND"
            )
        if not offering.is_available:
            raise ValidationError(
                message="This test offering is currently unavailable", code="OFFERING_UNAVAILABLE"
            )

        # 5. Validate Test
        test = await self.test_repo.get_by_id(offering.test_id)
        if not test or not test.is_active:
            raise ValidationError(
                message="Selected diagnostic test is inactive", code="TEST_INACTIVE"
            )

        # 6. Concurrency & Double-Booking Check
        conflicting_booking = await self.booking_repo.check_conflicting_booking(
            centre_id=booking_in.centre_id,
            offering_id=booking_in.offering_id,
            appointment_at=booking_in.appointment_at,
        )
        if conflicting_booking:
            raise ConflictError(
                message="This appointment slot is already booked. Please choose another time.",
                code="SLOT_ALREADY_BOOKED",
            )

        # 7. Price Snapshot from server offering price
        price_snapshot = offering.price

        # 8. Create Booking record
        booking_id = uuid.uuid4()
        booking_ref = generate_booking_reference()
        booking = Booking(
            id=booking_id,
            booking_reference=booking_ref,
            user_id=user_id,
            centre_id=booking_in.centre_id,
            test_id=offering.test_id,
            offering_id=booking_in.offering_id,
            appointment_at=booking_in.appointment_at,
            amount=price_snapshot,
            currency="INR",
            status=BookingStatus.PENDING,
            idempotency_key=idempotency_key,
        )

        try:
            self.session.add(booking)
            history = BookingStatusHistory(
                booking_id=booking_id,
                previous_status=None,
                new_status=BookingStatus.PENDING.value,
                reason="Booking initialized in PENDING state",
                changed_by=user_id,
            )
            self.session.add(history)
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"IntegrityError in create_booking: {str(e)}")
            if idempotency_key:
                existing = await self.booking_repo.get_by_idempotency_key(user_id, idempotency_key)
                if existing:
                    return BookingResponse.model_validate(existing)
            raise ConflictError(
                message=f"This appointment slot is already booked or concurrent conflict occurred: {str(e)}",
                code="SLOT_ALREADY_BOOKED",
            ) from e

        fetched = await self.booking_repo.get_by_id(booking_id)
        return BookingResponse.model_validate(fetched)

    async def get_booking(
        self, booking_id: uuid.UUID, current_user_id: uuid.UUID, is_admin: bool = False
    ) -> BookingResponse:
        booking = await self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise NotFoundError(message="Booking not found", code="BOOKING_NOT_FOUND")

        # Authorization check: user can only view their own booking unless admin
        if not is_admin and booking.user_id != current_user_id:
            raise ForbiddenError(
                message="You are not authorized to view this booking", code="FORBIDDEN_BOOKING_ACCESS"
            )

        return BookingResponse.model_validate(booking)

    async def cancel_booking(
        self,
        booking_id: uuid.UUID,
        current_user_id: uuid.UUID,
        is_admin: bool = False,
        reason: str | None = "Cancelled by user",
    ) -> BookingResponse:
        booking = await self.booking_repo.get_by_id_with_lock(booking_id)
        if not booking:
            raise NotFoundError(message="Booking not found", code="BOOKING_NOT_FOUND")

        if not is_admin and booking.user_id != current_user_id:
            raise ForbiddenError(
                message="You are not authorized to cancel this booking", code="FORBIDDEN_BOOKING_ACCESS"
            )

        # State machine transition rules:
        # PENDING -> CANCELLED (OK)
        # CONFIRMED -> CANCELLED (OK)
        # CANCELLED -> CANCELLED (Error)
        # FAILED -> CANCELLED (Error)
        if booking.status == BookingStatus.CANCELLED:
            raise InvalidStateTransitionError(
                message="Booking is already cancelled", code="BOOKING_ALREADY_CANCELLED"
            )
        if booking.status == BookingStatus.FAILED:
            raise InvalidStateTransitionError(
                message="Cannot cancel a failed booking", code="INVALID_BOOKING_STATE"
            )

        old_status = booking.status.value
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.now(UTC)

        history = BookingStatusHistory(
            booking_id=booking.id,
            previous_status=old_status,
            new_status=BookingStatus.CANCELLED.value,
            reason=reason,
            changed_by=current_user_id,
        )
        await self.booking_repo.add_status_history(history)
        await self.booking_repo.update(booking)
        await self.session.commit()

        refetched = await self.booking_repo.get_by_id(booking.id)
        return BookingResponse.model_validate(refetched)

    async def list_bookings(
        self,
        current_user_id: uuid.UUID,
        is_admin: bool = False,
        status: BookingStatus | None = None,
        params: PaginationParams | None = None,
    ) -> PaginatedResponse[BookingResponse]:
        params = params or PaginationParams()
        # If normal user, filter by user_id. If admin, show all bookings or filter by target user
        filter_user_id = None if is_admin else current_user_id

        items, total = await self.booking_repo.list_bookings(
            user_id=filter_user_id,
            status=status,
            offset=params.offset,
            limit=params.page_size,
        )
        responses = [BookingResponse.model_validate(b) for b in items]
        return PaginatedResponse.create(responses, total, params)
