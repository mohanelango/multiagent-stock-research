import yfinance as yf
import yaml
from typing import Dict, Any
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from src.utils.helper import safe_num
from src.utils.logger import get_logger
from src.tools.math_tool import basic_return_stats
from src.tools.plot_tool import save_price_plot
from src.tools.storage_tool import save_json, save_markdown, render_filename
from src.agents.data_agent import DataAgent
from src.agents.analyst_agent import AnalystAgent
from src.agents.compliance_agent import ComplianceAgent
from src.agents.supervisor_agent import SupervisorAgent
import textwrap
import pypandoc
import re
import os
from datetime import datetime

logger = get_logger(__name__)


def _llm_from_cfg(cfg: Dict[str, Any]) -> ChatOpenAI:
    """
    Safely initialize ChatOpenAI for GPT-5 and other OpenAI chat models.
    GPT-5 and GPT-4o families only accept default temperature (1.0).
    """
    prov = cfg["llm"]["provider"]
    model = cfg["llm"]["model"]
    temperature = cfg["llm"].get("temperature", 1.0)
    max_tokens = cfg["llm"].get("max_tokens", 3500)

    # Force safe defaults for GPT-5 or GPT-4o models
    if any(tag in model for tag in ["gpt-5", "gpt-4o"]) and temperature != 1.0:
        logger.warning(
            "Model %s does not support custom temperature (%.1f). "
            "Overriding to 1.0 for compatibility.", model, temperature
        )
        temperature = 1.0

    logger.info("Initializing LLM: provider=%s, model=%s, temperature=%.1f", prov, model, temperature)
    return ChatOpenAI(model=model, temperature=temperature, max_tokens=max_tokens)


