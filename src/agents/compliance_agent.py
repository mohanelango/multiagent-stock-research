from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ComplianceAgent:
    def __init__(self, llm: ChatOpenAI, forbidden: List[str], disclosure: List[str]):
        self.llm = llm
        self.forbidden = forbidden
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a compliance officer ensuring neutral tone and lawful phrasing."),
            ("user", """Analyst Note:
            {note}
            
            Forbidden phrases: {forbidden}
            Return a compliant, neutral 'Final Note'.""")
        ])
        logger.info("Compliance-Agent initialized with %d forbidden terms.", len(forbidden))

    def run(self, note: str) -> str:
        logger.info("Running compliance check.")
        chain = self.prompt | self.llm
        out = chain.invoke({
            "note": note,
            "forbidden": self.forbidden
        })
        logger.info("Compliance check done.")
        return out.content
