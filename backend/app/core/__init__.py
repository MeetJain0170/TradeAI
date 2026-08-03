"""Application core — cross-cutting infrastructure.

Exports the public API surface of ``app.core`` so that importers can
use short import paths::

    from app.core.exceptions import ValidationError
    from app.core.responses import ErrorResponse
    from app.core.request_context import get_request_id
"""
