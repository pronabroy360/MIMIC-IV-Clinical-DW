"""Logging setup for command-line pipeline runs."""

from __future__ import annotations

import logging


def configure_logging(verbose: bool = False) -> None:
    """Configure compact console logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
