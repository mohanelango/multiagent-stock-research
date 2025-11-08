from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SupervisorAgent:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the supervising editor. Stitch a clean markdown report."),
            ("user", """Inputs:
                        - Symbol: {symbol}
                        - Data summary: {data_summary}
                        - Compliant note: {final_note}
                        Compose a markdown report with title, snapshot, commentary, and sources.""")
        ])
        logger.info("Supervisor-Agent initialized.")

    def run(self, symbol: str, data_summary: str, final_note: str) -> str:
        logger.info("Composing final report for %s", symbol)
        chain = self.prompt | self.llm
        out = chain.invoke({"symbol": symbol, "data_summary": data_summary, "final_note": final_note})
        logger.info("Final report created for %s", symbol)
        return out.content
