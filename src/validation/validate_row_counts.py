"""Data volume validation checks."""

from __future__ import annotations

import duckdb

from src.core.db import row_count, table_exists
from src.validation.validation_report import ValidationResult


EXPECTED_NONEMPTY_WHEN_DATA_PRESENT = (
    "bronze_hosp_patients",
    "bronze_hosp_admissions",
    "bronze_icu_icustays",
)


def validate_row_counts(con: duckdb.DuckDBPyConnection) -> list[ValidationResult]:
    """Warn about empty core tables without failing public smoke tests."""
    results: list[ValidationResult] = []
    for table in EXPECTED_NONEMPTY_WHEN_DATA_PRESENT:
        if not table_exists(con, table):
            results.append(ValidationResult(f"{table}_exists", "warn", "Table is absent", "warn"))
            continue
        rows = row_count(con, table)
        results.append(
            ValidationResult(
                f"{table}_row_count",
                "pass" if rows > 0 else "warn",
                f"Rows: {rows}",
                "warn" if rows == 0 else "error",
            )
        )
    return results
