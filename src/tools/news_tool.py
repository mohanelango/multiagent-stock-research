import feedparser
from typing import List, Dict
from jinja2 import Template
from src.utils.logger import get_logger

logger = get_logger(__name__)


def fetch_news_feeds(symbol: str, rss_templates: List[str], max_items: int = 6) -> List[Dict]:
    logger.debug("Fetching news for %s from %d feeds", symbol, len(rss_templates))
    items = []
    for tmpl in rss_templates:
        url = Template(tmpl).render(symbol=symbol)
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:max_items]:
                items.append({
                    "title": getattr(e, "title", ""),
                    "link": getattr(e, "link", ""),
                    "published": getattr(e, "published", ""),
                    "summary": getattr(e, "summary", "")
                })
            logger.debug("Fetched %d items from %s", len(feed.entries[:max_items]), url)
        except Exception as e:
            logger.warning("Error fetching from %s: %s", url, e)
            continue

    dedup = {}
    for it in items:
        if it["link"] and it["link"] not in dedup:
            dedup[it["link"]] = it

    final = list(dedup.values())[:max_items]
    logger.info("Total news items for %s: %d", symbol, len(final))
    return final
