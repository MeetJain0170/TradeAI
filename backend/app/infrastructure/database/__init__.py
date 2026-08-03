"""Database infrastructure public API.

Import from here rather than from individual sub-modules so that
refactoring internal paths never breaks callers::

    from app.infrastructure.database import Base, get_engine, get_session_factory
"""

from app.infrastructure.database.base import Base
from app.infrastructure.database.engine import (
    dispose_engine,
    get_engine,
    verify_database_connection,
)
from app.infrastructure.database.models import AuditLog, BaseModel, SystemLog, User
from app.infrastructure.database.repositories import BaseRepository, UserRepository
from app.infrastructure.database.session import get_db_session, get_session_factory

__all__ = [
    # Core ORM
    "Base",
    "BaseModel",
    # ORM models
    "AuditLog",
    "SystemLog",
    "User",
    # Engine
    "dispose_engine",
    "get_engine",
    "verify_database_connection",
    # Session
    "get_db_session",
    "get_session_factory",
    # Repositories
    "BaseRepository",
    "UserRepository",
]
