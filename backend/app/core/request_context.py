"""Request-scoped context storage.

Stores the current request's unique identifier in a ``ContextVar`` so
that it is accessible from any code running within the same async task
chain — including logging formatters — without being threaded through
every function signature.

Usage
-----
From middleware::

    token = set_request_id("3fa85f64-5717-4562-b3fc-2c963f66afa6")
    try:
        ...
    finally:
        _request_id_ctx.reset(token)

From anywhere else (e.g., a log formatter)::

    request_id = get_request_id()  # returns "unknown" if not set
"""

from __future__ import annotations

from contextvars import ContextVar, Token

# Module-level ContextVar.  The default value is the string ``"unknown"``
# so that log lines emitted outside a request context are still valid JSON.
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="unknown")


def get_request_id() -> str:
    """Return the request ID for the current async context.

    Returns ``"unknown"`` when called outside of an active request
    (e.g., during startup tasks or background jobs that have not yet
    set a request ID).
    """
    return _request_id_ctx.get()


def set_request_id(request_id: str) -> Token[str]:
    """Set the request ID for the current async context.

    Parameters
    ----------
    request_id:
        The UUID (or any opaque string) that uniquely identifies the
        in-flight request.

    Returns
    -------
    Token[str]
        An opaque token that must be passed to ``_request_id_ctx.reset()``
        when the request is complete, in order to restore the previous
        value and prevent context leakage between requests.
    """
    return _request_id_ctx.set(request_id)
