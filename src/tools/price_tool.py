from __future__ import annotations

import yfinance as yf
from typing import Dict, Any, Optional

from src.utils.logger import get_logger
from src.utils.resilience import RetryConfig, retry_call, RetryableError

logger = get_logger(__name__)


def fetch_price_history(
    symbol: str,
    days: int = 30,
    *,
    retry_cfg: Optional[RetryConfig] = None,
) -> Dict[str, Any]:
    """
    Fetch price history via yfinance with:
      - bounded retries + exponential backoff (network/transient issues)
      - per-attempt timeout enforced by retry_call (thread-based)
      - structured __error__ returned on failures

    Returns:
      {"symbol": symbol, "data": [...], "meta": {...}} on success
      {"symbol": symbol, "data": [], "__error__": {...}} on failure
    """
    cfg = retry_cfg or RetryConfig(max_retries=2, base_delay_sec=0.5, max_delay_sec=6.0, timeout_sec=25.0)

    logger.debug("Fetching price history for %s (%d days)", symbol, days)

    def _do():
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=f"{days}d")
            return df
        except Exception as e:
            # Retry only for likely transient failures
            msg = str(e).lower()
            if any(k in msg for k in ["timeout", "timed out", "connection", "temporary", "rate", "429", "502", "503", "504"]):
                raise RetryableError(str(e))
            raise

    try:
        df = retry_call(
            _do,
            cfg=cfg,
            op_name=f"yfinance_history:{symbol}",
            logger=logger,
            retry_exceptions=(OSError, ConnectionError),
        )
    except Exception as e:
        logger.error("Price fetch failed for %s after retries: %s", symbol, e)
        return {
            "symbol": symbol,
            "data": [],
            "__error__": {
                "where": "prices",
                "status": None,
                "message": str(e),
            },
            "note": "Price data unavailable due to upstream error.",
            "meta": {"days": days},
        }

    if df is None or getattr(df, "empty", True):
        logger.warning("No price data found for %s", symbol)
        return {
            "symbol": symbol,
            "data": [],
            "__error__": {
                "where": "prices",
                "status": None,
                "message": "No data returned by yfinance (empty dataframe).",
            },
            "note": "No data returned.",
            "meta": {"days": days},
        }

    df = df.reset_index()
    df["Date"] = df["Date"].astype(str)

    records = df[["Date", "Open", "High", "Low", "Close", "Volume"]].to_dict(orient="records")
    logger.info("Fetched %d records for %s", len(records), symbol)
    return {"symbol": symbol, "data": records, "meta": {"days": days}}
