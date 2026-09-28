import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_centre_crud_operations(client: AsyncClient, admin_headers: dict, user_headers: dict):
    # 1. Admin creates centre
    centre_data = {
        "name": "EVE Test Lab",
        "address": "55 Innovation Park",
        "city": "Bangalore",
        "state": "Karnataka",
        "pincode": "560100",
    }
    create_res = await client.post("/api/v1/centres", json=centre_data, headers=admin_headers)
    assert create_res.status_code == 201
    centre_id = create_res.json()["id"]

    # 2. Non-admin creation forbidden
    forbidden_res = await client.post("/api/v1/centres", json=centre_data, headers=user_headers)
    assert forbidden_res.status_code == 403

    # 3. Public list centres
    list_res = await client.get("/api/v1/centres?city=Bangalore")
    assert list_res.status_code == 200
    assert list_res.json()["pagination"]["total"] >= 1

    # 4. Get centre detail
    get_res = await client.get(f"/api/v1/centres/{centre_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "EVE Test Lab"


@pytest.mark.asyncio
async def test_test_and_offering_creation(
    client: AsyncClient, admin_headers: dict, sample_centre
):
    # 1. Admin creates test
    test_data = {
        "name": "Complete Blood Count",
        "code": "CBC_INTEG",
        "category": "HAEMATOLOGY",
        "description": "Full blood analysis",
    }
    test_res = await client.post("/api/v1/tests", json=test_data, headers=admin_headers)
    assert test_res.status_code == 201
    test_id = test_res.json()["id"]

    # 2. Admin links test to centre (Offering)
    offering_data = {
        "test_id": test_id,
        "price": "750.00",
        "duration_minutes": 20,
    }
    offering_res = await client.post(
        f"/api/v1/centres/{sample_centre.id}/tests", json=offering_data, headers=admin_headers
    )
    assert offering_res.status_code == 201
    assert offering_res.json()["price"] == "750.00"

    # 3. List offerings for centre
    list_offerings = await client.get(f"/api/v1/centres/{sample_centre.id}/tests")
    assert list_offerings.status_code == 200
    assert len(list_offerings.json()["items"]) == 1
