# src/graph/orchestrator.py
from __future__ import annotations

import uuid
import yaml
import textwrap
import re
import os
import concurrent.futures as cf
from datetime import datetime
from typing import Dict, Any

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

from src.guardrails.inputs import validate_request
from src.guardrails.outputs import enforce_neutrality
from src.utils.helper import safe_num
from src.utils.log_context import set_log_context
from src.utils.logger import get_logger
from src.tools.math_tool import basic_return_stats
from src.tools.plot_tool import save_price_plot
from src.tools.storage_tool import save_json, save_markdown, render_filename

from src.agents.data_agent import DataAgent
from src.agents.analyst_agent import AnalystAgent
from src.agents.compliance_agent import ComplianceAgent
from src.agents.supervisor_agent import SupervisorAgent

logger = get_logger(__name__)


def _state_warn(state: dict, msg: str):
    """Accumulate non-fatal warnings for inclusion in report + logs."""
    logger.warning(msg)
    state.setdefault("__warnings__", []).append(msg)


def _bundle_error_summary(bundle: dict) -> list[str]:
    """
    Collect errors from DataAgent output if present.
    Supports:
      - bundle["__errors__"] list of dicts/strings
      - bundle["prices"]["__error__"]
      - bundle["fundamentals"]["__errors__"]
      - news items with "__error__"
    """
    msgs: list[str] = []

    for e in bundle.get("__errors__", []) or []:
        if isinstance(e, dict):
            where = e.get("where", "unknown")
            message = e.get("message", "") or e.get("text", "")
            msgs.append(f"{where}: {message}".strip())
        else:
            msgs.append(str(e))

    p_err = (bundle.get("prices") or {}).get("__error__")
    if p_err:
        if isinstance(p_err, dict):
            msgs.append(f"prices: {p_err.get('message', '')}".strip())
        else:
            msgs.append(f"prices: {p_err}")

    f = bundle.get("fundamentals") or {}
    for e in f.get("__errors__", []) or []:
        if isinstance(e, dict):
            msgs.append(f"{e.get('where', 'unknown')}: {e.get('message', '')}".strip())
        else:
            msgs.append(str(e))

    news = bundle.get("news")
    if isinstance(news, list):
        for n in news:
            if isinstance(n, dict) and n.get("__error__"):
                src = n.get("source", "")
                msgs.append(f"news: {n.get('__error__')}{' | ' + src if src else ''}")

    out: list[str] = []
    seen = set()
    for m in msgs:
        m = str(m).strip()
        if m and m not in seen:
            out.append(m)
            seen.add(m)
    return out


def _llm_from_cfg(cfg: Dict[str, Any]) -> ChatOpenAI:
    """
    Safely initialize ChatOpenAI for GPT-5 and other OpenAI chat models.
    GPT-5 and GPT-4o families only accept default temperature (1.0).
    """
    prov = cfg["llm"]["provider"]
    model = cfg["llm"]["model"]
    temperature = cfg["llm"].get("temperature", 1.0)
    max_tokens = cfg["llm"].get("max_tokens", 3500)

    if any(tag in model for tag in ["gpt-5", "gpt-4o"]) and temperature != 1.0:
        logger.warning(
            "Model %s does not support custom temperature (%.1f). Overriding to 1.0 for compatibility.",
            model,
            temperature,
        )
        temperature = 1.0

    logger.info("Initializing LLM: provider=%s, model=%s, temperature=%.1f", prov, model, temperature)
    return ChatOpenAI(model=model, temperature=temperature, max_tokens=max_tokens)


