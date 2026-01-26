import io
import os
import json
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any

import requests
import streamlit as st

# -----------------------------
# Config
# -----------------------------
DEFAULT_API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
ANALYZE_ENDPOINT = f"{DEFAULT_API_URL}/analyze"
HEALTH_ENDPOINT = f"{DEFAULT_API_URL}/health"


# -----------------------------
# Helpers
# -----------------------------
def _validate_symbol(symbol: str) -> str:
    s = (symbol or "").strip().upper()
    if not s:
        raise ValueError("Please enter a stock symbol (e.g., AAPL).")
    if not s.replace("-", "").replace(".", "").isalnum():
        raise ValueError("Symbol contains invalid characters. Use letters/numbers, '.' or '-' only.")
    if len(s) > 12:
        raise ValueError("Symbol is too long. Please verify the ticker.")
    return s


def _validate_days(days: int) -> int:
    if days < 5 or days > 10:
        raise ValueError("Days must be between 5 and 10.")
    return int(days)


def _call_api(symbol: str, days: int) -> Dict[str, Any]:
    payload = {"symbol": symbol, "days": days}
    r = requests.post(ANALYZE_ENDPOINT, json=payload)

    try:
        data = r.json()
    except Exception:
        raise RuntimeError(f"Backend returned a non-JSON response (HTTP {r.status_code}).")

    if r.status_code >= 400 or data.get("status") == "error":
        reason = data.get("reason") or f"Request failed (HTTP {r.status_code})."
        suggested = data.get("suggested_action")
        msg = reason + (f"\n\nSuggested action: {suggested}" if suggested else "")
        raise RuntimeError(msg)

    return data


def _safe_read_bytes(path: Optional[str]) -> Optional[bytes]:
    try:
        if not path:
            return None
        p = Path(path)
        if not p.exists():
            return None
        return p.read_bytes()
    except Exception:
        return None


def _safe_read_text(path: Optional[str]) -> Optional[str]:
    try:
        if not path:
            return None
        p = Path(path)
        if not p.exists():
            return None
        return p.read_text(encoding="utf-8")
    except Exception:
        return None


