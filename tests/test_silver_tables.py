from __future__ import annotations

import pytest

pytest.importorskip("duckdb")

from src.core.config import WarehouseConfig
from src.core.db import connect
from src.ingest.load_demo import load_local_files
from src.transform.build_silver import build_silver


def test_silver_tables_build_core_records(
    synthetic_config: WarehouseConfig,
    synthetic_raw_data,
) -> None:
    load_local_files(synthetic_config)
    build_silver(synthetic_config)

    with connect(synthetic_config) as con:
        admission = con.execute(
            "SELECT hospital_los_days, in_hospital_mortality_flag FROM silver_admissions"
        ).fetchone()
        icu = con.execute("SELECT icu_los_days, is_first_icu_stay FROM silver_icustays").fetchone()

    assert admission[0] == 4.0
    assert admission[1] == 0
    assert icu[0] == 2.0
    assert icu[1] == 1
