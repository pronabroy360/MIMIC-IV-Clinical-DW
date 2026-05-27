"""Schema validation checks."""

from __future__ import annotations

import duckdb

from src.core.db import get_columns, table_exists
from src.validation.validation_report import ValidationResult


REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "silver_patients": ("subject_id", "gender", "anchor_age"),
    "silver_admissions": ("subject_id", "hadm_id", "admittime", "dischtime"),
    "silver_icustays": ("subject_id", "hadm_id", "stay_id", "intime", "outtime"),
    "silver_labs": ("subject_id", "hadm_id", "itemid", "charttime", "valuenum"),
    "gold_patient_summary": ("subject_id", "total_admissions", "total_icu_stays"),
    "gold_admission_summary": ("subject_id", "hadm_id", "hospital_los_days"),
    "gold_icu_stay_summary": ("subject_id", "hadm_id", "stay_id", "icu_los_days"),
    "gold_first_24h_features": ("subject_id", "hadm_id", "stay_id", "hospital_mortality_flag"),
}


def validate_schema(con: duckdb.DuckDBPyConnection) -> list[ValidationResult]:
    """Check required tables and columns."""
    results: list[ValidationResult] = []
    for table, required in REQUIRED_COLUMNS.items():
        if not table_exists(con, table):
            results.append(ValidationResult(table, "fail", f"Missing table {table}"))
            continue
        columns = set(get_columns(con, table))
        missing = [column for column in required if column not in columns]
        if missing:
            results.append(
                ValidationResult(
                    f"{table}_required_columns",
                    "fail",
                    f"Missing required columns: {', '.join(missing)}",
                )
            )
        else:
            results.append(
                ValidationResult(
                    f"{table}_required_columns",
                    "pass",
                    "Required columns exist",
                )
            )
    return results
