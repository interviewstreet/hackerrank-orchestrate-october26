"""One logging configuration for the whole run, plus a stage timer."""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Iterator

from .config import CACHE_DIR, RUN_LOG

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def setup_logging(verbose: bool = False) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(logging.Formatter(_FORMAT, "%H:%M:%S"))
    root.addHandler(console)

    file_handler = logging.FileHandler(RUN_LOG, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(file_handler)

    # Third-party HTTP chatter stays out of the console.
    for noisy in ("httpx", "openai", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


@contextmanager
def stage(logger: logging.Logger, name: str) -> Iterator[None]:
    """Log start, end and elapsed time of a pipeline stage."""
    start = time.perf_counter()
    logger.info("%s: start", name)
    try:
        yield
    finally:
        logger.info("%s: done in %.2fs", name, time.perf_counter() - start)
