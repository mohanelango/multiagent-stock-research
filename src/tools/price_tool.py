import yfinance as yf
from typing import Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)


def fetch_price_history(symbol: str, days: int = 30) -> Dict[str, Any]:
    logger.debug("Fetching price history for %s (%d days)", symbol, days)
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=f"{days}d")
    if df.empty:
        logger.warning("No price data found for %s", symbol)
        return {"symbol": symbol, "data": [], "note": "No data returned."}
    df = df.reset_index()
    df["Date"] = df["Date"].astype(str)
    records = df[["Date", "Open", "High", "Low", "Close", "Volume"]].to_dict(orient="records")
    logger.info("Fetched %d records for %s", len(records), symbol)
    return {"symbol": symbol, "data": records, "meta": {"days": days}}
