"""Granular permission definitions and Role-to-Permission mappings."""

from __future__ import annotations

from enum import StrEnum

from app.security.roles import Role


class Permission(StrEnum):
    """Granular application permissions."""

    # User & Admin
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOGS = "view_audit_logs"

    # Profile
    VIEW_OWN_PROFILE = "view_own_profile"

    # Market Data
    READ_MARKET_DATA = "read_market_data"

    # Trading & Orders
    EXECUTE_TRADE = "execute_trade"
    CANCEL_ORDER = "cancel_order"
    VIEW_PORTFOLIO = "view_portfolio"

    # Forecasting & AI
    RUN_FORECAST = "run_forecast"
    QUERY_RAG = "query_rag"


# Explicit permission grant per role.  Each entry lists only permissions
# granted at that specific role — it is NOT cumulative (use
# ``role_has_permission`` for queries, which looks up the mapping directly).
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: {
        Permission.MANAGE_USERS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.VIEW_OWN_PROFILE,
        Permission.READ_MARKET_DATA,
        Permission.EXECUTE_TRADE,
        Permission.CANCEL_ORDER,
        Permission.VIEW_PORTFOLIO,
        Permission.RUN_FORECAST,
        Permission.QUERY_RAG,
    },
    Role.TRADER: {
        Permission.VIEW_OWN_PROFILE,
        Permission.READ_MARKET_DATA,
        Permission.EXECUTE_TRADE,
        Permission.CANCEL_ORDER,
        Permission.VIEW_PORTFOLIO,
        Permission.RUN_FORECAST,
        Permission.QUERY_RAG,
    },
    Role.RESEARCHER: {
        Permission.VIEW_OWN_PROFILE,
        Permission.READ_MARKET_DATA,
        Permission.VIEW_PORTFOLIO,
        Permission.RUN_FORECAST,
        Permission.QUERY_RAG,
    },
    Role.USER: {
        Permission.VIEW_OWN_PROFILE,
        Permission.READ_MARKET_DATA,
    },
    Role.READ_ONLY: {
        Permission.READ_MARKET_DATA,
        Permission.VIEW_PORTFOLIO,
    },
}


def role_has_permission(role: Role | str, permission: Permission | str) -> bool:
    """Return True when the given role possesses the requested permission."""
    try:
        r = Role(role) if isinstance(role, str) else role
        p = Permission(permission) if isinstance(permission, str) else permission
    except ValueError:
        return False

    return p in ROLE_PERMISSIONS.get(r, set())
