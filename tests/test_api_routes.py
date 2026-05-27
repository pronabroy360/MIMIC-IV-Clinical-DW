from __future__ import annotations

import pytest

pytest.importorskip("duckdb")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

import src.api.main as api_main
from src.core.config import WarehouseConfig
from src.ingest.load_demo import load_local_files
from src.transform.build_gold import build_gold


def test_api_routes_and_query_guardrails(
    synthetic_config: WarehouseConfig,
    synthetic_raw_data,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_local_files(synthetic_config)
    build_gold(synthetic_config)

    monkeypatch.setattr(api_main, "get_config", lambda: synthetic_config)
    client = TestClient(api_main.app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    overview = client.get("/analytics/overview")
    assert overview.status_code == 200
    overview_json = overview.json()
    assert overview_json["patient_count"] == 1
    assert overview_json["admission_count"] == 1
    assert overview_json["icu_stay_count"] == 1

    cohorts = client.get("/cohorts")
    assert cohorts.status_code == 200
    assert "adult_icu_first_stay" in cohorts.json()["cohorts"]

    cohort_summary = client.get("/cohorts/adult_icu_first_stay/summary")
    assert cohort_summary.status_code == 200
    assert cohort_summary.json()["cohort"] == "adult_icu_first_stay"

    allowed_query = client.post(
        "/query/aggregate",
        json={
            "sql": (
                "SELECT count(*) AS n_stays, avg(icu_los_days) AS avg_icu_los_days "
                "FROM gold_icu_stay_summary LIMIT 10"
            )
        },
    )
    assert allowed_query.status_code == 200
    allowed_rows = allowed_query.json()["rows"]
    assert isinstance(allowed_rows, list)
    assert len(allowed_rows) == 1
    assert "n_stays" in allowed_rows[0]

    blocked_query = client.post(
        "/query/aggregate",
        json={"sql": "SELECT * FROM gold_icu_stay_summary LIMIT 10"},
    )
    assert blocked_query.status_code == 400
    assert "SELECT * is not allowed" in blocked_query.json()["detail"]
