"""Integration tests for UserRepository and BaseRepository."""

from __future__ import annotations

import pytest
from app.infrastructure.database.models.user import User
from app.infrastructure.database.repositories.user_repository import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_user_repository_create_and_get(db_session: AsyncSession) -> None:
    """Test user creation and retrieval by ID and by email."""
    repo = UserRepository(db_session)
    user_instance = User(
        email="test_user@example.com",
        hashed_password="hashed_securepassword123",
        full_name="Test User",
    )

    created_user = await repo.create(user_instance)
    assert created_user.id is not None
    assert created_user.email == "test_user@example.com"
    assert created_user.hashed_password == "hashed_securepassword123"
    assert created_user.is_active is True
    assert created_user.deleted_at is None

    fetched = await repo.get_by_id(created_user.id)
    assert fetched is not None
    assert fetched.email == "test_user@example.com"

    by_email = await repo.get_by_email("test_user@example.com")
    assert by_email is not None
    assert by_email.id == created_user.id

    exists = await repo.email_exists("test_user@example.com")
    assert exists is True


@pytest.mark.asyncio
async def test_user_repository_update_entity(db_session: AsyncSession) -> None:
    """Test entity-based update pattern on UserRepository."""
    repo = UserRepository(db_session)
    user_instance = User(
        email="update_me@example.com",
        hashed_password="hashed_pass",
        full_name="Original Name",
    )

    user = await repo.create(user_instance)
    user.full_name = "Updated Name"

    updated_user = await repo.update(user)
    assert updated_user.full_name == "Updated Name"

    refetched = await repo.get_by_id(user.id)
    assert refetched is not None
    assert refetched.full_name == "Updated Name"


@pytest.mark.asyncio
async def test_user_repository_soft_delete_and_list(db_session: AsyncSession) -> None:
    """Test soft delete functionality and filtering in lists."""
    repo = UserRepository(db_session)
    user_instance = User(
        email="soft_delete@example.com",
        hashed_password="hashed_pass",
    )

    user = await repo.create(user_instance)
    assert await repo.get_by_id(user.id) is not None

    # Soft delete
    deleted = await repo.soft_delete(user.id)
    assert deleted is True

    # Standard get should return None
    assert await repo.get_by_id(user.id) is None
    assert await repo.get_by_email("soft_delete@example.com") is None

    # Get with include_deleted=True should return the entity
    deleted_user = await repo.get_by_id(user.id, include_deleted=True)
    assert deleted_user is not None
    assert deleted_user.deleted_at is not None


@pytest.mark.asyncio
async def test_user_repository_pagination(db_session: AsyncSession) -> None:
    """Test pagination over multiple users."""
    repo = UserRepository(db_session)

    for i in range(5):
        await repo.create(
            User(
                email=f"page_user_{i}@example.com",
                hashed_password="hashed",
            )
        )

    items, total, pages = await repo.paginate(page=1, page_size=2)
    assert len(items) == 2
    assert total >= 5
    assert pages >= 3
