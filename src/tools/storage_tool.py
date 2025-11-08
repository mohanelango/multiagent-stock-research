import os
import json
from datetime import datetime
from jinja2 import Template
from src.utils.logger import get_logger

logger = get_logger(__name__)


def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)
    logger.debug("Ensured directory exists: %s", p)


def save_json(obj, outdir: str, filename: str):
    ensure_dir(outdir)
    path = os.path.join(outdir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    logger.info("Saved JSON: %s", path)
    return path


def save_markdown(content: str, outdir: str, filename: str):
    ensure_dir(outdir)
    path = os.path.join(outdir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info("Saved Markdown: %s", path)
    return path


def render_filename(template: str, symbol: str, date: str | None = None):
    if date is None:
        date = datetime.utcnow().strftime("%Y-%m-%d")
    fname = Template(template).render(symbol=symbol, date=date)
    logger.debug("Rendered filename: %s", fname)
    return fname
