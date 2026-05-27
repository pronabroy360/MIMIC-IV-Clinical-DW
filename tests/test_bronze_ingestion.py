from __future__ import annotations

import pytest

pytest.importorskip("duckdb")

from src.core.config import WarehouseConfig
from src.core.db import connect, row_count
from src.ingest.load_demo import load_local_files


def test_bronze_ingestion_loads_available_files(
    synthetic_config: WarehouseConfig,
    synthetic_raw_data,
) -> None:
    report = load_local_files(synthetic_config)
    assert report.exists()

    with connect(synthetic_config) as con:
        assert row_count(con, "bronze_hosp_patients") == 1
        assert row_count(con, "bronze_icu_icustays") == 1
        columns = [row[1] for row in con.execute("PRAGMA table_info(bronze_hosp_patients)").fetchall()]
        assert "source_file" in columns