# ----------------------------------------------------------------------
# BUILD LANGGRAPH PIPELINE
# ----------------------------------------------------------------------
def build_graph(cfg: Dict[str, Any], fmp_api_key: str | None = None):
    """
    Builds the LangGraph orchestration pipeline connecting all 4 agents.
    """
    llm = _llm_from_cfg(cfg)
    rss = cfg["news"]["sources"]
    max_news = cfg["orchestration"]["max_news"]

    # Initialize agents
    data_agent = DataAgent(llm, rss_templates=rss, fmp_api_key=fmp_api_key or "demo", max_news=max_news)
    analyst = AnalystAgent(llm)
    compliance = ComplianceAgent(
        llm,
        forbidden=cfg["compliance"]["forbidden_phrases"],
        disclosure=cfg["compliance"]["disclosure"]
    )
    supervisor = SupervisorAgent(llm)

    # Define graph with plain dict state
    g = StateGraph(dict)

    # ---------------- Nodes ----------------
    def node_collect_data(state: dict):
        symbol, days = state["symbol"], state["days"]
        logger.info("[Node: Collect Data] Starting data collection for %s", symbol)
        bundle = data_agent.run(symbol, days)
        state["bundle"] = bundle
        logger.info("[Node: Collect Data] Completed for %s", symbol)

        # ---------- STRICT MODE EARLY-ABORT ----------
        strict = bool(cfg.get("strict_mode", True))

        # Extract blocks
        prices_ok = bool(bundle.get("prices", {}).get("data"))
        fundamentals = bundle.get("fundamentals", {}) or {}
        inc_list = fundamentals.get("income_statement")
        met_list = fundamentals.get("key_metrics_ttm")

        # Detect upstream API errors if fundamentals_tool exposed them
        inc_err = fundamentals.get("__error__") if isinstance(fundamentals,
                                                              dict) and "__error__" in fundamentals else None
        # Some DataAgents merge per-endpoint dicts; handle that shape too:
        if isinstance(inc_list, dict) and "__error__" in inc_list:
            inc_err = inc_list["__error__"]
            inc_list = inc_list.get("income_statement", [])

        if isinstance(met_list, dict) and "__error__" in met_list:
            met_err = met_list["__error__"]
            met_list = met_list.get("key_metrics_ttm", [])
        else:
            met_err = None

        news_ok = bool(bundle.get("news"))

        # If we saw explicit 402 from either fundamentals call, abort with suggestion
        def _mk402_message(where: str, err: dict) -> str:
            return (
                f"Upstream API failure ({where}) for {symbol}: status={err.get('status')} "
                f"- {err.get('message')}. Suggestion: provide a valid paid FMP API key or disable strict_mode."
            )

        if inc_err and inc_err.get("status") == 402:
            msg = _mk402_message("income_statement", inc_err)
            logger.error(msg)
            state["__fatal__"] = msg
            raise ValueError(msg)

        if met_err and met_err.get("status") == 402:
            msg = _mk402_message("key_metrics_ttm", met_err)
            logger.error(msg)
            state["__fatal__"] = msg
            raise ValueError(msg)

        if strict:
            missing = []
            if not prices_ok: missing.append("prices")
            if not (inc_list and isinstance(inc_list, list)): missing.append("income_statement")
            if not (met_list and isinstance(met_list, list)): missing.append("key_metrics_ttm")
            if not news_ok: missing.append("news")

            if missing:
                # If fundamentals are missing and we don't have explicit 402 info, still guide the user
                hint = ""
                if "income_statement" in missing or "key_metrics_ttm" in missing:
                    hint = " Possible causes: free FMP quota exhausted, invalid API key, or endpoint not available for this ticker."

                reason = f"Strict mode abort: missing critical data: {', '.join(missing)} for {symbol}.{hint}"
                logger.error("%s", reason)
                state["__fatal__"] = reason
                raise ValueError(reason)

        return state

    def node_analyze(state: dict):
        logger.info("[Node: Analyze] Generating analyst note for %s", state["symbol"])
        note = analyst.run(state["bundle"], state["days"])
        state["analyst_note"] = note
        logger.info("[Node: Analyze] Completed for %s", state["symbol"])
        return state

    def node_compliance(state: dict):
        logger.info("[Node: Compliance] Checking compliance for %s", state["symbol"])
        final_note = compliance.run(state["analyst_note"])
        state["final_note"] = final_note
        logger.info("[Node: Compliance] Completed for %s", state["symbol"])
        return state

    def node_enrich_and_publish(state: dict):
        """Combine all collected insights into a unified Markdown report with fundamentals, news, commentary,
        and metadata, and automatically export it to PDF."""

        symbol, outdir = state["symbol"], state["outdir"]
        bundle = state["bundle"]
        logger.info("[Node: Publish] Enriching and publishing unified report for %s", symbol)

        # ----------------------------------------------------------------------
        #  Compute snapshot stats safely
        # ----------------------------------------------------------------------
        price_rows = bundle.get("prices", {}).get("data", [])
        if not price_rows:
            error_msg = f"No price data available for {symbol}. Symbol may be invalid or delisted. Skipping report " \
                        f"generation."
            logger.error(error_msg)
            state["error"] = error_msg
            return state

        dates = [r.get("Date") for r in price_rows if r.get("Date")]
        closes = [r.get("Close") for r in price_rows if isinstance(r.get("Close"), (float, int))]

        stats = basic_return_stats(closes)
        mean_ret = float(stats.get("mean") or 0.0)
        vol_ret = float(stats.get("stdev") or stats.get("volatility") or 0.0)
        min_ret = float(stats.get("min") or 0.0)
        max_ret = float(stats.get("max") or 0.0)

        # ----------------------------------------------------------------------
        #  Fundamentals extraction
        # ----------------------------------------------------------------------
        fundamentals = bundle.get("fundamentals", {})
        inc_list = fundamentals.get("income_statement", [])
        met_list = fundamentals.get("key_metrics_ttm", [])
        inc, met = (inc_list[0], met_list[0]) if inc_list and met_list else ({}, {})
        reported_currency = inc.get("reportedCurrency")

        # ----------------------------------------------------------------------
        #  Save price chart
        # ----------------------------------------------------------------------
        plot_path = save_price_plot(dates, closes, reported_currency, os.path.join(outdir, f"{symbol}_chart.png"))
        logger.debug("[Node: Publish] Chart saved for %s -> %s", symbol, plot_path)
        # ----------------------------------------------------------------------
        #  News aggregation (clean alignment + safe escaping)
        # ----------------------------------------------------------------------
        news_items = bundle.get("news", [])
        if news_items:
            cleaned_news = []
            for n in news_items[:8]:
                title = n.get("title", "Untitled").strip()
                title = re.sub(r"[\[\]\n\r]+", " ", title)  # sanitize brackets/newlines
                link = n.get("link", "").strip()
                date_str = n.get("published", "")[:16] or "N/A"
                if link:
                    cleaned_news.append(f"- [{title}]({link}) ({date_str})")
                else:
                    cleaned_news.append(f"- {title} ({date_str})")
            # Ensure list always starts after a blank line
            news_summary = "\n" + "\n".join(cleaned_news)
        else:
            news_summary = "No significant news headlines found in this period."

        raw = state.get("final_note", "")
        # Remove line breaks inside sentences
        text = " ".join(raw.split())
        # Fix cases like "...risk.- Positioning..." → "...risk. Positioning..."
        text = re.sub(r"\.-\s*", ". ", text)
        # Split by sentence endings
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        # Build hyphen-prefixed lines
        safe_analyst_summary = "\n".join(f"- {s.strip()}" for s in sentences if s.strip())

        # ----------------------------------------------------------------------
        # Construct snapshot text safely
        # ----------------------------------------------------------------------
        if price_rows:
            stats_block = (
                f"- Mean: {mean_ret:.4f} ({mean_ret * 100:.2f}%)\n"
                f"- Volatility: {vol_ret:.4f} ({vol_ret * 100:.2f}%)\n"
                f"- Min: {min_ret:.4f} ({min_ret * 100:.2f}%)\n"
                f"- Max: {max_ret:.4f} ({max_ret * 100:.2f}%)\n"
            )
        else:
            stats_block = "- Insufficient price data for return statistics.\n"

        # ----------------------------------------------------------------------
        # Create unified Markdown content
        # ----------------------------------------------------------------------
        report_md = f"""
    # {symbol}: {state['days']}-Session Market Snapshot

## 1. Snapshot
- Symbol: {symbol}
- Data Coverage: {len(price_rows)} rows ({max(len(price_rows) - 1, 0)} returns)
{stats_block}- News Items Processed: {len(news_items)}

## 2. Fundamental Highlights
- Fiscal Year: {int(inc.get('fiscalYear')) if inc.get('fiscalYear') else "N/A"}.
- Revenue: {safe_num(inc.get('revenue'), reported_currency)}.
- Net Income: {safe_num(inc.get('netIncome'), reported_currency)}.
- EPS (Diluted): {safe_num(inc.get('epsDiluted'), reported_currency)}.
- Return on Equity (TTM): {safe_num(met.get('returnOnEquityTTM'), reported_currency)}.
- Free Cash Flow Yield (TTM): {safe_num(met.get('freeCashFlowYieldTTM'), reported_currency)}.

    ## 3. Recent News Headlines
    {news_summary}

## 4. Analyst Commentary
{safe_analyst_summary}

## 5. Methodology
- Prices sourced via yfinance.
- Fundamentals via FinancialModelingPrep (free key or fallback).
- News via RSS feeds.
- Volatility and returns calculated using numpy and pandas.
- Report generated through LangGraph multi-agent orchestration:
  - **Data Agent:** Market and fundamental data collection.
  - **Analyst Agent:** Narrative generation.
  - **Compliance Agent:** Disclosure and phrasing checks.
  - **Supervisor Agent:** Final synthesis and report structuring.

## 6. Execution Metadata
- Model: GPT-5.
- Run Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}.
- Coverage Days: {state['days']}.
- Output Directory: {outdir}.
- Data Sources: yfinance, FMP (Free/Fallback), Public RSS Feeds.
- Pipeline: LangGraph Orchestration Framework.

<div style="text-align: center; margin-top: 25px; margin-bottom: 25px;">
  <img src="{os.path.abspath(plot_path)}" alt="Price Chart" style="width: 70%; margin: auto; display: block;">
  <p style="font-weight: bold; margin-top: 10px;">Price Chart</p>
</div>


    ## 7. Compliance Disclaimer
    This automated report is generated by a multi-agent AI research framework (LangGraph + LangChain + GPT-5).  
    It is intended for **educational and informational purposes only** and does **not** constitute investment advice.  
    Past performance is not indicative of future results. Data accuracy is not guaranteed.


    **Generated by the Automated Stock Research Multi-Agent System.**
    """
        # Normalize and enhance Markdown layout
        report_md = textwrap.dedent(report_md).strip()
        report_md = report_md.replace("## ", "\n## ")

        # ----------------------------------------------------------------------
        #  Save Markdown + JSON
        # ----------------------------------------------------------------------
        file_name = render_filename(cfg["report"]["filename_template"], symbol=symbol)
        save_json(bundle, outdir, f"{symbol}_raw.json")
        save_markdown(report_md, outdir, file_name)

        state["report_path"] = os.path.join(outdir, file_name)
        state["plot_path"] = plot_path
        logger.info("[Node: Publish] Unified report ready for %s -> %s", symbol, state["report_path"])

        # ----------------------------------------------------------------------
        # Export PDF with CSS and image embedding
        # ----------------------------------------------------------------------
        pdf_path = os.path.join(outdir, file_name.replace(".md", ".pdf"))
        try:
            md_text = open(state["report_path"], "r", encoding="utf-8").read()
            css_path = os.path.abspath(os.path.join("assets", "pdf_style.css"))
            pypandoc.convert_text(
                md_text,
                "pdf",
                format="md",
                outputfile=pdf_path,
                extra_args=[
                    "--standalone",
                    "--pdf-engine=wkhtmltopdf",
                    f"--metadata=title:{symbol} Stock Market Report",
                    f"--css={css_path}",
                    f"--resource-path={outdir}",
                    f"--resource-path={os.path.dirname(plot_path)}"
                ],
            )
            logger.info("[Node: Publish] PDF version created for %s -> %s", symbol, pdf_path)
            state["pdf_path"] = file_name.replace(".md", ".pdf")
        except Exception as e:
            logger.warning("PDF export failed for %s: %s", symbol, e)

        return state

    # ---------------- Edges ----------------
    g.add_node("collect_data", node_collect_data)
    g.add_node("analyze", node_analyze)
    g.add_node("compliance", node_compliance)
    g.add_node("enrich_and_publish", node_enrich_and_publish)

    g.add_edge(START, "collect_data")
    g.add_edge("collect_data", "analyze")
    g.add_edge("analyze", "compliance")
    g.add_edge("compliance", "enrich_and_publish")
    g.add_edge("enrich_and_publish", END)

    logger.info("LangGraph pipeline successfully built.")
    return g.compile()


