from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from src.utils.logger import get_logger
from src.tools.price_tool import fetch_price_history
from src.tools.fundamentals_tool import fetch_income_statement, fetch_key_metrics
from src.tools.news_tool import fetch_news_feeds

logger = get_logger(__name__)


class DataAgent:
    def __init__(self, llm: ChatOpenAI, rss_templates: List[str], fmp_api_key: str, max_news: int = 6):
        self.llm = llm
        self.rss = rss_templates
        self.fmp_key = fmp_api_key
        self.max_news = max_news
        logger.info("Data-Agent initialized with max_news=%s", max_news)

    def run(self, symbol: str, days: int = 30) -> Dict[str, Any]:
        logger.info("Fetching data for %s (last %d days)", symbol, days)

        prices = fetch_price_history(symbol, days)
        inc = fetch_income_statement(symbol, api_key=self.fmp_key, limit=2)
        km = fetch_key_metrics(symbol, api_key=self.fmp_key)
        news = fetch_news_feeds(symbol, self.rss, max_items=self.max_news)

        # Collect non-fatal tool errors for downstream reporting
        tool_errors = []
        if isinstance(prices, dict) and prices.get("__error__"):
            tool_errors.append(prices["__error__"])
        if isinstance(inc, dict) and inc.get("__error__"):
            tool_errors.append(inc["__error__"])
        if isinstance(km, dict) and km.get("__error__"):
            tool_errors.append(km["__error__"])
        # news_tool may return error markers in list entries
        if isinstance(news, list):
            for n in news:
                if isinstance(n, dict) and n.get("__error__"):
                    tool_errors.append({"where": "news", "message": n.get("__error__"), "source": n.get("source")})

        logger.info(
            "Data fetch complete for %s: %d price rows, %d news items",
            symbol,
            len(prices.get("data", [])) if isinstance(prices, dict) else 0,
            len(news) if isinstance(news, list) else 0,
        )

        fundamentals = {
            "income_statement": inc.get("income_statement", []) if isinstance(inc, dict) else [],
            "key_metrics_ttm": km.get("key_metrics_ttm", []) if isinstance(km, dict) else [],
            "__errors__": [e for e in [inc.get("__error__") if isinstance(inc, dict) else None,
                                      km.get("__error__") if isinstance(km, dict) else None] if e],
        }

        return {
            "symbol": symbol,
            "prices": prices if isinstance(prices, dict) else {"symbol": symbol, "data": []},
            "fundamentals": fundamentals,
            "news": news if isinstance(news, list) else [],
            "__errors__": tool_errors,
        }
