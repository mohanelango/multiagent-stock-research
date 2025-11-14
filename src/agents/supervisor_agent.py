from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SupervisorAgent:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are the supervising editor. Your job is to stitch a clean, complete, "
             "fully-structured markdown research report. Do NOT output any partial sections, "
             "unfinished sentences, dangling headings, or placeholder text. "
             "If a section cannot be completed with the available information, simply omit that "
             "section entirely and continue with the next one. The final output MUST NOT contain "
             "any incomplete blocks like '## Compliant Note' followed by empty or partial content."
             ),

            ("user",
             """Inputs:
              - Symbol: {symbol}
              - Data summary: {data_summary}
              - Compliant note: {final_note}

             Requirements for Final Output:
             1. Produce a polished markdown report only containing the below info:
                - Snapshot
                - Price Action
                - Fundamentals
                - Valuation / Technicals (if possible)
                - Headlines & Interpretation
                - Key Watch Items
                - Risks (if possible)
                - Near-Term View / Summary
                - Sources

             2. ONLY include sections that can be fully completed.
                - If any supplied section text is empty, incomplete, or appears truncated,
                  SKIP that section entirely.
                - NEVER output incomplete lines such as:
                      ## Section Title
                      Some incomplete
                  or:
                      Final Note

             3. The output MUST be clean, well-organized, and contain no placeholders,
                no TODOs, no half sentences, and no unfinished markdown blocks.

             Produce the final stitched report now.
             """
             )
        ])

        logger.info("Supervisor-Agent initialized.")

    def run(self, symbol: str, data_summary: str, final_note: str) -> str:
        logger.info("Composing final report for %s", symbol)
        chain = self.prompt | self.llm
        out = chain.invoke({"symbol": symbol, "data_summary": data_summary, "final_note": final_note})
        logger.info("Final report created for %s", symbol)
        return out.content
