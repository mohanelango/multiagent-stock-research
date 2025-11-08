import os
import pandas as pd
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from typing import List
from src.utils.logger import get_logger

logger = get_logger(__name__)


def save_price_plot(dates: List[str], closes: List[float], outpath: str) -> str:
    logger.debug("Creating price plot at %s", outpath)
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    try:
        df = pd.DataFrame({"date": dates, "close": closes})
        df["date"] = pd.to_datetime(df["date"])
        plt.figure(figsize=(8, 4))
        plt.plot(df["date"], df["close"])
        plt.title("Close Price")
        plt.xlabel("Date")
        plt.ylabel("Price")
        plt.tight_layout()
        plt.savefig(outpath, dpi=120)
        plt.close()
        logger.info("Saved price chart to %s", outpath)
        # return outpath
        # plt.figure(figsize=(8, 4))  # wider chart helps prevent overlap
        # plt.plot(dates, closes)
        # plt.title("Close Price")
        # plt.xlabel("Date")
        # plt.ylabel("Price")

        # ✅ Format the date axis properly
        # plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
        # plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        # plt.xticks(rotation=45, ha="right")  # rotate labels to avoid overlap

        # plt.tight_layout()  # adjusts layout to fit labels
        # plt.savefig(outpath, dpi=300, bbox_inches="tight")
        plt.close()
        return outpath
    except Exception as e:
        logger.error("Plot generation failed: %s", e)
        return outpath
