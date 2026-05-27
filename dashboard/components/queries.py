"""Aggregate DuckDB queries for Streamlit pages."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.config import load_config  # noqa: E402
from src.core.db import connect, table_exists  # noqa: E402
from src.core.paths import project_root  # noqa: E402
from src.llm.nl_to_sql import answer_question  # noqa: E402
from src.llm.sql_guardrails import validate_aggregate_sql  # noqa: E402


def get_config():
    """Load dashboard config."""
    return load_config(os.getenv("MIMIC_CONFIG_PATH", "configs/demo.duckdb.yaml"))


def query_df(sql: str) -> pd.DataFrame:
    """Run an aggregate query and return a DataFrame."""
    with connect(get_config()) as con:
        return con.execute(sql).fetchdf()


def safe_query_df(sql: str) -> pd.DataFrame:
    """Run guarded aggregate SQL from the dashboard query assistant."""
    config = get_config()
    guardrail = validate_aggregate_sql(
        sql,
        allowed_tables=set(config.llm.allowed_tables),
        default_limit=config.llm.default_limit,
    )
    if not guardrail.allowed or guardrail.sql is None:
        raise ValueError("; ".join(guardrail.reasons))
    return query_df(guardrail.sql)


def overview_metrics() -> dict[str, object]:
    """Return dashboard overview metrics."""
    df = query_df(
        """
        SELECT
            (SELECT count(*) FROM gold_patient_summary) AS patients,
            (SELECT count(*) FROM gold_admission_summary) AS admissions,
            (SELECT count(*) FROM gold_icu_stay_summary) AS icu_stays,
            (SELECT coalesce(sum(lab_event_count), 0) FROM gold_admission_summary) AS lab_events,
            (SELECT coalesce(sum(medication_count), 0) FROM gold_admission_summary) AS medication_events,
            (SELECT coalesce(sum(chart_event_count_24h), 0) FROM gold_first_24h_features) AS chart_events_24h,
            (SELECT avg(hospital_los_days) FROM gold_admission_summary) AS avg_hospital_los,
            (SELECT avg(icu_los_days) FROM gold_icu_stay_summary) AS avg_icu_los,
            (SELECT avg(in_hospital_mortality_flag) FROM gold_admission_summary) AS mortality_rate
        """
    )
    return df.iloc[0].to_dict() if not df.empty else {}


def table_exists_in_db(table: str) -> bool:
    """Check table existence."""
    with connect(get_config()) as con:
        return table_exists(con, table)


def cohort_summary(cohort_name: str) -> pd.DataFrame:
    """Execute privacy-safe cohort summary SQL."""
    path = project_root() / "sql" / "cohorts" / f"{cohort_name}.sql"
    if not path.exists():
        raise ValueError(f"Unknown cohort: {cohort_name}")
    return query_df(path.read_text())


def cohort_names() -> list[str]:
    """Return available cohort names."""
    return sorted(path.stem for path in (project_root() / "sql" / "cohorts").glob("*.sql"))


def ask_demo_question(question: str) -> dict[str, object]:
    """Run the guarded rule-based query assistant."""
    config = get_config()
    with connect(config) as con:
        return answer_question(
            con,
            question,
            config.outputs_private_path,
            allowed_tables=set(config.llm.allowed_tables),
            default_limit=config.llm.default_limit,
        )
