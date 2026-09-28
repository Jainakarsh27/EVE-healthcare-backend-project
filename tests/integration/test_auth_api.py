import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_user_signup_success(client: AsyncClient):
    payload = {
        "email": "newuser@example.com",
        "password": "StrongPassword123!",
        "full_name": "New User",
        "phone": "+919876543210",
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_user_signup_duplicate_email(client: AsyncClient):
    payload = {
        "email": "duplicate@example.com",
        "password": "StrongPassword123!",
        "full_name": "User One",
    }
    res1 = await client.post("/api/v1/auth/signup", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/signup", json=payload)
    assert res2.status_code == 409
    err = res2.json()["error"]
    assert err["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_user_login_success(client: AsyncClient):
    signup_payload = {
        "email": "loginuser@example.com",
        "password": "CorrectPassword123!",
        "full_name": "Login User",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)

    login_payload = {
        "email": "loginuser@example.com",
        "password": "CorrectPassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "loginuser@example.com"


@pytest.mark.asyncio
async def test_user_login_wrong_password(client: AsyncClient):
    signup_payload = {
        "email": "testwrongpass@example.com",
        "password": "CorrectPassword123!",
        "full_name": "Test User",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)

    login_payload = {
        "email": "testwrongpass@example.com",
        "password": "WrongPassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    err = response.json()["error"]
    assert err["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_get_me_protected_route(client: AsyncClient, user_headers: dict):
    response = await client.get("/api/v1/auth/me", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@test.com"
