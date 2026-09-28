from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_event import WebhookEvent


class WebhookRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_event_id(self, event_id: str) -> WebhookEvent | None:
        stmt = select(WebhookEvent).where(WebhookEvent.event_id == event_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_event_id_with_lock(self, event_id: str) -> WebhookEvent | None:
        stmt = select(WebhookEvent).where(WebhookEvent.event_id == event_id).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, event: WebhookEvent) -> WebhookEvent:
        self.session.add(event)
        await self.session.flush()
        return event

    async def update(self, event: WebhookEvent) -> WebhookEvent:
        await self.session.flush()
        return event
