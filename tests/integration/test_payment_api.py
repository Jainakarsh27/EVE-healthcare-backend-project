from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_payment_simulation_success(
    client: AsyncClient, user_headers: dict, sample_centre, sample_offering
):
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
    booking_id = booking_res.json()["id"]

    # 2. Trigger mock payment success
    payment_res = await client.post(
        "/api/v1/payments",
        json={"booking_id": booking_id, "payment_method": "MOCK_SUCCESS"},
        headers=user_headers,
    )
    assert payment_res.status_code == 201
    pay_data = payment_res.json()
    assert pay_data["status"] == "SUCCESS"
    assert pay_data["amount"] == "850.00"

    # 3. Verify booking is now CONFIRMED
    b_res = await client.get(f"/api/v1/bookings/{booking_id}", headers=user_headers)
    assert b_res.json()["status"] == "CONFIRMED"


@pytest.mark.asyncio
async def test_payment_simulation_failure(
    client: AsyncClient, user_headers: dict, sample_centre, sample_offering
):
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
    booking_id = booking_res.json()["id"]

    # 2. Trigger mock payment failure
    payment_res = await client.post(
        "/api/v1/payments",
        json={"booking_id": booking_id, "payment_method": "MOCK_FAILURE"},
        headers=user_headers,
    )
    assert payment_res.status_code == 201
    pay_data = payment_res.json()
    assert pay_data["status"] == "FAILED"

    # 3. Verify booking is now FAILED
    b_res = await client.get(f"/api/v1/bookings/{booking_id}", headers=user_headers)
    assert b_res.json()["status"] == "FAILED"
