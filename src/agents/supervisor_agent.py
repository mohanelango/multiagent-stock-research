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


class SupervisorAgent:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are the supervising editor and final authority of a professional equity research report. "
             "You do NOT generate raw analysis. You evaluate, restructure, and finalize content produced "
             "by other agents. Your responsibilities include:\n"
             "- Ensuring all sections are complete and professionally written\n"
             "- Removing any incomplete, duplicated, or low-quality sections\n"
             "- Enforcing a clean institutional research structure\n"
             "- Skipping any section that cannot be fully formed\n\n"
             "You must NEVER output partial sections, placeholders, or unfinished headings."
             ),
            ("user",
             """Inputs:
             - Symbol: {symbol}
             - Data summary: {data_summary}
             - Compliant note: {final_note}

             Your task:
             Produce a FINAL, publish-ready markdown research report.

             Rules:
             1. Only include sections that can be fully completed.
             2. Omit any section that lacks sufficient information.
             3. Normalize tone, structure, and formatting.
             4. Ensure the output looks like an institutional research note.

             Required Sections (only if complete):
             - Title
             - Snapshot
             - Price Action
             - Fundamentals
             - Valuation / Technicals
             - Headlines & Interpretation
             - Key Watch Items
             - Risks
             - Near-Term View
             - Sources

             Deliver ONLY the final report.
             """
             )
        ])
        self.retry_cfg = RetryConfig(max_retries=2, base_delay_sec=0.6, max_delay_sec=6.0, timeout_sec=120.0)
        logger.info("Supervisor-Agent initialized.")

    def run(self, symbol: str, data_summary: str, final_note: str) -> str:
        logger.info("Composing final report for %s", symbol)
        chain = self.prompt | self.llm
        payload = {"symbol": symbol, "data_summary": data_summary, "final_note": final_note}

        def _invoke():
            try:
                return chain.invoke(payload)
            except Exception as e:
                if _is_retryable_llm_exc(e):
                    raise RetryableError(str(e))
                raise

        out = retry_call(_invoke, cfg=self.retry_cfg, op_name="llm_supervisor_invoke", logger=logger)
        logger.info("Final report created for %s", symbol)
        return out.content