# ----------------------------------------------------------------------
#  EXECUTION ENTRYPOINT
# ----------------------------------------------------------------------
def run_pipeline(symbol: str, days: int, outdir: str, human: bool = False) -> Dict[str, Any]:
    """
    Run the multi-agent pipeline end-to-end and return paths to generated artifacts.
    """
    symbol_uppercase = symbol.upper()
    outdir = os.path.join(outdir, symbol_uppercase)
    load_dotenv()
    logger.info("=== Starting pipeline for %s (days=%d) ===", symbol, days)

    # ---------- Pre-check with yfinance ----------
    try:
        ticker = yf.Ticker(symbol_uppercase)
        info = ticker.info
        if not info or "shortName" not in info or info.get("regularMarketPrice") is None:
            error_msg = (
                f"Symbol {symbol_uppercase} is invalid or has no current market data "
                "(possibly de-listed or inactive)."
            )
            logger.error(error_msg)
            return {
                "status": "error",
                "symbol": symbol_uppercase,
                "reason": error_msg,
                "suggested_action": "Verify the ticker or try another symbol."
            }
    except Exception as exc:
        error_msg = f"Could not validate symbol {symbol_uppercase}: {exc}"
        logger.error(error_msg)
        return {
            "status": "error",
            "symbol": symbol_uppercase,
            "reason": error_msg,
        }

    # Load YAML configuration
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Fetch FMP key from env or default to demo
    fmp_key = os.getenv("FMP_API_KEY", "demo")
    logger.debug("Loaded configuration and API key.")

    try:
        app = build_graph(cfg, fmp_api_key=fmp_key)
        state = {"symbol": symbol_uppercase, "days": days, "outdir": outdir}
        result = app.invoke(state)
    except ValueError as e:
        # Clean, structured error (raised by strict-mode or API-aware checks)
        msg = str(e)
        logger.error("Pipeline failed for %s: %s", symbol_uppercase, msg)

        # Add a gentle suggestion if we detect 402 in the message
        suggestion = None
        if "402" in msg or "Payment Required" in msg:
            suggestion = "Provide a paid FMP API key or set strict_mode: false in config/settings.yaml."

        return {
            "status": "error",
            "symbol": symbol_uppercase,
            "reason": msg,
            **({"suggested_action": suggestion} if suggestion else {})
        }
    except Exception as e:
        logger.exception("Pipeline failed for %s: %s", symbol_uppercase, e)
        return {
            "status": "error",
            "symbol": symbol_uppercase,
            "reason": f"Unexpected pipeline error: {e}",
        }

    # Optional human-in-the-loop review
    if str(os.getenv("HUMAN_IN_LOOP", "false")).lower() == "true" or human:
        input(f"\n[HUMAN-IN-THE-LOOP] Review report at {result.get('report_path')} and press Enter to continue...\n")
        logger.info("Human-in-loop approved report for %s", symbol_uppercase)

    return {
        "report": result.get("report_path"),
        "plot": result.get("plot_path"),
        "raw": os.path.join(outdir, f"{symbol_uppercase}_raw.json"),
        "pdf": result.get("pdf_path"),
    }
