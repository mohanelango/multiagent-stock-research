import numpy as np
from typing import List, Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)


def basic_return_stats(closes: List[float]) -> Dict[str, Any]:
    logger.debug("Computing basic return stats for %d data points", len(closes))
    arr = np.array(closes, dtype=float)
    if arr.size < 2:
        logger.warning("Insufficient data for stats computation")
        return {"mean": None, "vol": None, "count": int(arr.size)}
    rets = np.diff(arr) / arr[:-1]
    stats = {
        "mean": float(np.mean(rets)),
        "vol": float(np.std(rets)),
        "min": float(np.min(rets)),
        "max": float(np.max(rets)),
        "count": int(rets.size)
    }
    logger.debug("Return stats computed: %s", stats)
    return stats
