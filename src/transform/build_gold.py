"""Gold layer builder."""

from __future__ import annotations

from pathlib import Path

from src.core.config import WarehouseConfig
from src.transform.build_silver import build_silver
from src.transform.run_sql_layer import run_sql_layer


def build_gold(config: WarehouseConfig) -> list[Path]:
    """Build analytics-ready Gold marts from Silver tables."""
    build_silver(config)
    return run_sql_layer(config, "gold")
