
from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.schemas.webhook import WebhookPayload, WebhookResponse
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/payments/webhook", tags=["Webhooks"])


@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Payment provider webhook callback",
    description=(
        "Idempotent webhook endpoint for payment status updates. Verifies `X-Webhook-Signature` HMAC header and ensures event processing uniqueness."
    ),
)
async def handle_payment_webhook(
    request: Request,
    payload: WebhookPayload,
    signature: str | None = Header(None, alias="X-Webhook-Signature"),
    db: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()
    service = WebhookService(db)
    return await service.process_payment_webhook(
        raw_body=raw_body,
        signature=signature,
        payload=payload,
    )
