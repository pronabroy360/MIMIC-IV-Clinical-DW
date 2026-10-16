"""Quality checks that catch source errors before Silver deduplication hides them."""

from __future__ import annotations

import duckdb

from src.core.db import table_exists
from src.validation.validation_report import ValidationResult


def validate_source_key_uniqueness(con: duckdb.DuckDBPyConnection) -> list[ValidationResult]:
    """Detect duplicate source keys in Bronze admission and ICU tables."""
    checks = (
        ("bronze_hosp_admissions", "hadm_id", "bronze_unique_admission_keys"),
        ("bronze_icu_icustays", "stay_id", "bronze_unique_icu_stay_keys"),
    )
    results = []
    for table, column, check in checks:
        if not table_exists(con, table):
            continue
        duplicates = int(con.execute(
            f"SELECT count(*) FROM (SELECT {column} FROM {table} GROUP BY {column} HAVING count(*) > 1)"
        ).fetchone()[0])
        results.append(ValidationResult(
            check,
            "pass" if duplicates == 0 else "fail",
            f"Duplicate source {column} groups: {duplicates}",
        ))
    return results


def validate_invented_physiology_ranges(con: duckdb.DuckDBPyConnection) -> list[ValidationResult]:
    """Block impossible saturation values in the invented quality laboratory."""
    if not table_exists(con, "bronze_icu_chartevents"):
        return []
    impossible = int(con.execute("SELECT count(*) FROM bronze_icu_chartevents WHERE itemid = '220277' AND (try_cast(valuenum AS DOUBLE) > 105 OR try_cast(valuenum AS DOUBLE) < 0)").fetchone()[0])
    return [ValidationResult("bronze_invented_physiology_range", "pass" if impossible == 0 else "fail", f"Impossible invented chart values: {impossible}")]
