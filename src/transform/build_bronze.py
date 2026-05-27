"""Bronze layer builder."""

from __future__ import annotations

from pathlib import Path

from src.core.config import WarehouseConfig
from src.ingest.load_demo import ensure_all_expected_bronze_tables
from src.transform.run_sql_layer import run_sql_layer


def build_bronze(config: WarehouseConfig) -> list[Path]:
    """Ensure Bronze tables exist and execute any Bronze helper SQL."""
    ensure_all_expected_bronze_tables(config)
    return run_sql_layer(config, "bronze")
