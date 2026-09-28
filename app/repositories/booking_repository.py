import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.booking import Booking
from app.models.booking_status_history import BookingStatusHistory
from app.utils.enums import BookingStatus


class BookingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, booking_id: uuid.UUID) -> Booking | None:
        stmt = (
            select(Booking)
            .options(
                selectinload(Booking.user),
                selectinload(Booking.centre),
                selectinload(Booking.test),
                selectinload(Booking.offering),
                selectinload(Booking.status_history),
            )
            .where(Booking.id == booking_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_lock(self, booking_id: uuid.UUID) -> Booking | None:
        """Fetch booking with pessimistic lock (FOR UPDATE)."""
        stmt = (
            select(Booking)
            .options(
                selectinload(Booking.user),
                selectinload(Booking.centre),
                selectinload(Booking.test),
                selectinload(Booking.offering),
                selectinload(Booking.status_history),
            )
            .where(Booking.id == booking_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(
        self, user_id: uuid.UUID, idempotency_key: str
    ) -> Booking | None:
        stmt = (
            select(Booking)
            .options(
                selectinload(Booking.user),
                selectinload(Booking.centre),
                selectinload(Booking.test),
                selectinload(Booking.offering),
                selectinload(Booking.status_history),
            )
            .where(
                Booking.user_id == user_id,
                Booking.idempotency_key == idempotency_key,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def check_conflicting_booking(
        self, centre_id: uuid.UUID, offering_id: uuid.UUID, appointment_at: datetime
    ) -> Booking | None:
        """Check if an active booking already exists for the same slot."""
        stmt = select(Booking).where(
            Booking.centre_id == centre_id,
            Booking.offering_id == offering_id,
            Booking.appointment_at == appointment_at,
            Booking.status.notin_([BookingStatus.FAILED, BookingStatus.CANCELLED]),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, booking: Booking) -> Booking:
        self.session.add(booking)
        await self.session.flush()
        return booking

    async def update(self, booking: Booking) -> Booking:
        await self.session.flush()
        return booking

    async def add_status_history(self, history: BookingStatusHistory) -> BookingStatusHistory:
        self.session.add(history)
        await self.session.flush()
        return history

    async def list_bookings(
        self,
        user_id: uuid.UUID | None = None,
        status: BookingStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Booking], int]:
        stmt = (
            select(Booking)
            .options(
                selectinload(Booking.centre),
                selectinload(Booking.test),
                selectinload(Booking.user),
            )
        )
        if user_id:
            stmt = stmt.where(Booking.user_id == user_id)
        if status:
            stmt = stmt.where(Booking.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = stmt.offset(offset).limit(limit).order_by(Booking.created_at.desc())
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total