def build_graph(cfg: Dict[str, Any], fmp_api_key: str | None = None):
    """
    Builds the LangGraph orchestration pipeline connecting all 4 agents.
    """
    llm = _llm_from_cfg(cfg)
    rss = cfg["news"]["sources"]
    max_news = cfg["orchestration"]["max_news"]

    data_agent = DataAgent(llm, rss_templates=rss, fmp_api_key=fmp_api_key or "demo", max_news=max_news)
    analyst = AnalystAgent(llm)
    compliance = ComplianceAgent(
        llm,
        forbidden=cfg["compliance"]["forbidden_phrases"],
        disclosure=cfg["compliance"]["disclosure"],
    )
    supervisor = SupervisorAgent(llm)

    g = StateGraph(dict)

    def node_collect_data(state: dict):
        symbol, days = state["symbol"], state["days"]
        logger.info("[Run:%s][Node: Collect Data] Starting data collection for %s", state.get("run_id"), symbol)

        bundle = data_agent.run(symbol, days)
        state["bundle"] = bundle

        logger.info("[Run:%s][Node: Collect Data] Completed for %s", state.get("run_id"), symbol)

        strict = bool(cfg.get("StrictMode", {}).get("strict_mode", True))

        prices_ok = bool(bundle.get("prices", {}).get("data"))
        fundamentals = bundle.get("fundamentals", {}) or {}
        inc_list = fundamentals.get("income_statement")
        met_list = fundamentals.get("key_metrics_ttm")

        # Detect upstream API errors if fundamentals_tool exposed them
        inc_err = fundamentals.get("__error__") if isinstance(fundamentals,
                                                              dict) and "__error__" in fundamentals else None

        if isinstance(inc_list, dict) and "__error__" in inc_list:
            inc_err = inc_list["__error__"]
            inc_list = inc_list.get("income_statement", [])

        if isinstance(met_list, dict) and "__error__" in met_list:
            met_err = met_list["__error__"]
            met_list = met_list.get("key_metrics_ttm", [])
        else:
            met_err = None

        # News: treat "ok" as presence of at least one valid item (not just error markers)
        news_items = bundle.get("news", [])
        if isinstance(news_items, list):
            news_ok = any(isinstance(n, dict) and not n.get("__error__") for n in news_items) or (len(news_items) > 0)
        else:
            news_ok = False

        def _mk402_message(where: str, err: dict) -> str:
            return (
                f"Upstream API failure ({where}) for {symbol}: status={err.get('status')} - {err.get('message')}. "
                "Suggestion: provide a valid paid FMP API key or disable strict_mode."
            )

        if inc_err and isinstance(inc_err, dict) and inc_err.get("status") == 402:
            msg = _mk402_message("income_statement", inc_err)
            logger.error(msg)
            state["__fatal__"] = msg
            raise ValueError(msg)

        if met_err and isinstance(met_err, dict) and met_err.get("status") == 402:
            msg = _mk402_message("key_metrics_ttm", met_err)
            logger.error(msg)
            state["__fatal__"] = msg
            raise ValueError(msg)

        if strict:
            missing = []
            if not prices_ok:
                missing.append("prices")
            if not (inc_list and isinstance(inc_list, list)):
                missing.append("income_statement")
            if not (met_list and isinstance(met_list, list)):
                missing.append("key_metrics_ttm")
            if not news_ok:
                missing.append("news")

            if missing:
                hint = ""
                if "income_statement" in missing or "key_metrics_ttm" in missing:
                    hint = " Possible causes: free FMP quota exhausted, invalid API key, or endpoint not available for this ticker."
                reason = f"Strict mode abort: missing critical data: {', '.join(missing)} for {symbol}.{hint}"
                logger.error("%s", reason)
                state["__fatal__"] = reason
                raise ValueError(reason)

        # Non-strict: proceed, but record warnings
        if not strict:
            for m in _bundle_error_summary(bundle):
                _state_warn(state, f"Data warning for {symbol}: {m}")

            if not prices_ok:
                _state_warn(state, f"{symbol}: Price series missing/empty. Report generation may fail.")
            if not (inc_list and isinstance(inc_list, list)):
                _state_warn(state, f"{symbol}: Fundamentals income_statement missing. Using N/A placeholders.")
            if not (met_list and isinstance(met_list, list)):
                _state_warn(state, f"{symbol}: Fundamentals key_metrics_ttm missing. Using N/A placeholders.")
            if not news_ok:
                _state_warn(state, f"{symbol}: News feed empty/unavailable. Proceeding without headlines.")

        return state

    def node_analyze(state: dict):
        symbol = state["symbol"]
        logger.info("[Run:%s][Node: Analyze] Generating analyst note for %s", state.get("run_id"), symbol)

        try:
            note = analyst.run(state["bundle"], state["days"])
            if not isinstance(note, str) or not note.strip():
                raise ValueError("AnalystAgent returned empty output.")
            state["analyst_note"] = note
        except Exception as e:
            _state_warn(state, f"{symbol}: AnalystAgent failed, using fallback note. ({e})")
            state["analyst_note"] = (
                "Analyst note unavailable due to an upstream generation error. "
                "The report continues with available market data and disclosures."
            )

        logger.info("[Run:%s][Node: Analyze] Completed for %s", state.get("run_id"), symbol)
        return state

    def node_compliance(state: dict):
        symbol = state["symbol"]
        logger.info("[Run:%s][Node: Compliance] Checking compliance for %s", state.get("run_id"), symbol)

        try:
            final_note = compliance.run(state["analyst_note"])
            if not isinstance(final_note, str) or not final_note.strip():
                raise ValueError("ComplianceAgent returned empty output.")
        except Exception as e:
            _state_warn(state, f"{symbol}: ComplianceAgent failed, using analyst note as fallback. ({e})")
            final_note = state.get("analyst_note", "")

        final_note = enforce_neutrality(final_note, cfg["compliance"]["forbidden_phrases"])
        if "[REDACTED]" in final_note:
            logger.warning("[Run:%s] Compliance redaction applied for %s", state.get("run_id"), symbol)

        state["final_note"] = final_note
        logger.info("[Run:%s][Node: Compliance] Completed for %s", state.get("run_id"), symbol)
        return state

    def node_supervise(state: dict):
        symbol, outdir = state["symbol"], state["outdir"]
        bundle = state["bundle"]

        # Data quality notes
        dq_msgs = []
        dq_msgs.extend(state.get("__warnings__", []) or [])
        dq_msgs.extend(_bundle_error_summary(bundle))

        dq_block = ""
        if dq_msgs:
            uniq = []
            seen = set()
            for m in dq_msgs:
                m = str(m).strip()
                if m and m not in seen:
                    uniq.append(m)
                    seen.add(m)
            dq_lines = "\n".join([f"- {m}" for m in uniq[:8]])
            dq_block = f"\n## Data Quality Notes\n{dq_lines}\n"

        logger.info("[Run:%s][Node: Publish] Enriching and publishing unified report for %s", state.get("run_id"),
                    symbol)

        price_rows = bundle.get("prices", {}).get("data", [])
        if not price_rows:
            error_msg = (
                f"No price data available for {symbol}. Symbol may be invalid or delisted. "
                "Skipping report generation."
            )
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

        fundamentals = bundle.get("fundamentals", {})
        inc_list = fundamentals.get("income_statement", [])
        met_list = fundamentals.get("key_metrics_ttm", [])

        inc = inc_list[0] if isinstance(inc_list, list) and inc_list else {}
        met = met_list[0] if isinstance(met_list, list) and met_list else {}
        reported_currency = inc.get("reportedCurrency")

        # Chart generation (safe)
        try:
            plot_path = save_price_plot(dates, closes, reported_currency, os.path.join(outdir, f"{symbol}_chart.png"))
        except Exception as e:
            _state_warn(state, f"{symbol}: Chart generation failed. ({e})")
            plot_path = ""

        # --- News headlines (skip error markers) ---
        news_items = bundle.get("news", [])
        cleaned_news = []
        if isinstance(news_items, list) and news_items:
            for n in news_items[:8]:
                if isinstance(n, dict) and n.get("__error__"):
                    continue  # IMPORTANT: do not show error markers as headlines

                title = (n.get("title", "Untitled") if isinstance(n, dict) else "Untitled").strip()
                title = re.sub(r"[\[\]\n\r]+", " ", title)
                link = (n.get("link", "") if isinstance(n, dict) else "").strip()
                date_str = ((n.get("published", "") if isinstance(n, dict) else "")[:16] or "N/A")

                if link:
                    cleaned_news.append(f"- [{title}]({link}) ({date_str})")
                else:
                    cleaned_news.append(f"- {title} ({date_str})")

        if cleaned_news:
            news_summary = "\n" + "\n".join(cleaned_news)
        else:
            news_summary = "No significant news headlines found in this period."

        # SupervisorAgent synthesis (safe)
        try:
            supervisor_input_summary = f"""
            Prices: {len(price_rows)} rows
            Fundamentals available: {bool(inc_list and met_list)}
            News items: {len([n for n in news_items if isinstance(n, dict) and not n.get("__error__")]) if isinstance(news_items, list) else 0}
            """

            supervisor_text = supervisor.run(
                symbol=symbol,
                data_summary=supervisor_input_summary,
                final_note=state.get("final_note", ""),
            ).strip()

            # Remove dangling "## Compliant Note\nFinal Note"
            supervisor_text = re.sub(
                r"(?is)\n##\s*Compliant Note\s*\n\s*(final note)?\s*$",
                "",
                supervisor_text,
            ).strip()

        except Exception as e:
            logger.warning("SupervisorAgent failed for %s, falling back to raw compliant text. (%s)", symbol, e)
            supervisor_text = state.get("final_note", "").strip()

        stats_block = (
            f"- Mean: {mean_ret:.4f} ({mean_ret * 100:.2f}%)\n"
            f"- Volatility: {vol_ret:.4f} ({vol_ret * 100:.2f}%)\n"
            f"- Min: {min_ret:.4f} ({min_ret * 100:.2f}%)\n"
            f"- Max: {max_ret:.4f} ({max_ret * 100:.2f}%)\n"
        )

        chart_block = ""
        if plot_path:
            chart_block = f"""
<div style="text-align: center; margin-top: 25px; margin-bottom: 25px;">
  <img src="{os.path.abspath(plot_path)}" alt="Price Chart" style="width: 70%; margin: auto; display: block;">
  <p style="font-weight: bold; margin-top: 10px;">Price Chart</p>
</div>
""".strip()

        report_md = f"""
## 1. Market Overview
- Symbol: {symbol}
- Data Coverage: {len(price_rows)} rows ({max(len(price_rows) - 1, 0)} returns)
{stats_block}- News Items Processed: {len(cleaned_news)}

## 2. Fundamental Highlights
- Fiscal Year: {int(inc.get('fiscalYear')) if inc.get('fiscalYear') else "N/A"}.
- Revenue: {safe_num(inc.get('revenue'), reported_currency)}.
- Net Income: {safe_num(inc.get('netIncome'), reported_currency)}.
- EPS (Diluted): {safe_num(inc.get('epsDiluted'), reported_currency)}.

## 3. Recent News Headlines
{news_summary}

## 4. Analyst Commentary
{supervisor_text}

## 5. Methodology
- Prices sourced via yfinance.
- Fundamentals via FinancialModelingPrep (free key or fallback).
- News via RSS feeds.
- Volatility and returns calculated using numpy and pandas.
- Report generated through LangGraph multi-agent orchestration:
  - Data Agent: Market and fundamental data collection.
  - Analyst Agent: Narrative generation.
  - Compliance Agent: Disclosure and phrasing checks.
  - Supervisor Agent: Final synthesis and report structuring.
{dq_block}
## 6. Execution Metadata
- Model: GPT-5.
- Run Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}.
- Coverage Days: {state['days']}.
- Output Directory: {outdir}.
- Data Sources: yfinance, FMP (Free/Fallback), Public RSS Feeds.
- Pipeline: LangGraph Orchestration Framework.

{chart_block}

## 7. Compliance Disclaimer
This automated report is generated by a multi-agent AI research framework (LangGraph + LangChain + GPT-5).
It is intended for educational and informational purposes only and does not constitute investment advice.
Past performance is not indicative of future results. Data accuracy is not guaranteed.

Generated by the Automated Stock Research Multi-Agent System.
"""

        report_md = textwrap.dedent(report_md).strip()
        report_md = report_md.replace("## ", "\n## ")

        file_name = render_filename(cfg["report"]["filename_template"], symbol=symbol)
        save_json(bundle, outdir, f"{symbol}_raw.json")
        save_markdown(report_md, outdir, file_name)

        state["report_path"] = os.path.join(outdir, file_name)
        state["plot_path"] = plot_path
        logger.info(
            "[Run:%s][Node: Publish] Unified report ready for %s -> %s",
            state.get("run_id"),
            symbol,
            state["report_path"],
        )

        # PDF export (safe)
        pdf_path = os.path.join(outdir, file_name.replace(".md", ".pdf"))
        try:
            import pypandoc

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
                    f"--metadata=title:{symbol} Stock Market Report - {state['days']}-Session",
                    f"--css={css_path}",
                    f"--resource-path={outdir}",
                    f"--resource-path={os.path.dirname(plot_path)}" if plot_path else f"--resource-path={outdir}",
                ],
            )

            logger.info("[Run:%s][Node: Publish] PDF version created for %s -> %s", state.get("run_id"), symbol,
                        pdf_path)
            state["pdf_path"] = pdf_path

        except Exception as e:
            logger.warning("PDF export failed for %s: %s", symbol, e)

        return state

    g.add_node("collect_data", node_collect_data)
    g.add_node("analyze", node_analyze)
    g.add_node("compliance", node_compliance)
    g.add_node("supervisor", node_supervise)

    g.add_edge(START, "collect_data")
    g.add_edge("collect_data", "analyze")
    g.add_edge("analyze", "compliance")
    g.add_edge("compliance", "supervisor")
    g.add_edge("supervisor", END)

    logger.info("LangGraph pipeline successfully built.")
    return g.compile()