def _make_zip_bundle(files: Dict[str, Optional[bytes]]) -> Optional[bytes]:
    """
    files: dict of {filename: bytes}
    """
    usable = {k: v for k, v in files.items() if v}
    if not usable:
        return None

    buff = io.BytesIO()
    with zipfile.ZipFile(buff, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, data in usable.items():
            zf.writestr(filename, data)
    buff.seek(0)
    return buff.read()


def _inject_css():
    st.markdown(
        """
        <style>
        /* Layout */
        .block-container { padding-top: 1.3rem; max-width: 1200px; }
        header { visibility: hidden; }
        footer { visibility: hidden; }

        /* Background */
        [data-testid="stAppViewContainer"] {
          background: radial-gradient(1200px 600px at 30% 0%, rgba(56,189,248,0.12), transparent 60%),
                      radial-gradient(1000px 600px at 80% 20%, rgba(249,115,22,0.12), transparent 60%),
                      linear-gradient(180deg, #0B1220 0%, #070B14 100%);
        }

        /* Cards */
        .card {
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.10);
          border-radius: 16px;
          padding: 16px 16px;
        }
        .card-title {
          font-size: 0.95rem;
          font-weight: 600;
          color: rgba(255,255,255,0.90);
          margin-bottom: 6px;
        }
        .muted {
          color: rgba(255,255,255,0.65);
          font-size: 0.85rem;
        }

        /* Badges */
        .badge {
          display: inline-block;
          padding: 4px 10px;
          border-radius: 999px;
          font-size: 0.78rem;
          border: 1px solid rgba(255,255,255,0.14);
          background: rgba(255,255,255,0.04);
          color: rgba(255,255,255,0.80);
          margin-right: 8px;
        }

        /* Buttons */
        div.stButton > button {
          border-radius: 12px !important;
          padding: 0.65rem 1.0rem !important;
          font-weight: 600 !important;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
          background: rgba(255,255,255,0.02);
          border-right: 1px solid rgba(255,255,255,0.08);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_state():
    if "symbol" not in st.session_state:
        st.session_state.symbol = "MSFT"
    if "days" not in st.session_state:
        st.session_state.days = 10

    # persisted results
    if "result" not in st.session_state:
        st.session_state.result = None

    # persisted artifact bytes
    if "artifact_bytes" not in st.session_state:
        st.session_state.artifact_bytes = {}


def _render_agent_flow():
    st.markdown(
        """
        <div class="card">
          <div class="card-title">Agent Flow</div>
          <div class="muted">
            DataAgent → AnalystAgent → ComplianceAgent → SupervisorAgent
          </div>
          <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap;">
            <span class="badge">Prices (yfinance)</span>
            <span class="badge">Fundamentals (FMP)</span>
            <span class="badge">News (RSS)</span>
            <span class="badge">Neutrality Filter</span>
            <span class="badge">Markdown + PDF</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_backend_status():
    with st.sidebar:

        # Non-blocking health check
        status_txt = "Unknown"
        try:
            r = requests.get(HEALTH_ENDPOINT)
            if r.status_code == 200:
                status_txt = "Online"
            else:
                status_txt = f"HTTP {r.status_code}"
        except Exception:
            status_txt = "Not reachable"

        st.write(f"Status: **{status_txt}**")
        st.write("Start it with:")
        st.code("uvicorn src.api:app --reload --port 8000", language="bash")

        st.divider()
        st.subheader("Tips")
        st.write("- Use symbols like AAPL, MSFT, META.")
        st.write("- If fundamentals fail: FMP quota may be exhausted (402).")
        st.write("- PDF export needs pandoc + wkhtmltopdf.")


def _persist_artifacts(result: Dict[str, Any]):
    """
    Reads artifacts from paths returned by API and stores bytes in session_state,
    so downloads won't depend on the 'Generate' button state.
    """
    report_path = result.get("report") or result.get("report_path")
    pdf_path = result.get("pdf") or result.get("pdf_path")
    plot_path = result.get("plot") or result.get("plot_path")
    raw_path = result.get("raw") or result.get("raw_data")

    md_bytes = _safe_read_bytes(report_path)
    pdf_bytes = _safe_read_bytes(pdf_path)
    chart_bytes = _safe_read_bytes(plot_path)
    raw_bytes = _safe_read_bytes(raw_path)

    stored = {
        "symbol": result.get("symbol"),
        "report.md": md_bytes,
        "report.pdf": pdf_bytes,
        "chart.png": chart_bytes,
        "raw.json": raw_bytes,
        "_paths": {
            "md": report_path,
            "pdf": pdf_path,
            "chart": plot_path,
            "raw": raw_path,
        }
    }
    st.session_state.artifact_bytes = stored


def _render_results():
    """
    Render persisted results if available.
    """
    result = st.session_state.result
    if not result:
        return

    st.success("Report generated successfully.")
    with st.expander("API response payload", expanded=False):
        st.json(result)

    paths = st.session_state.artifact_bytes.get("_paths", {})
    md_path = paths.get("md")
    pdf_path = paths.get("pdf")
    chart_path = paths.get("chart")
    raw_path = paths.get("raw")

    tabs = st.tabs(["Overview", "Report", "Chart", "Raw Data", "Downloads"])

    # --- Overview ---
    with tabs[0]:
        cols = st.columns(2)
        with cols[0]:
            st.markdown('<div class="card"><div class="card-title">Symbol</div>', unsafe_allow_html=True)
            st.markdown(f"<div class='muted'>{(result.get('symbol') or '').upper()}</div></div>",
                        unsafe_allow_html=True)

        with cols[1]:
            st.markdown('<div class="card"><div class="card-title">Artifacts</div>', unsafe_allow_html=True)
            available = []
            if md_path and Path(md_path).exists(): available.append("Markdown")
            if pdf_path and Path(pdf_path).exists(): available.append("PDF")
            if chart_path and Path(chart_path).exists(): available.append("Chart")
            if raw_path and Path(raw_path).exists(): available.append("Raw JSON")
            st.markdown(f"<div class='muted'>{', '.join(available) if available else 'None found'}</div></div>",
                        unsafe_allow_html=True)

        st.write("")
        _render_agent_flow()

    # --- Report ---
    with tabs[1]:
        md_text = _safe_read_text(md_path)
        if md_text:
            st.markdown(md_text)
        else:
            st.warning("Markdown report not found. Ensure API and UI run on the same machine, or serve files via API.")

    # --- Chart ---
    with tabs[2]:
        if chart_path and Path(chart_path).exists():
            st.image(chart_path, caption="Price Chart", width='stretch')
        else:
            st.warning("Chart not found.")

    # --- Raw Data ---
    with tabs[3]:
        raw_text = _safe_read_text(raw_path)
        if raw_text:
            try:
                st.json(json.loads(raw_text))
            except Exception:
                st.code(raw_text)
        else:
            st.warning("Raw JSON not found.")

    # --- Downloads ---
    with tabs[4]:
        stored = st.session_state.artifact_bytes or {}
        md_b = stored.get("report.md")
        pdf_b = stored.get("report.pdf")
        raw_b = stored.get("raw.json")
        chart_b = stored.get("chart.png")
        symbol = stored.get("symbol")

        colA, colB, colC, colD = st.columns(4)
        with colA:
            if md_b:
                st.download_button(
                    "Download .md",
                    data=md_b,
                    file_name=Path(md_path).name if md_path else "report.md",
                    mime="text/markdown",
                    key="dl_md",
                )
        with colB:
            if pdf_b:
                st.download_button(
                    "Download .pdf",
                    data=pdf_b,
                    file_name=Path(pdf_path).name if pdf_path else "report.pdf",
                    mime="application/pdf",
                    key="dl_pdf",
                )
        with colC:
            if raw_b:
                st.download_button(
                    "Download raw .json",
                    data=raw_b,
                    file_name=Path(raw_path).name if raw_path else "raw.json",
                    mime="application/json",
                    key="dl_raw",
                )
        with colD:
            if chart_b:
                st.download_button(
                    "Download chart .png",
                    data=chart_b,
                    file_name=Path(chart_path).name if chart_path else "chart.png",
                    mime="image/png",
                    key="dl_chart",
                )

        st.write("")
        bundle_zip = _make_zip_bundle({
            Path(md_path).name if md_path else "report.md": md_b,
            Path(pdf_path).name if pdf_path else "report.pdf": pdf_b,
            Path(raw_path).name if raw_path else "raw.json": raw_b,
            Path(chart_path).name if chart_path else "chart.png": chart_b,
        })
        if bundle_zip:
            st.download_button(
                "Download ALL (zip bundle)",
                data=bundle_zip,
                file_name=f"{symbol}.zip",
                mime="application/zip",
                key="dl_zip",
            )

    st.write("")
    if st.button("Clear results", type="secondary"):
        st.session_state.result = None
        st.session_state.artifact_bytes = {}
        st.rerun()


# -----------------------------
# App
# -----------------------------
def main():
    st.set_page_config(
        page_title="Multi-Agent Stock Research",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_css()
    _init_state()
    _render_backend_status()

    # Hero / Header
    st.markdown(
        """
        <div style="padding: 10px 0 14px 0;">
          <div style="font-size: 2.3rem; font-weight: 800; color: rgba(255,255,255,0.92);">
            Multi-Agent Stock Research
          </div>
          <div class="muted" style="margin-top:6px;">
            Generate a research snapshot using a LangGraph workflow:
            Data → Analyst → Compliance → Supervisor.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # st.image("docs/_Multiagent.svg", width='stretch')

    # Input form (prevents rerun noise)
    with st.form("run_form", clear_on_submit=False):
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol = st.text_input("Stock symbol", value=st.session_state.symbol)
        with c2:
            days = st.number_input("Days", min_value=5, max_value=10, value=int(st.session_state.days), step=1)

        submitted = st.form_submit_button("Generate report", type="primary")

    # Submit action
    if submitted:
        try:
            symbol_clean = _validate_symbol(symbol)
            days_clean = _validate_days(int(days))
        except Exception as ve:
            st.error(str(ve))
        else:
            st.session_state.symbol = symbol_clean
            st.session_state.days = days_clean

            with st.spinner(f"Generating Snapshot For {symbol_clean} ({days_clean} days)…"):
                try:
                    result = _call_api(symbol_clean, days_clean)
                except Exception as e:
                    st.error(str(e))
                    st.info(
                        "If fundamentals fail, it may be FMP quota exhaustion (402). Consider strict_mode: false or a paid key.")
                else:
                    st.session_state.result = result
                    _persist_artifacts(result)
                    st.rerun()

    # Render persisted results even after downloads / reruns
    _render_results()

    # Footer note
    st.caption("Disclaimer: Informational only. Not investment advice. Data accuracy not guaranteed.")


if __name__ == "__main__":
    main()
