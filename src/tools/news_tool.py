import feedparser
import requests
from typing import List, Dict, Optional, Tuple
from jinja2 import Template

from src.utils.logger import get_logger
from src.utils.resilience import RetryConfig, retry_call, RetryableError

logger = get_logger(__name__)


class NonRetryableHTTPError(RuntimeError):
    """HTTP errors that should not be retried (e.g., 404/401/403)."""
    pass


def _fetch_bytes(
        url: str,
        *,
        timeout: Tuple[float, float] = (3.05, 12.0),
        retry_cfg: Optional[RetryConfig] = None,
) -> bytes:
    cfg = retry_cfg or RetryConfig()

    def _do():
        r = requests.get(url, timeout=timeout)
        # Retry transient statuses
        if r.status_code in cfg.retry_statuses:
            raise RetryableError(f"Transient HTTP {r.status_code}")
        # Non-transient -> fail fast (handled by caller)
        if r.status_code >= 400:
            raise NonRetryableHTTPError(f"HTTP {r.status_code}")
        return r.content

    return retry_call(
        _do,
        cfg=cfg,
        op_name="rss_http_get",
        logger=logger,
        retry_exceptions=(requests.RequestException, TimeoutError, OSError),
    )


def fetch_news_feeds(
        symbol: str,
        rss_templates: List[str],
        max_items: int = 6,
        timeout: Tuple[float, float] = (3.05, 12.0),
        retry_cfg: Optional[RetryConfig] = None,
) -> List[Dict]:
    logger.debug("Fetching news for %s from %d feeds", symbol, len(rss_templates))
    items: List[Dict] = []
    cfg = retry_cfg or RetryConfig()

    for tmpl in rss_templates:
        url = Template(tmpl).render(symbol=symbol)
        try:
            # content = _fetch_bytes(url, timeout=timeout, retry_cfg=cfg)
            feed = feedparser.parse(url)

            for e in feed.entries[:max_items]:
                items.append({
                    "title": getattr(e, "title", ""),
                    "link": getattr(e, "link", ""),
                    "published": getattr(e, "published", ""),
                    "summary": getattr(e, "summary", ""),
                })

            logger.debug("Fetched %d items from %s", min(len(feed.entries), max_items), url)

        except Exception as e:
            logger.warning("News fetch failed for %s (symbol=%s): %s", url, symbol, e)
            continue

    dedup: Dict[str, Dict] = {}
    for it in items:
        if it.get("link") and it["link"] not in dedup:
            dedup[it["link"]] = it

    final = list(dedup.values())[:max_items]
    logger.info("Total news items for %s: %d", symbol, len(final))
    return final
