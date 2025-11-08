from typing import Dict, Any, List
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
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
        self.parser = StrOutputParser()
        self.system = PromptTemplate.from_template("You are a data ingestion agent assembling clean JSON bundles.")
        logger.info("Data-Agent initialized with max_news=%s", max_news)

    def run(self, symbol: str, days: int = 30) -> Dict[str, Any]:
        logger.info("Fetching data for %s (last %d days)", symbol, days)
        prices = fetch_price_history(symbol, days)
        inc = fetch_income_statement(symbol, api_key=self.fmp_key, limit=2)
        km = fetch_key_metrics(symbol, api_key=self.fmp_key)
        news = fetch_news_feeds(symbol, self.rss, max_items=self.max_news)
        logger.info("Data fetch complete for %s: %d price rows, %d news items", symbol, len(prices.get("data", [])),
                    len(news))
        return {
            "symbol": symbol,
            "prices": prices,
            "fundamentals": {
                "income_statement": inc.get("income_statement", []),
                "key_metrics_ttm": km.get("key_metrics_ttm", [])
            },
            "news": news
        }
