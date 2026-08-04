"""Unit tests for YahooFinanceClient."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
from external.yahoo_finance.client import YahooFinanceClient


def test_yahoo_client_fetch_history_skips_nan() -> None:
    """
    Verify that rows with NaN OHLC values
    are skipped while valid rows are returned.
    """
    # Create a mock DataFrame simulating yfinance output
    # Row 1: Valid
    # Row 2: NaN Open
    # Row 3: Valid

    dt1 = datetime(2023, 1, 1, tzinfo=UTC)
    dt2 = datetime(2023, 1, 2, tzinfo=UTC)
    dt3 = datetime(2023, 1, 3, tzinfo=UTC)

    df = pd.DataFrame(
        {
            "Open": [150.0, float("nan"), 152.0],
            "High": [151.0, 151.5, 153.0],
            "Low": [149.0, 149.5, 151.0],
            "Close": [150.5, 150.0, 152.5],
            "Volume": [1000, 1500, 2000],
        },
        index=[dt1, dt2, dt3],
    )

    client = YahooFinanceClient()

    with patch("external.yahoo_finance.client.yf.Ticker") as mock_ticker_class:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df
        mock_ticker_class.return_value = mock_ticker

        bars = client.fetch_history("AAPL")

        # Assert only 2 valid bars are returned (dt1 and dt3)
        assert len(bars) == 2

        # Verify first bar
        assert bars[0]["timestamp"] == dt1
        assert bars[0]["open"] == 150.0
        assert bars[0]["volume"] == 1000

        # Verify second bar
        assert bars[1]["timestamp"] == dt3
        assert bars[1]["open"] == 152.0
        assert bars[1]["volume"] == 2000
