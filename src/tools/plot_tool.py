import os
import pandas as pd
import matplotlib
matplotlib.use(os.environ.get("MPLBACKEND", "Agg"))
import matplotlib.pyplot as plt
from typing import List
from src.utils.logger import get_logger

logger = get_logger(__name__)


def save_price_plot(dates: List[str], closes: List[float], reported_currency, outpath: str) -> str:
    logger.debug("Creating price plot at %s", outpath)
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    try:
        df = pd.DataFrame({"date": dates, "close": closes})
        df["date"] = pd.to_datetime(df["date"],utc=True)
        plt.figure(figsize=(8, 4))
        plt.plot(df["date"], df["close"])
        plt.title("Close Price")
        plt.xlabel("Date")
        plt.ylabel(f"Price ({reported_currency})")
        plt.tight_layout()
        plt.savefig(outpath, dpi=120)
        plt.close()
        logger.info("Saved price chart to %s", outpath)
        plt.close()
        return outpath
    except Exception as e:
        logger.error("Plot generation failed: %s", e)
        return outpath
