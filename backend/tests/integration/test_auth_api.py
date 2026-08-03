"""Integration tests for Authentication API endpoints."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from app.api.dependencies import get_db
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def async_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient]:
    """Provide an AsyncClient with the database session dependency overridden."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_login_profile_flow(
    async_client: AsyncClient,
) -> None:
    """Test full user registration, login, profile, refresh, and logout flow."""

    # 1. Register
    reg_payload = {
        "email": "NewUser@Example.com",
        "password": "StrongPassword123!",
        "password_confirm": "StrongPassword123!",
        "full_name": "New User",
    }

    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json=reg_payload,
    )

    assert reg_resp.status_code == 201

    reg_data = reg_resp.json()

    assert reg_data["success"] is True
    assert reg_data["data"]["email"] == "newuser@example.com"

    # 2. Login
    login_payload = {
        "email": "newuser@example.com",
        "password": "StrongPassword123!",
    }

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json=login_payload,
    )

    assert login_resp.status_code == 200

    login_data = login_resp.json()

    assert login_data["success"] is True

    access_token = login_data["data"]["access_token"]
    refresh_token = login_data["data"]["refresh_token"]

    # 3. Profile
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    prof_resp = await async_client.get(
        "/api/v1/auth/profile",
        headers=headers,
    )

    assert prof_resp.status_code == 200

    prof_data = prof_resp.json()

    assert prof_data["success"] is True
    assert prof_data["data"]["email"] == "newuser@example.com"

    # 4. Refresh
    ref_payload = {
        "refresh_token": refresh_token,
    }

    ref_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json=ref_payload,
    )

    assert ref_resp.status_code == 200

    ref_data = ref_resp.json()

    assert ref_data["success"] is True

    new_refresh_token = ref_data["data"]["refresh_token"]

    # 5. Logout
    logout_payload = {
        "refresh_token": new_refresh_token,
    }

    logout_resp = await async_client.post(
        "/api/v1/auth/logout",
        json=logout_payload,
    )

    assert logout_resp.status_code == 200
    assert logout_resp.json()["success"] is True


@pytest.mark.asyncio
async def test_register_duplicate_email(
    async_client: AsyncClient,
) -> None:
    """Test duplicate registration returns the standard error envelope."""

    payload = {
        "email": "dup@example.com",
        "password": "StrongPassword123!",
        "password_confirm": "StrongPassword123!",
    }

    resp1 = await async_client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert resp1.status_code == 201

    resp2 = await async_client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert resp2.status_code == 422

    data = resp2.json()

    assert data["success"] is False
    assert "already exists" in data["error"]["message"]


@pytest.mark.asyncio
async def test_register_password_mismatch(
    async_client: AsyncClient,
) -> None:
    """Test registration with password mismatch returns 422."""

    payload = {
        "email": "mismatch@example.com",
        "password": "StrongPassword123!",
        "password_confirm": "Different123!",
    }

    resp = await async_client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert resp.status_code == 422

    data = resp.json()

    assert data["success"] is False
    assert "does not match" in data["error"]["message"]


@pytest.mark.asyncio
async def test_login_invalid_password(
    async_client: AsyncClient,
) -> None:
    """Test login with an incorrect password returns 401."""

    reg_payload = {
        "email": "user1@example.com",
        "password": "StrongPassword123!",
        "password_confirm": "StrongPassword123!",
    }

    await async_client.post(
        "/api/v1/auth/register",
        json=reg_payload,
    )

    login_payload = {
        "email": "user1@example.com",
        "password": "WrongPassword123!",
    }

    resp = await async_client.post(
        "/api/v1/auth/login",
        json=login_payload,
    )

    assert resp.status_code == 401
    assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_profile_unauthorized(
    async_client: AsyncClient,
) -> None:
    """Test profile endpoint without Authorization header returns 401."""

    resp = await async_client.get("/api/v1/auth/profile")

    assert resp.status_code == 401
    assert resp.json()["success"] is False
