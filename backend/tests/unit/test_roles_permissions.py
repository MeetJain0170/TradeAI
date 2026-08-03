"""Unit tests for RBAC roles and permissions."""

from __future__ import annotations

from app.security.permissions import Permission, role_has_permission
from app.security.roles import Role, has_sufficient_role


def test_role_hierarchy_admin_beats_all() -> None:
    """ADMIN outranks every other role."""
    for role in (Role.TRADER, Role.RESEARCHER, Role.USER, Role.READ_ONLY):
        assert has_sufficient_role(Role.ADMIN, role) is True


def test_role_hierarchy_same_role() -> None:
    """Any role meets its own requirement."""
    for role in Role:
        assert has_sufficient_role(role, role) is True


def test_role_hierarchy_ascending() -> None:
    """Lower-privilege roles cannot satisfy higher-privilege requirements."""
    assert has_sufficient_role(Role.READ_ONLY, Role.USER) is False
    assert has_sufficient_role(Role.USER, Role.RESEARCHER) is False
    assert has_sufficient_role(Role.RESEARCHER, Role.TRADER) is False
    assert has_sufficient_role(Role.TRADER, Role.ADMIN) is False


def test_role_hierarchy_descending() -> None:
    """Higher-privilege roles satisfy lower-privilege requirements."""
    assert has_sufficient_role(Role.TRADER, Role.USER) is True
    assert has_sufficient_role(Role.TRADER, Role.READ_ONLY) is True
    assert has_sufficient_role(Role.RESEARCHER, Role.USER) is True


def test_user_role_default_permissions() -> None:
    """USER role can view own profile and read market data."""
    assert role_has_permission(Role.USER, Permission.VIEW_OWN_PROFILE) is True
    assert role_has_permission(Role.USER, Permission.READ_MARKET_DATA) is True
    assert role_has_permission(Role.USER, Permission.EXECUTE_TRADE) is False
    assert role_has_permission(Role.USER, Permission.MANAGE_USERS) is False


def test_admin_has_all_permissions() -> None:
    """ADMIN possesses every defined permission."""
    for perm in Permission:
        assert role_has_permission(Role.ADMIN, perm) is True


def test_trader_cannot_manage_users() -> None:
    """TRADER does not have user-management permissions."""
    assert role_has_permission(Role.TRADER, Permission.MANAGE_USERS) is False
    assert role_has_permission(Role.TRADER, Permission.EXECUTE_TRADE) is True


def test_read_only_cannot_trade() -> None:
    """READ_ONLY role cannot execute trades."""
    assert role_has_permission(Role.READ_ONLY, Permission.EXECUTE_TRADE) is False
    assert role_has_permission(Role.READ_ONLY, Permission.READ_MARKET_DATA) is True
