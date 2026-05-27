"""Silver layer builder."""

from __future__ import annotations

from pathlib import Path

from src.core.config import WarehouseConfig
from src.transform.build_bronze import build_bronze
from src.transform.run_sql_layer import run_sql_layer


def build_silver(config: WarehouseConfig) -> list[Path]:
    """Build cleaned Silver tables from Bronze tables."""
    build_bronze(config)
    return run_sql_layer(config, "silver")
