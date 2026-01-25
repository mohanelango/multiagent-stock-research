from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
from src.graph.orchestrator import run_pipeline
from src.utils.logger import get_logger
import yfinance as yf

logger = get_logger(__name__)

app = FastAPI(
    title="Automated Stock Research MultiAgent System",
    description="LangGraph Multi-Agent Orchestration (Data, Analyst, Compliance, Supervisor)",
    version="0.1.0",
)


class RunRequest(BaseModel):
    symbol: str
    days: int = 30
    human: bool = False
    outdir: str = "artifacts"


@app.get("/health", tags=["health"])
def health():
    """
    Lightweight health endpoint for UIs and monitoring.
    Does not call external services.
    """
    return {"status": "ok", "service": "multiagent-stock-research"}



@app.post("/analyze", tags=["analysis"])
def analyze_stock(req: RunRequest):
    symbol_uppercase = req.symbol.strip().upper()
    if not symbol_uppercase.replace("-", "").replace(".", "").isalnum():
        return JSONResponse(status_code=400, content={"status": "error", "reason": "Invalid symbol format."})

    if req.days < 5 or req.days > 15:
        return JSONResponse(status_code=400, content={"status": "error", "reason": "Days must be between 5 and 15."})

    # Pre-check: Validate ticker using yfinance before pipeline execution
    try:
        ticker = yf.Ticker(symbol_uppercase)
        info = ticker.info
        if not info or "shortName" not in info or info.get("regularMarketPrice") is None:
            error_message = (
                f"Symbol '{symbol_uppercase}' is invalid or has no current market data (possibly delisted). "
                "Please check the ticker or try another one."
            )
            logger.error(error_message)
            return JSONResponse(
                status_code=400,
                content={"status": "error", "reason": error_message}
            )
    except Exception as exc:
        logger.error("Error during pre-check for symbol %s: %s", symbol_uppercase, exc)
        return JSONResponse(
            status_code=400,
            content={"status": "error", "reason": f"Could not validate symbol {symbol_uppercase}: {exc}"}
        )

    logger.info("POST /analyze called with symbol=%s, days=%d", req.symbol, req.days)

    try:
        os.makedirs(req.outdir, exist_ok=True)
        result = run_pipeline(req.symbol, req.days, req.outdir, req.human)

        # If strict-mode returned an error
        if isinstance(result, dict) and result.get("status") == "error":
            logger.error("Strict mode pipeline abort: %s", result.get("reason"))
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "symbol": result.get("symbol"),
                    "reason": result.get("reason"),
                    "suggested_action": result.get("suggested_action")
                }
            )

        logger.info("Report successfully generated for %s", req.symbol)
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "symbol": symbol_uppercase,
                "report_path": result.get("report"),
                "plot_path": result.get("plot"),
                "raw_data": result.get("raw"),
                "pdf_path": result.get("pdf"),
                "message": "Report successfully generated"
            }
        )

    except Exception as e:
        logger.exception("Error generating report for %s", req.symbol)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "reason": "Internal server error while generating report.",
                "suggested_action": "Check server logs for details."
            }
        )

