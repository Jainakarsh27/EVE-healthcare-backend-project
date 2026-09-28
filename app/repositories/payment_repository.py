import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.payment import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        stmt = select(Payment).options(selectinload(Payment.booking)).where(Payment.id == payment_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_provider_payment_id(self, provider_payment_id: str) -> Payment | None:
        stmt = (
            select(Payment)
            .options(selectinload(Payment.booking))
            .where(Payment.provider_payment_id == provider_payment_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_booking_id(self, booking_id: uuid.UUID) -> Payment | None:
        stmt = (
            select(Payment)
            .options(selectinload(Payment.booking))
            .where(Payment.booking_id == booking_id)
            .order_by(Payment.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, payment: Payment) -> Payment:
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def update(self, payment: Payment) -> Payment:
        await self.session.flush()
        return payment
