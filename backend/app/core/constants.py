"""Application-wide constants.

This module holds values that are truly constant — they do not change
between environments and are not user-configurable.

Separation from configuration
------------------------------
``backend/config/settings.py`` holds **environment-specific** values
that vary between development, staging, and production (e.g., database
URLs, log levels, JWT expiry).

This module holds **application constants** that belong to the business
domain and application layer, not to deployment configuration.  Examples
include fixed string identifiers, version strings, and standard field
lengths.

If a value might ever differ between environments, it belongs in
``Settings``, not here.
"""

from __future__ import annotations

# ------------------------------------------------------------------ #
# Service identity                                                    #
# ------------------------------------------------------------------ #

SERVICE_NAME: str = "tradeai-api"
"""Logical name of this service.  Appears in structured log lines."""

API_VERSION: str = "v1"
"""Current public API version prefix (e.g. ``/api/v1/...``)."""

# ------------------------------------------------------------------ #
# Request / Response                                                  #
# ------------------------------------------------------------------ #

REQUEST_ID_HEADER: str = "X-Request-ID"
"""HTTP header used to propagate request identifiers across service
boundaries.  Clients may supply this header; the middleware assigns a
UUID when it is absent."""

# ------------------------------------------------------------------ #
# Validation limits                                                   #
# ------------------------------------------------------------------ #

JWT_SECRET_MIN_LENGTH: int = 32
"""Minimum number of characters required for ``JWT_SECRET_KEY``."""

# ------------------------------------------------------------------ #
# Error codes                                                         #
# ------------------------------------------------------------------ #
# These constants mirror the ``default_code`` values on exception
# classes in ``app.core.exceptions``.  Import from here when you need
# to reference a code without importing the exception class itself.

ERROR_CODE_INTERNAL: str = "INTERNAL_ERROR"
ERROR_CODE_CONFIGURATION: str = "CONFIGURATION_ERROR"
ERROR_CODE_VALIDATION: str = "VALIDATION_ERROR"
ERROR_CODE_INFRASTRUCTURE: str = "INFRASTRUCTURE_ERROR"
ERROR_CODE_AUTHENTICATION: str = "AUTHENTICATION_ERROR"
