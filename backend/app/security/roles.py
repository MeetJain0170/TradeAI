"""Role definitions and role hierarchy helpers for RBAC."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """User security roles in descending privilege order.

    Hierarchy (highest → lowest):
        ADMIN > TRADER > RESEARCHER > USER > READ_ONLY

    ADMIN:      Full system access — manages users, audit logs, all features.
    TRADER:     Executes trades, manages own portfolio, runs forecasts.
    RESEARCHER: Analyses market data and forecasts; no trade execution.
    USER:       Default role after registration; can read own profile and data.
    READ_ONLY:  External / monitoring integrations; read-only market data.
    """

    ADMIN = "ADMIN"
    TRADER = "TRADER"
    RESEARCHER = "RESEARCHER"
    USER = "USER"
    READ_ONLY = "READ_ONLY"


# Hierarchy ordering: ADMIN has highest privilege, READ_ONLY has lowest.
# The numeric level determines whether one role "outranks" another in
# ``has_sufficient_role``.
ROLE_HIERARCHY: dict[Role, int] = {
    Role.ADMIN: 100,
    Role.TRADER: 50,
    Role.RESEARCHER: 30,
    Role.USER: 20,
    Role.READ_ONLY: 10,
}


def has_sufficient_role(user_role: str | Role, required_role: str | Role) -> bool:
    """Return True when the user's role meets or exceeds the required role level."""
    try:
        u_role = Role(user_role) if isinstance(user_role, str) else user_role
        r_role = (
            Role(required_role) if isinstance(required_role, str) else required_role
        )
    except ValueError:
        return False

    return ROLE_HIERARCHY.get(u_role, 0) >= ROLE_HIERARCHY.get(r_role, 100)
