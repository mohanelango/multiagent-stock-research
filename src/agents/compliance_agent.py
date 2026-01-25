from typing import List
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


class ComplianceAgent:
    def __init__(self, llm: ChatOpenAI, forbidden: List[str], disclosure: List[str]):
        self.llm = llm
        self.forbidden = forbidden
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a compliance officer responsible for enforcing legal safety, neutrality, "
             "and disclosure requirements. You must rewrite content to remove prohibited claims, "
             "add disclosures if required, and ensure regulatory-safe language. "
             "You do not add new analysis."
             ),
            ("user", """Analyst Note:
            {note}

            Forbidden phrases: {forbidden}
            Return a compliant, neutral 'Final Note'.""")
        ])
        self.retry_cfg = RetryConfig(max_retries=2, base_delay_sec=0.6, max_delay_sec=6.0, timeout_sec=90.0)
        logger.info("Compliance-Agent initialized with %d forbidden terms.", len(forbidden))

    def run(self, note: str) -> str:
        logger.info("Running compliance check.")
        chain = self.prompt | self.llm
        payload = {"note": note, "forbidden": self.forbidden}

        def _invoke():
            try:
                return chain.invoke(payload)
            except Exception as e:
                if _is_retryable_llm_exc(e):
                    raise RetryableError(str(e))
                raise

        out = retry_call(_invoke, cfg=self.retry_cfg, op_name="llm_compliance_invoke", logger=logger)
        logger.info("Compliance check done.")
        return out.content
