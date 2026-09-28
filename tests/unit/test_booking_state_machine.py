from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import InvalidStateTransitionError
from app.models.booking import Booking
from app.services.booking_service import BookingService
from app.utils.enums import BookingStatus


@pytest.mark.asyncio
async def test_booking_cancellation_state_transitions(db_session, normal_user, sample_centre, sample_test, sample_offering):
    booking_service = BookingService(db_session)

    # 1. Create initial PENDING booking
    booking = Booking(
        booking_reference="EVE-TEST-001",
        user_id=normal_user.id,
        centre_id=sample_centre.id,
        test_id=sample_test.id,
        offering_id=sample_offering.id,
        appointment_at=datetime.now(UTC) + timedelta(days=1),
        amount=Decimal("850.00"),
        currency="INR",
        status=BookingStatus.PENDING,
    )
    db_session.add(booking)
    await db_session.commit()

    # 2. Transition PENDING -> CANCELLED (Valid)
    res = await booking_service.cancel_booking(booking.id, normal_user.id, is_admin=False)
    assert res.status == BookingStatus.CANCELLED

    # 3. Transition CANCELLED -> CANCELLED (Invalid - Should raise Error)
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        await booking_service.cancel_booking(booking.id, normal_user.id, is_admin=False)
    assert "already cancelled" in exc_info.value.message.lower()
