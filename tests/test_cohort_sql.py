from __future__ import annotations

import pytest

pytest.importorskip("duckdb")

from src.core.config import WarehouseConfig
from src.core.db import connect
from src.core.paths import project_root
from src.ingest.load_demo import load_local_files
from src.transform.build_gold import build_gold


def test_cohort_sql_returns_aggregate_summary(
    synthetic_config: WarehouseConfig,
    synthetic_raw_data,
) -> None:
    load_local_files(synthetic_config)
    build_gold(synthetic_config)

    cohort_dir = project_root() / "sql" / "cohorts"
    with connect(synthetic_config) as con:
        for path in cohort_dir.glob("*.sql"):
            df = con.execute(path.read_text()).fetchdf()
            assert "cohort_size" in df.columns
            assert len(df) == 1
