from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    InvalidWebhookAmountError,
    InvalidWebhookSignatureError,
    NotFoundError,
)
from app.core.security import verify_webhook_signature
from app.models.booking_status_history import BookingStatusHistory
from app.models.webhook_event import WebhookEvent
from app.repositories.booking_repository import BookingRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.webhook_repository import WebhookRepository
from app.schemas.webhook import WebhookPayload, WebhookResponse
from app.utils.enums import BookingStatus, PaymentStatus, WebhookProcessingStatus


class WebhookService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.webhook_repo = WebhookRepository(session)
        self.payment_repo = PaymentRepository(session)
        self.booking_repo = BookingRepository(session)

    async def process_payment_webhook(
        self,
        raw_body: bytes,
        signature: str | None,
        payload: WebhookPayload,
    ) -> WebhookResponse:
        # 1. Verify HMAC SHA256 Signature
        if not signature or not verify_webhook_signature(
            raw_body, signature, settings.WEBHOOK_SECRET
        ):
            raise InvalidWebhookSignatureError(
                message="Invalid or missing X-Webhook-Signature header",
                code="INVALID_WEBHOOK_SIGNATURE",
            )

        # 2. Check Idempotency by Event ID in DB
        existing_event = await self.webhook_repo.get_by_event_id(payload.event_id)
        if existing_event:
            if existing_event.processing_status == WebhookProcessingStatus.PROCESSED:
                return WebhookResponse(
                    status="already_processed",
                    event_id=payload.event_id,
                    message="Webhook event was previously processed",
                    details={"processed_at": str(existing_event.processed_at)},
                )

        # 3. Create Webhook Event record inside transaction
        webhook_record = WebhookEvent(
            event_id=payload.event_id,
            event_type=payload.event_type,
            provider="mock_gateway",
            payload=payload.model_dump(mode="json"),
            processing_status=WebhookProcessingStatus.PENDING,
        )

        try:
            await self.webhook_repo.create(webhook_record)
        except IntegrityError:
            await self.session.rollback()
            # Database constraint caught duplicate event_id concurrently
            return WebhookResponse(
                status="already_processed",
                event_id=payload.event_id,
                message="Duplicate webhook event detected and ignored",
            )

        # 4. Lookup target payment
        payment = await self.payment_repo.get_by_provider_payment_id(payload.provider_payment_id)
        if not payment:
            webhook_record.processing_status = WebhookProcessingStatus.FAILED
            webhook_record.error_message = f"Payment with provider ID '{payload.provider_payment_id}' not found"
            await self.webhook_repo.update(webhook_record)
            await self.session.commit()
            raise NotFoundError(
                message=f"Payment record '{payload.provider_payment_id}' not found",
                code="PAYMENT_NOT_FOUND",
            )

        # 5. Validate Amount and Currency
        if Decimal(str(payload.amount)) != payment.amount:
            webhook_record.processing_status = WebhookProcessingStatus.FAILED
            webhook_record.error_message = (
                f"Amount mismatch: Expected {payment.amount}, got {payload.amount}"
            )
            await self.webhook_repo.update(webhook_record)
            await self.session.commit()
            raise InvalidWebhookAmountError(
                message=f"Webhook amount {payload.amount} does not match payment amount {payment.amount}",
                code="INVALID_WEBHOOK_AMOUNT",
            )

        # 6. Fetch Booking with lock
        booking = await self.booking_repo.get_by_id_with_lock(payment.booking_id)
        if not booking:
            webhook_record.processing_status = WebhookProcessingStatus.FAILED
            webhook_record.error_message = "Associated booking not found"
            await self.webhook_repo.update(webhook_record)
            await self.session.commit()
            raise NotFoundError(message="Associated booking not found", code="BOOKING_NOT_FOUND")

        # 7. Safe State Machine Transition & Out-of-Order protection
        # If payment is already SUCCESS, ignore late FAILED or duplicate events
        if payment.status == PaymentStatus.SUCCESS:
            webhook_record.processing_status = WebhookProcessingStatus.IGNORED
            webhook_record.processed_at = datetime.now(UTC)
            webhook_record.error_message = "Payment is already marked SUCCESS; ignoring state change"
            await self.webhook_repo.update(webhook_record)
            await self.session.commit()
            return WebhookResponse(
                status="already_processed",
                event_id=payload.event_id,
                message="Payment already in final SUCCESS state",
            )

        # Update Payment status
        old_booking_status = booking.status.value
        payment.status = payload.status
        await self.payment_repo.update(payment)

        # Update Booking status
        if payload.status == PaymentStatus.SUCCESS:
            booking.status = BookingStatus.CONFIRMED
            new_booking_status = BookingStatus.CONFIRMED.value
            reason = f"Webhook event {payload.event_id}: Payment SUCCESS"
        else:
            booking.status = BookingStatus.FAILED
            new_booking_status = BookingStatus.FAILED.value
            reason = f"Webhook event {payload.event_id}: Payment FAILED"

        history = BookingStatusHistory(
            booking_id=booking.id,
            previous_status=old_booking_status,
            new_status=new_booking_status,
            reason=reason,
            changed_by=None,
        )
        await self.booking_repo.add_status_history(history)
        await self.booking_repo.update(booking)

        # Mark WebhookEvent PROCESSED
        webhook_record.processing_status = WebhookProcessingStatus.PROCESSED
        webhook_record.processed_at = datetime.now(UTC)
        await self.webhook_repo.update(webhook_record)

        # Commit everything atomically
        await self.session.commit()

        return WebhookResponse(
            status="processed",
            event_id=payload.event_id,
            message="Payment webhook processed successfully",
            details={
                "booking_id": str(booking.id),
                "booking_status": booking.status.value,
                "payment_status": payment.status.value,
            },
        )
