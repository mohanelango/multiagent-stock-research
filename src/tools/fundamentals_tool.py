# src/tools/fundamentals_tool.py
import requests
from typing import Dict, Any, Optional, Tuple

from src.utils.logger import get_logger
from src.utils.resilience import RetryConfig, retry_call, RetryableError

logger = get_logger(__name__)
BASE = "https://financialmodelingprep.com/stable"


def _call(
    url: str,
    *,
    timeout: Tuple[float, float] = (3.05, 15.0),  # (connect, read)
    retry_cfg: Optional[RetryConfig] = None,
) -> Dict[str, Any]:
    """
    Internal helper to call FMP with:
      - timeouts (connect/read)
      - exponential backoff retries for transient statuses (429/5xx/408)
      - NO retries for 402 (quota/tier), 400/401/403/404 etc.
    Returns {"ok": True, "json": <parsed>} on success.
    Returns {"ok": False, "status": <int>, "text": <str>} on HTTP errors.
    """
    cfg = retry_cfg or RetryConfig()

    def _do_request():
        r = requests.get(url, timeout=timeout)

        # Never retry quota/tier issues
        if r.status_code == 402:
            return r

        # Retry transient statuses only
        if r.status_code in cfg.retry_statuses:
            raise RetryableError(f"Transient HTTP {r.status_code}")

        return r

    try:
        r = retry_call(
            _do_request,
            cfg=cfg,
            op_name="fmp_http_get",
            logger=logger,
            retry_exceptions=(requests.RequestException, TimeoutError, OSError),
        )

        if r.status_code == 402:
            return {"ok": False, "status": 402, "text": "Payment Required (quota/tier limit)"}

        if r.status_code >= 400:
            return {"ok": False, "status": r.status_code, "text": r.text}

        # JSON parse can fail for malformed responses
        try:
            return {"ok": True, "json": r.json()}
        except ValueError:
            return {"ok": False, "status": r.status_code, "text": "Invalid JSON response from FMP"}

    except Exception as e:
        # Network-level failures after retries
        logger.error("FMP request failed after retries: %s", e)
        return {"ok": False, "status": None, "text": str(e)}


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
