from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SupervisorAgent:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        # self.prompt = ChatPromptTemplate.from_messages([
        #     ("system",
        #      "You are the supervising editor. Your job is to stitch a clean, complete, "
        #      "fully-structured markdown research report. Do NOT output any partial sections, "
        #      "unfinished sentences, dangling headings, or placeholder text. "
        #      "If a section cannot be completed with the available information, simply omit that "
        #      "section entirely and continue with the next one. The final output MUST NOT contain "
        #      "any incomplete blocks like '## Compliant Note' followed by empty or partial content."
        #      ),
        #
        #     ("user",
        #      """Inputs:
        #       - Symbol: {symbol}
        #       - Data summary: {data_summary}
        #       - Compliant note: {final_note}
        #
        #      Requirements for Final Output:
        #      1. Produce a polished markdown report only containing the below info:
        #         - Snapshot
        #         - Price Action
        #         - Fundamentals
        #         - Valuation / Technicals (if possible)
        #         - Headlines & Interpretation
        #         - Key Watch Items
        #         - Risks (if possible)
        #         - Near-Term View / Summary
        #         - Sources
        #
        #      2. ONLY include sections that can be fully completed.
        #         - If any supplied section text is empty, incomplete, or appears truncated,
        #           SKIP that section entirely.
        #         - NEVER output incomplete lines such as:
        #               ## Section Title
        #               Some incomplete
        #           or:
        #               Final Note
        #
        #      3. The output MUST be clean, well-organized, and contain no placeholders,
        #         no TODOs, no half sentences, and no unfinished markdown blocks.
        #
        #      Produce the final stitched report now.
        #      """
        #      )
        # ])
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

        logger.info("Supervisor-Agent initialized.")

    def run(self, symbol: str, data_summary: str, final_note: str) -> str:
        logger.info("Composing final report for %s", symbol)
        chain = self.prompt | self.llm
        out = chain.invoke({"symbol": symbol, "data_summary": data_summary, "final_note": final_note})
        logger.info("Final report created for %s", symbol)
        return out.content
