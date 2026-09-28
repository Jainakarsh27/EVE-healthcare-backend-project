from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import ConflictError
from app.schemas.booking import BookingCreate
from app.services.booking_service import BookingService


@pytest.mark.asyncio
async def test_concurrent_booking_conflict_prevention(
    db_session, normal_user, sample_centre, sample_offering
):
    """
    Verifies double-booking / concurrency slot protection:
    Attempting to book the exact same slot twice results in ConflictError on the second attempt.
    """
    appointment_time = datetime.now(UTC) + timedelta(days=5)
    booking_in = BookingCreate(
        centre_id=sample_centre.id,
        offering_id=sample_offering.id,
        appointment_at=appointment_time,
    )

    service = BookingService(db_session)

    # First booking attempt succeeds
    booking1 = await service.create_booking(
        user_id=normal_user.id,
        booking_in=booking_in,
    )
    assert booking1 is not None
    assert booking1.centre_id == sample_centre.id

    # Second booking attempt for the exact same centre, offering & slot MUST fail with ConflictError
    with pytest.raises(ConflictError) as exc_info:
        await service.create_booking(
            user_id=normal_user.id,
            booking_in=booking_in,
        )

    assert exc_info.value.code == "SLOT_ALREADY_BOOKED"
    assert "already booked" in exc_info.value.message.lower()