def run_pipeline(symbol: str, days: int, outdir: str, human: bool = False) -> Dict[str, Any]:
    """
    Run the multi-agent pipeline end-to-end and return paths to generated artifacts.
    """
    import yfinance as yf
    req = validate_request(symbol=symbol, days=days, outdir=outdir)
    symbol_uppercase = req.symbol
    run_id = str(uuid.uuid4())[:8]
    set_log_context(run_id=run_id, symbol=symbol_uppercase)
    logger.info("Run ID: %s", run_id)

    days = req.days
    outdir = os.path.join(req.outdir, symbol_uppercase)

    load_dotenv()
    logger.info("=== Starting pipeline for %s (days=%d) ===", symbol_uppercase, days)

    # Pre-check with yfinance
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
                "suggested_action": "Verify the ticker or try another symbol.",
            }
    except Exception as exc:
        error_msg = f"Could not validate symbol {symbol_uppercase}: {exc}"
        logger.error(error_msg)
        return {"status": "error", "symbol": symbol_uppercase, "reason": error_msg}

    # Load YAML configuration
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    fmp_key = os.getenv("FMP_API_KEY", "demo")
    logger.debug("Loaded configuration and API key.")

    # Global timeout
    timeout_sec = int(cfg.get("orchestration", {}).get("timeout_sec", 90))

    try:
        app = build_graph(cfg, fmp_api_key=fmp_key)
        state = {"symbol": symbol_uppercase, "days": days, "outdir": outdir, "run_id": run_id}

        # ---- GLOBAL WORKFLOW TIMEOUT (Patch 4) ----
        with cf.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(app.invoke, state)
            result = fut.result(timeout=timeout_sec)

        if not result.get("report_path"):
            reason = result.get("error") or "Report was not generated due to missing required data."
            return {
                "status": "error",
                "symbol": symbol_uppercase,
                "reason": reason,
                "suggested_action": (
                    "Try another symbol or adjust days. If strict_mode=true, consider disabling it."
                ),
            }

    except cf.TimeoutError:
        msg = f"Workflow timeout after {timeout_sec}s (symbol={symbol_uppercase})."
        logger.error("[Run:%s] %s", run_id, msg)
        return {
            "status": "error",
            "symbol": symbol_uppercase,
            "reason": msg,
            "suggested_action": "Reduce days, try again later, or increase orchestration.timeout_sec in settings.yaml.",
        }

    except ValueError as e:
        msg = str(e)
        logger.error("Pipeline failed for %s: %s", symbol_uppercase, msg)

        suggestion = None
        if "402" in msg or "Payment Required" in msg:
            suggestion = "Provide a paid FMP API key or set strict_mode: false in config/settings.yaml."

        return {
            "status": "error",
            "symbol": symbol_uppercase,
            "reason": msg,
            **({"suggested_action": suggestion} if suggestion else {}),
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
