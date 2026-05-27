"""Clinical date and length-of-stay sanity checks."""

from __future__ import annotations

import duckdb

from src.core.db import table_exists
from src.validation.validation_report import ValidationResult


def _count(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    return int(con.execute(sql).fetchone()[0])


def validate_date_ranges(con: duckdb.DuckDBPyConnection) -> list[ValidationResult]:
    """Check LOS and core date sanity."""
    results: list[ValidationResult] = []
    if table_exists(con, "silver_admissions"):
        negative_hosp = _count(
            con,
            "SELECT COUNT(*) FROM silver_admissions WHERE hospital_los_hours < 0",
        )
        results.append(
            ValidationResult(
                "nonnegative_hospital_los",
                "pass" if negative_hosp == 0 else "fail",
                f"Negative hospital LOS records: {negative_hosp}",
            )
        )
        null_admit_discharge = _count(
            con,
            """
            SELECT COUNT(*)
            FROM silver_admissions
            WHERE admittime IS NULL OR dischtime IS NULL
            """,
        )
        results.append(
            ValidationResult(
                "core_admission_dates_present",
                "pass" if null_admit_discharge == 0 else "warn",
                f"Admissions with null admit/discharge time: {null_admit_discharge}",
                "warn" if null_admit_discharge else "error",
            )
        )

    if table_exists(con, "silver_icustays"):
        negative_icu = _count(
            con,
            "SELECT COUNT(*) FROM silver_icustays WHERE icu_los_hours < 0",
        )
        results.append(
            ValidationResult(
                "nonnegative_icu_los",
                "pass" if negative_icu == 0 else "fail",
                f"Negative ICU LOS records: {negative_icu}",
            )
        )

    if table_exists(con, "silver_patients"):
        unexpected_gender = _count(
            con,
            """
            SELECT COUNT(*)
            FROM silver_patients
            WHERE gender IS NOT NULL AND gender NOT IN ('M', 'F')
            """,
        )
        results.append(
            ValidationResult(
                "expected_gender_categories",
                "pass" if unexpected_gender == 0 else "warn",
                f"Unexpected gender values: {unexpected_gender}",
                "warn" if unexpected_gender else "error",
            )
        )
    return results
