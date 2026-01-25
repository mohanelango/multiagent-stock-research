import logging
import os
from logging.handlers import RotatingFileHandler

from src.utils.log_context import get_run_id, get_symbol


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = get_run_id()
        record.symbol = get_symbol()
        return True


def get_logger(name: str):
    """
    Create or return a configured logger with both console and rotating file handlers.
    Logs are stored at logs/app.log (max 5 MB, 3 backups).
    """
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Avoid duplicate handlers

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(level)

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(level)

    # Rotating File Handler
    fh = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] run=%(run_id)s sym=%(symbol)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    logger.addFilter(ContextFilter())
    ch.addFilter(ContextFilter())
    fh.addFilter(ContextFilter())

    logger.addHandler(ch)
    logger.addHandler(fh)
    logger.propagate = False

    return logger
