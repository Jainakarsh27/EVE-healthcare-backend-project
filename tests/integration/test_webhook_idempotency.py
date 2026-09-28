import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.security import generate_webhook_signature
from app.models.payment import Payment
from app.utils.enums import PaymentStatus


@pytest.mark.asyncio
async def test_critical_webhook_idempotency_flow(
    client: AsyncClient, user_headers: dict, db_session, sample_centre, sample_offering
):
    """
    CRITICAL REQUIREMENT TEST (#43):
    Send webhook event #1 -> payment SUCCESS, booking CONFIRMED
    Send exact same webhook event #2 -> no duplicate payment, booking remains CONFIRMED
    Send exact same webhook event 10 times -> database remains consistent
    """
    # 1. Create booking
    appointment_time = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    booking_res = await client.post(
        "/api/v1/bookings",
        json={
            "centre_id": str(sample_centre.id),
            "offering_id": str(sample_offering.id),
            "appointment_at": appointment_time,
        },
        headers=user_headers,
    )
    booking_id_str = booking_res.json()["id"]
    booking_id = uuid.UUID(booking_id_str)

    # 2. Create pending payment record
    provider_pay_id = "pay_webhook_idempotency_123"
    payment = Payment(
        booking_id=booking_id,
        provider_payment_id=provider_pay_id,
        amount=Decimal("850.00"),
        currency="INR",
        status=PaymentStatus.PENDING,
        payment_method="MOCK_GATEWAY",
    )
    db_session.add(payment)
    await db_session.commit()

    # Webhook event payload
    event_payload = {
        "event_id": "evt_critical_test_001",
        "event_type": "payment.updated",
        "provider_payment_id": provider_pay_id,
        "status": "SUCCESS",
        "amount": "850.00",
        "currency": "INR",
    }
    raw_payload_bytes = json.dumps(event_payload).encode("utf-8")
    valid_signature = generate_webhook_signature(raw_payload_bytes, settings.WEBHOOK_SECRET)

    webhook_headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": valid_signature,
    }

    # --- Event #1: First delivery ---
    res1 = await client.post(
        "/api/v1/payments/webhook", content=raw_payload_bytes, headers=webhook_headers
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "processed"
    assert data1["event_id"] == "evt_critical_test_001"

    # Verify Booking is CONFIRMED
    booking_check = await client.get(f"/api/v1/bookings/{booking_id}", headers=user_headers)
    assert booking_check.json()["status"] == "CONFIRMED"

    # --- Event #2: Second delivery (Duplicate) ---
    res2 = await client.post(
        "/api/v1/payments/webhook", content=raw_payload_bytes, headers=webhook_headers
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "already_processed"
    assert data2["event_id"] == "evt_critical_test_001"

    # --- Events #3 to #10: Repeated 8 more times ---
    for _i in range(3, 11):
        res_i = await client.post(
            "/api/v1/payments/webhook", content=raw_payload_bytes, headers=webhook_headers
        )
        assert res_i.status_code == 200
        assert res_i.json()["status"] == "already_processed"

    # Verify booking status REMAINS CONFIRMED and consistent
    booking_check_final = await client.get(f"/api/v1/bookings/{booking_id}", headers=user_headers)
    assert booking_check_final.json()["status"] == "CONFIRMED"


@pytest.mark.asyncio
async def test_invalid_webhook_signature_rejection(client: AsyncClient):
    event_payload = {
        "event_id": "evt_invalid_sig_001",
        "event_type": "payment.updated",
        "provider_payment_id": "pay_999",
        "status": "SUCCESS",
        "amount": "850.00",
        "currency": "INR",
    }
    invalid_headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": "invalid_hmac_signature_value",
    }

    res = await client.post(
        "/api/v1/payments/webhook", json=event_payload, headers=invalid_headers
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_WEBHOOK_SIGNATURE"


@pytest.mark.asyncio
async def test_invalid_webhook_amount_mismatch_rejection(
    client: AsyncClient, user_headers: dict, db_session, sample_centre, sample_offering
):
    # Create booking for 850 INR
    appointment_time = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    booking_res = await client.post(
        "/api/v1/bookings",
        json={
            "centre_id": str(sample_centre.id),
            "offering_id": str(sample_offering.id),
            "appointment_at": appointment_time,
        },
        headers=user_headers,
    )
    booking_id_str = booking_res.json()["id"]
    booking_id = uuid.UUID(booking_id_str)

    provider_pay_id = "pay_amount_mismatch_123"
    payment = Payment(
        booking_id=booking_id,
        provider_payment_id=provider_pay_id,
        amount=Decimal("850.00"),
        currency="INR",
        status=PaymentStatus.PENDING,
        payment_method="MOCK_GATEWAY",
    )
    db_session.add(payment)
    await db_session.commit()

    # Webhook tries to confirm payment with amount = 1.00 INR (Fraud attempt)
    tampered_payload = {
        "event_id": "evt_tampered_001",
        "event_type": "payment.updated",
        "provider_payment_id": provider_pay_id,
        "status": "SUCCESS",
        "amount": "1.00",  # MISMATCH!
        "currency": "INR",
    }
    raw_payload_bytes = json.dumps(tampered_payload).encode("utf-8")
    sig = generate_webhook_signature(raw_payload_bytes, settings.WEBHOOK_SECRET)
    headers = {"Content-Type": "application/json", "X-Webhook-Signature": sig}

    res = await client.post("/api/v1/payments/webhook", content=raw_payload_bytes, headers=headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_WEBHOOK_AMOUNT"

    # Verify booking was NOT confirmed and remains PENDING
    b_check = await client.get(f"/api/v1/bookings/{booking_id}", headers=user_headers)
    assert b_check.json()["status"] == "PENDING"
