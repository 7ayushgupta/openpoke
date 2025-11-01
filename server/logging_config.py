from __future__ import annotations

import logging
import os

logger = logging.getLogger("openpoke.server")


def configure_logging() -> None:
    """Configure logging with a fixed log level."""
    if logger.handlers:
        return

    # Enable DEBUG mode if DEBUG env var is set
    log_level = logging.DEBUG if os.getenv("DEBUG", "").lower() in ("1", "true", "yes") else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
