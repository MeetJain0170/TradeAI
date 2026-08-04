"""Synchronous wrapper around the yfinance SDK.

This module is the ONLY place in the application permitted to import yfinance directly.
No business logic, caching, validation, or ORM dependencies belong here.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

import yfinance as yf  # type: ignore[import-untyped]


class YahooFinanceClient:
    """Low-level wrapper for Yahoo Finance API interactions."""

    DEFAULT_INDICES: dict[str, str] = {
        "^GSPC": "S&P 500",
        "^DJI": "Dow Jones",
        "^IXIC": "NASDAQ",
        "^NSEI": "NIFTY 50",
        "^BSESN": "SENSEX",
    }

    def fetch_quote(self, symbol: str) -> dict[str, Any]:
        """Fetch raw current quote dictionary for a given symbol."""
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        price = (
            info.get("regularMarketPrice")
            or info.get("currentPrice")
            or info.get("navPrice")
        )

        if price is None:
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                open_val = float(hist["Open"].iloc[-1])
                high_val = float(hist["High"].iloc[-1])
                low_val = float(hist["Low"].iloc[-1])
                vol_val = int(hist["Volume"].iloc[-1])
            else:
                price = 0.0
                open_val = None
                high_val = None
                low_val = None
                vol_val = None
        else:
            open_val = info.get("regularMarketOpen") or info.get("open")
            high_val = info.get("regularMarketDayHigh") or info.get("dayHigh")
            low_val = info.get("regularMarketDayLow") or info.get("dayLow")
            vol_val = info.get("regularMarketVolume") or info.get("volume")

        return {
            "symbol": symbol,
            "provider_symbol": symbol,
            "price": price,
            "open": open_val,
            "high": high_val,
            "low": low_val,
            "prev_close": info.get("previousClose")
            or info.get("regularMarketPreviousClose"),
            "volume": vol_val,
            "currency": info.get("currency"),
            "exchange": info.get("exchange"),
            "name": info.get("shortName") or info.get("longName") or symbol,
            "fetched_at": datetime.now(UTC),
        }

    def fetch_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[dict[str, Any]]:
        """Fetch historical OHLCV rows for a symbol."""
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return []

        bars: list[dict[str, Any]] = []
        for idx, row in df.iterrows():
            try:
                o = float(row["Open"])
                h = float(row["High"])
                low = float(row["Low"])
                c = float(row["Close"])
            except (ValueError, TypeError, KeyError):
                continue

            if (
                math.isnan(o)
                or math.isnan(h)
                or math.isnan(low)
                or math.isnan(c)
            ):
                continue

            if isinstance(idx, datetime):
                dt = idx.astimezone(UTC) if idx.tzinfo else idx.replace(tzinfo=UTC)
            else:
                dt = datetime.now(UTC)

            try:
                vol = int(row["Volume"]) if not math.isnan(float(row["Volume"])) else 0
            except (ValueError, TypeError, KeyError):
                vol = 0

            bars.append(
                {
                    "symbol": symbol,
                    "provider_symbol": symbol,
                    "timestamp": dt,
                    "interval": interval,
                    "open": o,
                    "high": h,
                    "low": low,
                    "close": c,
                    "volume": vol,
                }
            )
        return bars

    def fetch_indices(
        self,
        symbols_map: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch status dictionaries for major market indices."""
        target_map = symbols_map or self.DEFAULT_INDICES
        results: list[dict[str, Any]] = []

        for sym, name in target_map.items():
            try:
                ticker = yf.Ticker(sym)
                info = ticker.info or {}
                price = info.get("regularMarketPrice") or info.get("currentPrice")
                prev_close = info.get("previousClose")

                if price is None:
                    hist = ticker.history(period="2d")
                    if not hist.empty:
                        price = float(hist["Close"].iloc[-1])
                        if len(hist) > 1:
                            prev_close = float(hist["Close"].iloc[-2])

                change = None
                change_pct = None
                if price is not None and prev_close is not None and prev_close != 0:
                    change = float(price) - float(prev_close)
                    change_pct = (change / float(prev_close)) * 100

                results.append(
                    {
                        "symbol": sym,
                        "provider_symbol": sym,
                        "name": name,
                        "price": float(price) if price is not None else 0.0,
                        "change": change,
                        "change_pct": change_pct,
                    }
                )
            except Exception:
                results.append(
                    {
                        "symbol": sym,
                        "provider_symbol": sym,
                        "name": name,
                        "price": 0.0,
                        "change": None,
                        "change_pct": None,
                    }
                )

        return results

    def fetch_options_chain(self, symbol: str) -> dict[str, Any]:
        """Fetch options chain contracts for a symbol."""
        ticker = yf.Ticker(symbol)
        try:
            expirations = ticker.options
        except Exception:
            expirations = None

        if not expirations:
            return {
                "symbol": symbol,
                "options": [],
                "provider_note": f"No options chain data available for {symbol}.",
            }

        contracts: list[dict[str, Any]] = []
        first_exp = expirations[0]
        try:
            opt_chain = ticker.option_chain(first_exp)
            exp_date = datetime.strptime(first_exp, "%Y-%m-%d").date()

            def _parse_num(val: Any) -> float | None:
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    return None
                return float(val)

            def _parse_int(val: Any) -> int | None:
                parsed = _parse_num(val)
                return int(parsed) if parsed is not None else None

            # Process calls
            if opt_chain.calls is not None:
                for _, row in opt_chain.calls.iterrows():
                    contract_sym = str(row.get("contractSymbol", f"{symbol}-CALL"))
                    contracts.append(
                        {
                            "symbol": contract_sym,
                            "provider_symbol": contract_sym,
                            "expiry": exp_date,
                            "strike": float(row.get("strike", 0.0)),
                            "option_type": "call",
                            "last_price": _parse_num(row.get("lastPrice")),
                            "volume": _parse_int(row.get("volume")),
                            "open_interest": _parse_int(row.get("openInterest")),
                        }
                    )

            # Process puts
            if opt_chain.puts is not None:
                for _, row in opt_chain.puts.iterrows():
                    contract_sym = str(row.get("contractSymbol", f"{symbol}-PUT"))
                    contracts.append(
                        {
                            "symbol": contract_sym,
                            "provider_symbol": contract_sym,
                            "expiry": exp_date,
                            "strike": float(row.get("strike", 0.0)),
                            "option_type": "put",
                            "last_price": _parse_num(row.get("lastPrice")),
                            "volume": _parse_int(row.get("volume")),
                            "open_interest": _parse_int(row.get("openInterest")),
                        }
                    )
        except Exception:
            pass

        note = None if contracts else f"Options chain empty for {symbol}."
        return {
            "symbol": symbol,
            "options": contracts,
            "provider_note": note,
        }
