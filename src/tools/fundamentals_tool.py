import requests
from typing import Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)
BASE = "https://financialmodelingprep.com/stable"


def _call(url: str) -> Dict[str, Any]:
    """
    Internal helper to call FMP with consistent error handling.
    Returns {"ok": True, "json": <parsed>} on success.
    Returns {"ok": False, "status": <int>, "text": <str>} on HTTP errors.
    """
    logger.debug("GET %s", url)
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 402:
            # Explicitly surface quota/tier issues
            return {"ok": False, "status": 402, "text": "Payment Required (quota/tier limit)", "url": url}
        r.raise_for_status()
        return {"ok": True, "json": r.json()}
    except requests.RequestException as e:
        status = getattr(e.response, "status_code", None)
        body = getattr(e.response, "text", str(e))
        return {"ok": False, "status": status, "text": body, "url": url}


def fetch_income_statement(symbol: str, api_key: str, limit: int = 2) -> Dict[str, Any]:
    url = f"{BASE}/income-statement?symbol={symbol}&limit={limit}&apikey={api_key}"
    res = _call(url)
    if res["ok"]:
        data = res["json"]
        logger.info("Fetched income statement for %s (%d records)", symbol, len(data))
        return {"symbol": symbol, "income_statement": data}
    # Error path
    logger.error("Error fetching income statement for %s: %s (status=%s)", symbol, res.get("text"), res.get("status"))
    return {
        "symbol": symbol,
        "income_statement": [],
        "__error__": {
            "where": "income_statement",
            "status": res.get("status"),
            "message": res.get("text"),
        },
    }


def fetch_key_metrics(symbol: str, api_key: str) -> Dict[str, Any]:
    url = f"{BASE}/key-metrics-ttm?symbol={symbol}&apikey={api_key}"
    res = _call(url)
    if res["ok"]:
        data = res["json"]
        logger.info("Fetched key metrics for %s", symbol)
        return {"symbol": symbol, "key_metrics_ttm": data}
    # Error path
    logger.error("Error fetching key metrics for %s: %s (status=%s)", symbol, res.get("text"), res.get("status"))
    return {
        "symbol": symbol,
        "key_metrics_ttm": [],
        "__error__": {
            "where": "key_metrics_ttm",
            "status": res.get("status"),
            "message": res.get("text"),
        },
    }
