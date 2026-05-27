from __future__ import annotations

import pytest

pytest.importorskip("duckdb")

from src.core.config import WarehouseConfig
from src.core.db import connect, row_count
from src.ingest.load_demo import load_local_files
from src.transform.build_gold import build_gold


def test_gold_tables_build_first_24h_features(
    synthetic_config: WarehouseConfig,
    synthetic_raw_data,
) -> None:
    load_local_files(synthetic_config)
    build_gold(synthetic_config)

    with connect(synthetic_config) as con:
        assert row_count(con, "gold_icu_stay_summary") == 1
        feature = con.execute(
            "SELECT lactate_mean, creatinine_mean, heart_rate_mean FROM gold_first_24h_features"
        ).fetchone()

    assert feature[0] == 2.5
    assert feature[1] == 1.1
    assert feature[2] == 80.0
