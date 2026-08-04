"""Pydantic schemas for Stock domain models."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StockBase(BaseModel):
    """Base fields shared across Stock schemas."""

    symbol: str = Field(
        description="Canonical symbol identifier (e.g. AAPL, RELIANCE.NS)."
    )
    name: str | None = Field(default=None, description="Company or asset name.")
    exchange: str | None = Field(
        default=None, description="Exchange name (e.g. NASDAQ, NSE)."
    )
    currency: str | None = Field(
        default=None, description="Trading currency (e.g. USD, INR)."
    )
    sector: str | None = Field(default=None, description="Market sector.")
    industry: str | None = Field(default=None, description="Market industry.")


class StockCreate(StockBase):
    """Schema for creating a new Stock entry."""

    pass


class StockResponse(StockBase):
    """Schema for Stock response payloads."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Unique stock UUID.")
    created_at: datetime = Field(description="Creation UTC timestamp.")
    updated_at: datetime = Field(description="Last update UTC timestamp.")
    deleted_at: datetime | None = Field(
        default=None, description="Soft delete UTC timestamp."
    )
