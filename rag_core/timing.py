"""Latency logs for agent calls."""

import logging
import time
from contextlib import contextmanager

logger = logging.getLogger("codelens.agents")


@contextmanager
def log_latency(agent: str, **fields):
    """Log wall-clock seconds for one agent call.

    The yielded dict can be updated inside the block; those fields are
    included in the log line (for example cache=hit).
    """
    info = dict(fields)
    start = time.perf_counter()
    try:
        yield info
    finally:
        elapsed = time.perf_counter() - start
        extra = " ".join(f"{key}={value}" for key, value in info.items())
        suffix = f" {extra}" if extra else ""
        logger.info("agent=%s latency_s=%.3f%s", agent, elapsed, suffix)
