from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.utils.logger import get_logger
from src.utils.resilience import RetryConfig, retry_call, RetryableError

logger = get_logger(__name__)


def _is_retryable_llm_exc(e: Exception) -> bool:
    msg = str(e).lower()
    return any(k in msg for k in [
        "timeout", "timed out", "rate limit", "429",
        "temporarily", "unavailable", "502", "503", "504",
        "connection", "server error"
    ])


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
        self.retry_cfg = RetryConfig(max_retries=2, base_delay_sec=0.6, max_delay_sec=6.0, timeout_sec=90.0)
        logger.info("Analyst-Agent initialized.")

    def run(self, bundle: Dict[str, Any], days: int) -> str:
        symbol = bundle["symbol"]
        logger.info("Generating analyst note for %s", symbol)

        payload = {
            "symbol": symbol,
            "price_excerpt": str(bundle["prices"].get("data", [])[-5:]),
            "is_excerpt": str(bundle["fundamentals"].get("income_statement", [])[:1]),
            "km_excerpt": str(bundle["fundamentals"].get("key_metrics_ttm", [])[:1]),
            "news_excerpt": str(bundle.get("news", [])[:3]),
            "days": days,
        }

        chain = self.prompt | self.llm

        def _invoke():
            try:
                return chain.invoke(payload)
            except Exception as e:
                if _is_retryable_llm_exc(e):
                    raise RetryableError(str(e))
                raise

        out = retry_call(_invoke, cfg=self.retry_cfg, op_name="llm_analyst_invoke", logger=logger)
        logger.info("Analyst note completed for %s", symbol)
        return out.content
