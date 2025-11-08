import argparse
import os
from src.graph.orchestrator import run_pipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Automated Stock Market Research (LangGraph Multi-Agent)")
    parser.add_argument("--symbol", required=True, help="Stock ticker to analyze (e.g., AAPL, MSFT)")
    parser.add_argument("--days", type=int, default=30, help="Number of past trading days to analyze")
    parser.add_argument("--outdir", default="artifacts", help="Output directory for storing artifacts")
    parser.add_argument("--human", default="false", help="Enable human-in-the-loop review (true/false)")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    logger.info("CLI called with symbol=%s days=%d outdir=%s", symbol, args.days, args.outdir)
    os.makedirs(args.outdir, exist_ok=True)

    res = run_pipeline(args.symbol, args.days, args.outdir, human=(str(args.human).lower() == "true"))
    # Check for error in response
    if isinstance(res, dict) and res.get("status") == "error":
        print(f"\n[ERROR] {res['reason']}")
        if "suggested_action" in res:
            print(f"Suggestion: {res['suggested_action']}")
        return

    logger.info("CLI execution finished successfully for %s", symbol)

    print("\n== Outputs ==")
    for k, v in res.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
