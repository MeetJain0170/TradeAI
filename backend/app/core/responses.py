"""Standard API response models for TradeAI.

Every API endpoint must return one of the shapes defined here so that
clients always receive a predictable, consistent envelope regardless
of which endpoint they call.

Error shape
-----------
::

    {
        "success": false,
        "error": {
            "code": "validation_error",
            "message": "Stock symbol is required.",
            "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
        }
    }

Success shape
-------------
::

    {
        "success": true,
        "data": { ... }
    }

Note: ``SuccessResponse`` is generic and typed per endpoint; this
avoids losing type information while still enforcing the envelope.
"""

from __future__ import annotations

from typing import Literal, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ErrorDetail(BaseModel):
    """Structured error information embedded inside ``ErrorResponse``.

    Attributes
    ----------
    code:
        Machine-readable snake_case identifier (matches the ``code``
        field on ``TradeAIError`` subclasses).
    message:
        Human-readable description of what went wrong.  Must not
        contain secrets, passwords, or stack traces.
    request_id:
        The UUID assigned to the request by ``RequestIDMiddleware``.
        Enables log correlation without exposing sensitive context.
    """

    code: str = Field(
        description="Machine-readable error code.",
        json_schema_extra={"example": "validation_error"},
    )
    message: str = Field(
        description="Human-readable error description.",
        json_schema_extra={"example": "Stock symbol is required."},
    )
    request_id: str = Field(
        description="Request identifier for log correlation.",
        json_schema_extra={"example": "3fa85f64-5717-4562-b3fc-2c963f66afa6"},
    )


class ErrorResponse(BaseModel):
    """Standardised error envelope returned for all API errors.

    This is the *only* shape clients should expect on non-2xx responses.
    The ``success`` discriminator allows clients to branch on a single
    field without inspecting the HTTP status code.
    """

    success: Literal[False] = Field(
        default=False,
        description="Always ``false`` for error responses.",
    )
    error: ErrorDetail = Field(description="Structured error details.")

    @classmethod
    def from_exception(
        cls,
        *,
        code: str,
        message: str,
        request_id: str,
    ) -> ErrorResponse:
        """Convenience factory used by exception handlers.

        Parameters
        ----------
        code:
            Machine-readable error identifier.
        message:
            Human-readable error description.
        request_id:
            Request correlation ID from the middleware context.
        """
        return cls(
            error=ErrorDetail(
                code=code,
                message=message,
                request_id=request_id,
            )
        )


class SuccessResponse[DataT](BaseModel):
    """Generic success envelope for API responses.

    Usage
    -----
    ::

        @router.get("/stocks/{symbol}", response_model=SuccessResponse[StockResponse])
        async def get_stock(symbol: str) -> SuccessResponse[StockResponse]:
            data = await stock_service.get(symbol)
            return SuccessResponse(data=data)

    Attributes
    ----------
    success:
        Always ``True`` for success responses.
    data:
        The actual response payload, typed by the ``DataT`` type
        parameter so OpenAPI schema generation remains accurate.
    """

    success: Literal[True] = Field(
        default=True,
        description="Always ``true`` for success responses.",
    )
    data: DataT = Field(description="Response payload.")
