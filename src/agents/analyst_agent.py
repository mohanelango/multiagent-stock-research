from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AnalystAgent:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an equity research analyst. Write concise, professional analysis."),
            ("user", """Given:
                    - Symbol: {symbol}
                    - Price data (recent): {price_excerpt}
                    - Fundamentals (income statement excerpt): {is_excerpt}
                    - Key metrics TTM excerpt: {km_excerpt}
                    - Latest headlines: {news_excerpt}
                    
                    Tasks:
                    1) Summarize the last {days} days of price action.
                    2) Identify 2-3 key fundamental takeaways.
                    3) Highlight 2 notable headlines and implications.
                    4) Provide a neutral 'Analyst Note' (<=250 words).""")
        ])
        logger.info("Analyst-Agent initialized.")

    def run(self, bundle: Dict[str, Any], days: int) -> str:
        symbol = bundle["symbol"]
        logger.info("Generating analyst note for %s", symbol)
        price_excerpt = str(bundle["prices"].get("data", [])[-5:])
        is_excerpt = str(bundle["fundamentals"].get("income_statement", [])[:1])
        km_excerpt = str(bundle["fundamentals"].get("key_metrics_ttm", [])[:1])
        news_excerpt = str(bundle.get("news", [])[:3])
        chain = self.prompt | self.llm
        out = chain.invoke({
            "symbol": symbol,
            "price_excerpt": price_excerpt,
            "is_excerpt": is_excerpt,
            "km_excerpt": km_excerpt,
            "news_excerpt": news_excerpt,
            "days": days
        })
        logger.info("Analyst note completed for %s", symbol)
        return out.content
