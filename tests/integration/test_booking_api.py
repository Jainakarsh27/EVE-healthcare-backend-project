from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.utils.enums import UserRole


@pytest.mark.asyncio
async def test_booking_creation_and_price_snapshot(
    client: AsyncClient, user_headers: dict, sample_centre, sample_offering
):
    appointment_time = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    booking_payload = {
        "centre_id": str(sample_centre.id),
        "offering_id": str(sample_offering.id),
        "appointment_at": appointment_time,
    }

    headers = {**user_headers, "Idempotency-Key": "test-key-12345"}
    res = await client.post("/api/v1/bookings", json=booking_payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["amount"] == "850.00"  # Price snapshot from sample_offering
    assert data["status"] == "PENDING"
    assert data["booking_reference"].startswith("EVE-")
    assert data["idempotency_key"] == "test-key-12345"

    booking_id = data["id"]

    # Test Idempotent call with same key -> Returns existing booking without duplicate
    res_duplicate = await client.post("/api/v1/bookings", json=booking_payload, headers=headers)
    assert res_duplicate.status_code == 201
    assert res_duplicate.json()["id"] == booking_id


@pytest.mark.asyncio
async def test_unauthorized_user_booking_access(
    client: AsyncClient, user_headers: dict, db_session, sample_centre, sample_offering
):
    # Create booking for user 1
    appointment_time = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    booking_payload = {
        "centre_id": str(sample_centre.id),
        "offering_id": str(sample_offering.id),
        "appointment_at": appointment_time,
    }
    create_res = await client.post("/api/v1/bookings", json=booking_payload, headers=user_headers)
    booking_id = create_res.json()["id"]

    # Create User 2 and headers
    user2 = User(
        email="otheruser@test.com",
        password_hash=hash_password("Pass123!"),
        full_name="Other User",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user2)
    await db_session.commit()
    token2 = create_access_token(str(user2.id), user2.role.value, user2.email)
    user2_headers = {"Authorization": f"Bearer {token2}"}

    # User 2 attempts to get User 1's booking -> 403 Forbidden
    get_res = await client.get(f"/api/v1/bookings/{booking_id}", headers=user2_headers)
    assert get_res.status_code == 403
    assert get_res.json()["error"]["code"] == "FORBIDDEN_BOOKING_ACCESS"
